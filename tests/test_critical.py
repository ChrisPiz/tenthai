"""Critical invariants — these protect design contracts. Refactors must not break these silently."""
from pathlib import Path

import pytest
from unittest.mock import AsyncMock, MagicMock

from henge.agents import PROMPTS, PROMPTS_HASH, TEMPERATURE, TENTH_MAN, run_agents
from henge.embed import project_mds
from henge.pricing import (
    HENGE_PRICING_VERSION,
    anthropic_call_cost,
    total_cost,
)
from henge.viz import compute_cfi


@pytest.mark.asyncio
async def test_partial_failure_8of9(mock_anthropic_client):
    """1 frame falla → sistema continúa con 8 frames + tenth-man, marca el faltante."""
    call_count = [0]
    original_create = mock_anthropic_client.messages.create

    async def maybe_fail(**kwargs):
        call_count[0] += 1
        if call_count[0] == 3:
            raise RuntimeError("Simulated 1-of-9 API failure")
        return await original_create(**kwargs)

    mock_anthropic_client.messages.create = AsyncMock(side_effect=maybe_fail)

    results = await run_agents(mock_anthropic_client, "Pregunta de prueba")

    assert len(results) == 10
    failed = [r for r in results if r[2] == "failed"]
    ok = [r for r in results if r[2] == "ok"]
    assert len(failed) == 1, f"Expected exactly 1 failed frame, got {len(failed)}"
    assert len(ok) == 9, "8 frames + 1 tenth-man = 9 ok"
    assert results[-1][0] == TENTH_MAN
    assert results[-1][2] == "ok"


@pytest.mark.asyncio
async def test_partial_failure_abort_lt_8(mock_anthropic_client):
    """2+ frames fallan → RuntimeError con mensaje claro indicando cuántos sobrevivieron."""
    call_count = [0]

    async def fail_two(**kwargs):
        call_count[0] += 1
        if call_count[0] in (2, 4):
            raise RuntimeError("Simulated 2-of-9 API failure")
        result = MagicMock()
        text_part = MagicMock()
        text_part.text = "ok response"
        result.content = [text_part]
        result.usage = MagicMock(input_tokens=10, output_tokens=20)
        return result

    mock_anthropic_client.messages.create = AsyncMock(side_effect=fail_two)

    with pytest.raises(RuntimeError, match=r"7/9"):
        await run_agents(mock_anthropic_client, "Pregunta de prueba")


def test_centroid_excludes_tenth(synthetic_embeddings_10):
    """centroid_of_9 debe computarse SOLO sobre los primeros 9, excluyendo el #10.

    Synthetic setup: 9 puntos clusterizan en una dirección, 1 outlier está lejos.
    Si el centroide incluye al #10, las distancias se diluyen y este test falla.
    """
    proj = project_mds(synthetic_embeddings_10)
    distances = proj["distance_to_centroid_of_9"]

    assert len(distances) == 10
    max_frame_dist = max(distances[:9])
    tenth_dist = distances[9]
    assert tenth_dist > max_frame_dist, (
        f"tenth-man distance ({tenth_dist:.3f}) debe exceder max frame distance "
        f"({max_frame_dist:.3f}). Si no, el centroide está contaminado por #10."
    )


# ──────────────────────────────────────────────────────────────────────────
# v0.5 — Reproducibility kit + embed-fix regression tests
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_temperature_is_zero(mock_anthropic_client):
    """Cada llamada Anthropic debe pasar ``temperature=0`` para reproducibilidad,
    excepto modelos en ``MODELS_WITHOUT_TEMPERATURE`` (Opus 4.7) que la
    rechazan por requerir extended thinking.

    Sin esto, mismo input produce verdict distinto entre corridas y la
    palabra "measurement" del README es marketing. v0.5 lo fija como
    decisión pre-registrada (ver WHITEPAPER.md §4).
    """
    from henge.agents import MODELS_WITHOUT_TEMPERATURE

    seen_calls = []
    original_create = mock_anthropic_client.messages.create

    async def capture(**kwargs):
        seen_calls.append((kwargs.get("model"), kwargs.get("temperature")))
        return await original_create(**kwargs)

    mock_anthropic_client.messages.create = AsyncMock(side_effect=capture)

    await run_agents(mock_anthropic_client, "Pregunta de prueba")

    assert TEMPERATURE == 0, "Module-level TEMPERATURE constant must be 0"

    # 9 frames + 1 tenth-man = 10 calls minimum
    assert len(seen_calls) == 10

    for model, temp in seen_calls:
        if model in MODELS_WITHOUT_TEMPERATURE:
            assert temp is None, (
                f"{model} rejects temperature; we must omit the kwarg, got {temp!r}"
            )
        else:
            assert temp == 0, (
                f"{model} must use temperature=0 for reproducibility; got {temp!r}"
            )


def test_project_mds_excludes_failed_frames():
    """project_mds(..., n_frames=8) debe centrar el centroide en 8 frames, no 9.

    Esto verifica el fix v0.5 al bug donde texts incluía stubs de frames
    fallidos al embedding. Con n_frames=8 + tenth, el centroide ignora
    cualquier frame fallido (que ya no se embebe).
    """
    import numpy as np

    rng = np.random.default_rng(7)
    # 8 frames cluster around +x, the tenth (last) is opposite
    cluster = rng.normal(0, 0.1, size=(8, 256))
    cluster[:, 0] += 1.0
    cluster = cluster / np.linalg.norm(cluster, axis=1, keepdims=True)
    tenth = rng.normal(0, 0.1, size=(1, 256))
    tenth[:, 0] -= 1.0
    tenth = tenth / np.linalg.norm(tenth, axis=1, keepdims=True)
    embeddings = np.vstack([cluster, tenth]).tolist()

    proj = project_mds(embeddings, n_frames=8)
    assert proj["n_frames"] == 8
    assert len(proj["distance_to_centroid_of_9"]) == 9  # 8 frames + tenth
    # Tenth must be furthest because the 8 cluster on one side
    distances = proj["distance_to_centroid_of_9"]
    assert distances[8] > max(distances[:8]), (
        "Tenth-man must be further from the centroid than any successful frame"
    )


def test_prompts_hash_stable():
    """``PROMPTS_HASH`` es determinístico — mismo prompt set → mismo hash.

    Persistido en cada report. Cualquier cambio a los .md cambia el hash;
    reports con hashes distintos no son directamente comparables.
    """
    import hashlib

    from henge.agents import FRAMES

    blob = "".join(PROMPTS[name] for name in [*FRAMES, TENTH_MAN]).encode("utf-8")
    expected = hashlib.sha256(blob).hexdigest()[:16]
    assert PROMPTS_HASH == expected
    assert len(PROMPTS_HASH) == 16
    # SHA256 hex prefix → only [0-9a-f]
    assert all(c in "0123456789abcdef" for c in PROMPTS_HASH)


def test_cost_breakdown_sums_components():
    """``total_cost`` retorna la suma exacta de Anthropic + embeddings.

    Regression contra v0.4 cost_usd hardcoded. cost_breakdown debe
    derivarse de uso real, no de un literal.
    """
    advisor_usages = [
        {"model": "claude-sonnet-4-6", "input_tokens": 1000, "output_tokens": 500},
        {"model": "claude-sonnet-4-6", "input_tokens": 1200, "output_tokens": 600},
        {"model": "claude-opus-4-7",   "input_tokens": 5000, "output_tokens": 2500},
    ]
    scoping = {"model": "claude-haiku-4-5-20251001", "input_tokens": 200, "output_tokens": 150}
    consensus = {"model": "claude-haiku-4-5-20251001", "input_tokens": 800, "output_tokens": 400}

    expected_anthropic = (
        anthropic_call_cost(advisor_usages[0])
        + anthropic_call_cost(advisor_usages[1])
        + anthropic_call_cost(advisor_usages[2])
        + anthropic_call_cost(scoping)
        + anthropic_call_cost(consensus)
    )

    breakdown = total_cost(
        advisor_usages=advisor_usages,
        scoping_usage=scoping,
        consensus_usage=consensus,
        embedding_model="text-embedding-3-small",
        embedding_input_tokens=2500,
    )

    assert abs(breakdown["anthropic_usd"] - round(expected_anthropic, 6)) < 1e-9
    assert breakdown["embedding_usd"] >= 0
    assert abs(
        breakdown["total_usd"]
        - round(breakdown["anthropic_usd"] + breakdown["embedding_usd"], 6)
    ) < 1e-9
    assert breakdown["pricing_version"] == HENGE_PRICING_VERSION


def test_no_hardcoded_cost_in_logic():
    """Regression: ``cost_usd = 0.65`` ya no debe aparecer como asignación literal.

    En v0.4 el cost vivía hardcoded en server.py. v0.5 lo deriva de usage real.
    Si alguien lo reintroduce, este test falla. Comentarios y docs pueden
    seguir mencionando 0.65 como rango histórico.
    """
    server_path = Path(__file__).parent.parent / "henge" / "server.py"
    text = server_path.read_text(encoding="utf-8")
    # We don't ban the literal 0.65 entirely (docs / comments may reference
    # historical costs). We ban the specific assignment pattern.
    forbidden_patterns = [
        "cost_usd = 0.65",
        'cost_usd= 0.65',
        'cost_usd=0.65',
    ]
    for pat in forbidden_patterns:
        assert pat not in text, (
            f"Regression: {pat!r} found in server.py. v0.5 derives cost from "
            f"actual token usage via henge.pricing.total_cost()."
        )


@pytest.mark.asyncio
async def test_k_runs_requires_temperature(monkeypatch):
    """k_runs > 1 sin run_temperature debe fallar con un error claro.

    K-runs es un modo de muestreo de varianza; con temperature=0 todas las
    corridas son idénticas y la distribución es degenerada. El error debe
    decirle al caller que pase run_temperature.
    """
    # Stub the validator so server import doesn't try to ping Anthropic.
    import henge.server as server

    result = await server.decide(
        question="X",
        context="Y",
        k_runs=5,
        run_temperature=None,
    )
    assert result["error"] == "k_runs_requires_temperature"
    assert "run_temperature" in result["reason"]


@pytest.mark.asyncio
async def test_k_runs_requires_context():
    """k_runs > 1 sin context (y sin skip_scoping) debe fallar.

    El modo K-runs salta scoping para no entrar en una recursión interactiva
    durante el muestreo. El caller debe haber recolectado context antes.
    """
    import henge.server as server

    result = await server.decide(
        question="X",
        context=None,
        skip_scoping=False,
        k_runs=3,
        run_temperature=0.7,
    )
    assert result["error"] == "k_runs_requires_context"


def test_compute_cfi_three_bins():
    """CFI clasifica tight clusters según distancia del tenth-man al cluster.

    Pre-registrado en docs/cfi-spec.md:
      - σ ≥ 0.03 → divided
      - else CFI < 0.33 → aligned-stable
      - else → aligned-fragile
    """
    # Tight cluster (σ ≈ 0.012), tenth close → aligned-stable, low CFI
    tight = [0.62, 0.63, 0.64, 0.64, 0.65, 0.65, 0.66, 0.67, 0.68]
    r = compute_cfi(tenth_distance=0.66, frame_distances=tight)
    assert r["cfi_bin"] == "aligned-stable"
    assert 0.0 <= r["cfi"] < 0.33
    assert r["sigma_9"] is not None and r["sigma_9"] < 0.03

    # Tight cluster, tenth pushed far → aligned-fragile, high CFI
    r = compute_cfi(tenth_distance=0.95, frame_distances=tight)
    assert r["cfi_bin"] == "aligned-fragile"
    assert r["cfi"] >= 0.33

    # Spread cluster (σ ≥ 0.03) → divided regardless of tenth
    spread = [0.50, 0.55, 0.60, 0.62, 0.65, 0.68, 0.72, 0.78, 0.85]
    r = compute_cfi(tenth_distance=0.90, frame_distances=spread)
    assert r["cfi_bin"] == "divided"
    assert r["sigma_9"] >= 0.03
