"""Embeddings (OpenAI default, Voyage opt-in) + classical MDS over pairwise cosine distance.

Why MDS not PCA: with N=10 in 1024+ dims (n<<d), PCA is statistically trivial —
first 2 components capture ~100% variance regardless of semantic content.
MDS preserves pairwise distances faithfully, which IS what a disagreement map needs.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.distance import pdist, squareform
from sklearn.manifold import MDS

CACHE_DIR = Path.home() / ".henge" / "embed_cache"

# One-time legacy-cache notice. v0.4 used cwd-relative ./.embed_cache which leaked
# between projects and missed on cwd changes. v0.5 moves to ~/.henge/embed_cache.
_LEGACY_CACHE = Path(".embed_cache")
if _LEGACY_CACHE.exists() and _LEGACY_CACHE.is_dir() and not os.environ.get("HENGE_LEGACY_CACHE_NOTICE_SHOWN"):
    print(
        f"⚠ Henge: legacy embed cache at {_LEGACY_CACHE.resolve()} ignored. "
        f"v0.5 caches at {CACHE_DIR}. Safe to delete the legacy dir.",
        file=sys.stderr,
    )
    os.environ["HENGE_LEGACY_CACHE_NOTICE_SHOWN"] = "1"


def _cache_key(text: str, provider: str, model: str) -> str:
    return hashlib.sha256(f"{provider}:{model}:{text}".encode()).hexdigest()


def _cached_embedding(text: str, provider: str, model: str):
    if not CACHE_DIR.exists():
        return None
    path = CACHE_DIR / f"{_cache_key(text, provider, model)}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return None
    return None


def _save_embedding(text: str, provider: str, model: str, embedding):
    CACHE_DIR.mkdir(exist_ok=True)
    path = CACHE_DIR / f"{_cache_key(text, provider, model)}.json"
    path.write_text(json.dumps(embedding))


def _embed_openai(texts, model="text-embedding-3-small"):
    from openai import OpenAI
    client = OpenAI()
    resp = client.embeddings.create(model=model, input=texts)
    return [d.embedding for d in resp.data]


def _embed_voyage(texts, model="voyage-3-large"):
    import voyageai
    client = voyageai.Client()
    resp = client.embed(texts=texts, model=model)
    return resp.embeddings


def _resolve_provider():
    """Return (provider, model, embed_fn). Default OpenAI for lower friction."""
    provider = os.getenv("EMBED_PROVIDER", "openai").lower()
    if provider == "voyage":
        return "voyage", "voyage-3-large", _embed_voyage
    return "openai", "text-embedding-3-small", _embed_openai


def embed_responses(texts):
    """Batch embed N texts. Returns dict {ok, embeddings?, provider, model, error?, reason?}.

    Errors propagate as structured dict, not raw exception, so MCP server returns
    a clear error to the client instead of a stack trace.
    """
    provider, model, embed_fn = _resolve_provider()

    embeddings = [_cached_embedding(t, provider, model) for t in texts]
    missing_idx = [i for i, e in enumerate(embeddings) if e is None]

    if missing_idx:
        try:
            new_embeds = embed_fn([texts[i] for i in missing_idx])
            for i, e in zip(missing_idx, new_embeds):
                embeddings[i] = e
                try:
                    _save_embedding(texts[i], provider, model, e)
                except Exception:
                    pass  # cache write is best-effort
        except Exception as exc:
            return {
                "ok": False,
                "error": "embed_failed",
                "reason": f"{provider}: {type(exc).__name__}: {exc}",
            }

    return {
        "ok": True,
        "embeddings": embeddings,
        "provider": provider,
        "model": model,
    }


def project_mds(embeddings, n_frames=None):
    """Classical MDS over pairwise cosine distance → 2D coords.

    Layout convention: embeddings are ordered [frame_0, ..., frame_{n-1}, tenth_man].
    The centroid is computed over the first ``n_frames`` (excluding the tenth-man).
    Distances are computed in the original embedding space using cosine distance —
    the MDS projection is for visualization only.

    Args:
        embeddings: list of M vectors. Last position must be the tenth-man.
        n_frames: number of frames at the head of ``embeddings`` (M-1 by default,
            i.e. last entry is tenth-man, all others are frames). v0.5 supports
            n_frames < 9 to handle partial-frame failures correctly — previously
            failed frames were embedded as their error stub, polluting the
            centroid.

    Returns:
        dict with ``coords_2d``, ``distance_to_centroid_of_9`` (legacy key —
        actually centroid of n_frames), and ``n_frames``.
    """
    arr = np.array(embeddings, dtype=float)
    m = arr.shape[0]
    if n_frames is None:
        n_frames = m - 1
    if n_frames < 1 or n_frames >= m:
        raise ValueError(
            f"n_frames must be in [1, {m - 1}] (got {n_frames}); "
            f"last embedding is reserved for the tenth-man."
        )

    cosine_distances = squareform(pdist(arr, metric="cosine"))

    mds = MDS(
        n_components=2,
        dissimilarity="precomputed",
        random_state=42,
        normalized_stress="auto",
        n_init=4,
    )
    coords_2d = mds.fit_transform(cosine_distances)

    centroid = arr[:n_frames].mean(axis=0)
    centroid_norm = centroid / (np.linalg.norm(centroid) + 1e-12)

    distances = []
    for vec in arr:
        v_norm = vec / (np.linalg.norm(vec) + 1e-12)
        cos_sim = float(np.dot(v_norm, centroid_norm))
        cos_sim = max(-1.0, min(1.0, cos_sim))
        distances.append(1.0 - cos_sim)

    return {
        "coords_2d": coords_2d.tolist(),
        "distance_to_centroid_of_9": distances,
        "n_frames": n_frames,
    }
