# Changelog

All notable changes to Henge are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to semantic versioning once it reaches 1.0. Pre-1.0 versions may
introduce additive fields freely; field removals or breaking changes are
documented under **Removed** with migration notes.

---

## [0.5.0] — 2026-05-01

The "Validity + paper" release. Adopts a DORA-style hybrid model: rigor
academic mínimo (paper + límites declarados + reproducibilidad) + marketing
surface intacto (Tenth Man, mapa, ritual). All output JSON changes are
**additive with soft deprecation** — existing integrations continue to work.

### Added

- **Consensus Fragility Index (CFI)** — pre-registered scalar 0–1 metric
  surfaced in every report. Spec: [`docs/cfi-spec.md`](docs/cfi-spec.md).
  New summary fields: `cfi`, `cfi_bin`, `mu_9`, `sigma_9`.
- **Real cost accounting** via `henge.pricing`. Reports now include
  `cost_breakdown.{anthropic_usd, embedding_usd, total_usd, pricing_version}`
  derived from the `usage` field returned by the Anthropic SDK. Replaces
  the v0.4 hardcoded `cost_usd = 0.65`.
- **Runtime metadata** in every report under `runtime`: `henge_version`,
  `temperature`, `model_versions`, `embed.{provider, model}`,
  `prompts_hash`, `n_frames_succeeded`, `n_frames_embedded`. Persisted so
  any future reader can reproduce the run.
- **Per-call usage** under `usage.per_advisor`, `usage.scoping`,
  `usage.consensus`, `usage.embedding`. Token counts come straight from
  the SDK.
- **`PROMPTS_HASH`** — SHA-256 prefix over the ordered concat of the 10
  prompt files. Persisted in every report so prompt drift is detectable.
- **WHITEPAPER.md** — v0.5.0 specification of the Structured Dissent
  Protocol (SDP), pre-registered runtime decisions, validation plan.
- **LIMITS.md** — declared list of what Henge does *not* measure, validate,
  or claim. Linked from README and WHITEPAPER.
- **METHODOLOGY.md** — reproducible step-by-step protocol, reproducibility
  envelope, comparison rules between reports.
- **MANIFESTO.md** — the poetic / philosophical framing previously
  embedded in the README.
- **`docs/cfi-spec.md`** — formal CFI specification with worked examples.
- **CI** — GitHub Actions workflow at `.github/workflows/test.yml` running
  pytest on Python 3.11 and 3.12 across push and pull request.
- **6 new tests** — `test_temperature_is_zero`,
  `test_project_mds_excludes_failed_frames`, `test_prompts_hash_stable`,
  `test_cost_breakdown_sums_components`, `test_no_hardcoded_cost_in_logic`,
  `test_compute_cfi_three_bins`.

### Changed

- **`temperature=0` pinned** in every Anthropic call (frames, scoping,
  consensus, tenth-man). Reproducibility > stylistic variance — the
  pre-registered choice is documented in `WHITEPAPER.md` §4.
- **Embedding cache directory** moved from cwd-relative `./.embed_cache`
  to absolute `~/.henge/embed_cache`. The legacy directory is ignored
  with a one-time stderr notice; safe to delete.
- **`run_agents` return shape** is now a list of
  `(frame, response, status, usage)` 4-tuples (was 3-tuple). The fourth
  element is the SDK `usage` dict for `status == "ok"` and `None` for
  `status == "failed"`. Tests using positional indexing (`r[2]`) keep
  working.
- **`generate_questions` and `synthesize_consensus` return shape** are
  now `(value, usage)` tuples instead of bare value. On failure both
  return `(None, None)`.
- **`project_mds(embeddings, n_frames=None)`** accepts variable frame
  counts. When `n_frames < len(embeddings) - 1`, the tenth-man is
  always the last embedding by convention; previous fixed `n_frames=9`
  behaviour is the default when omitted.
- **README.md** rewritten as academic/corporate interface. Manifesto-tone
  content moved to MANIFESTO.md. Link surface added to WHITEPAPER, LIMITS,
  METHODOLOGY, MANIFESTO, and CFI spec.
- **`schema_version`** in `report.json` bumped from `"1"` to `"2"`.
  All v0.4 fields remain present; v0.5 adds the new metadata blocks.
- **`storage.py` ledger label** bumped from `v0.4` to `v0.5`.

### Fixed

- **Embedding bug** (server.py): when 1–2 frames failed (allowed by the
  8/9 minimum), their `"[failed: …]"` stub text was being embedded
  alongside the successful responses, polluting the centroid and silently
  corrupting all distances. v0.5 embeds only the successful frames + the
  tenth-man and maps distances back to a length-10 list with `None` for
  failed slots.
- **`most_divergent_frame` / `closest_frame` lookup** previously used
  `frame_distances.index(value)` which can return the wrong index on tied
  distances. Now uses explicit `(index, value)` pairs.
- **Opus 4.7 temperature rejection.** Initial v0.5 release pinned
  `temperature=0` on every Anthropic call, but Opus 4.7 (reasoning tier
  with extended thinking on by default) refuses the parameter. Henge now
  omits `temperature` for models in `henge.agents.MODELS_WITHOUT_TEMPERATURE`
  (currently `{claude-opus-4-7}`) and falls back to a no-temperature retry
  when an unknown model surfaces a temperature-related API error. Trade-off
  documented in `WHITEPAPER.md` §4 — the Opus tenth-man is no longer
  bit-reproducible, but the CFI bin remains stable in practice.

### Deprecated

These fields stay in the response and report payload through v0.x and will
be removed in v1.0. Migration guidance below; new integrations should use
the v0.5 replacements.

| Deprecated field            | Replacement                          |
|-----------------------------|--------------------------------------|
| `summary.consensus_state`   | `summary.cfi_bin`                    |
| `summary.consensus_fragility` | derive from `cfi_bin` + locale     |
| `cost_usd` (top-level)      | `cost_breakdown.total_usd`           |

The legacy verdict thresholds (`TIGHT_SIGMA = 0.03`, `DISSENT_SIGMA = 3.0`
in `viz.py`) continue to drive `consensus_verdict`. The v0.5 CFI uses the
same `TIGHT_SIGMA` floor for the `divided` bin so the new and old verdicts
agree on tri-state classification within numerical tolerance.

---

## [0.4.0] — 2026-04 (pre-CHANGELOG)

Last v0.4 release. The CHANGELOG was introduced in v0.5; for prior history
see `git log` and the GitHub release notes.
