# Henge · Methodology

Step-by-step reproducible protocol. Anyone with the API keys, the same Henge
release, the same `prompts_hash`, and `temperature=0` should be able to
re-run a question and produce a CFI within numerical noise of the original.

---

## 1 · Prerequisites

- Python ≥ 3.11
- `ANTHROPIC_API_KEY` (required)
- `OPENAI_API_KEY` (default embedding provider) **or** `VOYAGE_API_KEY` with
  `EMBED_PROVIDER=voyage`
- Henge installed from the repo at a known SHA, or `henge-mcp==X.Y.Z` from
  PyPI (planned v0.6+)

The simplest path: see the [Quickstart](README.md#quickstart) in the README.

## 2 · Reproducibility envelope

A Henge run is reproducible **only** within this envelope:

| Dimension                | Pinned in v0.5                                    |
|--------------------------|---------------------------------------------------|
| `temperature`            | `0` (see WHITEPAPER §4)                           |
| Anthropic model versions | `claude-sonnet-4-6`, `claude-opus-4-7`, `claude-haiku-4-5-20251001` |
| Embedding model          | `text-embedding-3-small` (default)                |
| Prompt set               | identified by `prompts_hash` SHA-256 prefix       |
| MDS init                 | `random_state=42`, `n_init=4` (viz only)          |
| Henge release            | identified by `henge_version` field in report.json|
| CFI spec                 | `cfi/2026-05-01` (see `docs/cfi-spec.md`)         |

If any of these change between runs, the runs are not directly comparable.

## 3 · Protocol

```
Step 1 · Caller sends:
   decide(question="…")

Step 2 · Henge returns:
   {status: "needs_context", questions: [4–7 clarifying questions]}

Step 3 · Caller surfaces those to the user, collects answers, and re-calls:
   decide(question="…", context="…answers…")

Step 4 · Henge runs in this exact order:
   - 9 frames in parallel (asyncio.gather), Sonnet 4.6, temperature=0
   - if 8/9 succeed → continue, else abort with structured error
   - consensus synthesis from successful frames, Haiku 4.5, temperature=0
   - tenth-man steel-man over the successful frames, Opus 4.7, temperature=0
   - embed only the successful frames + tenth-man (NOT the failed stub texts)
   - cosine distances to centroid of the n successful frames
   - classical MDS for the 2-D scatter (visual only)
   - compute CFI per docs/cfi-spec.md
   - persist report.json + report.html under ~/.henge/reports/{id}/
   - return summary JSON to caller

Step 5 · Caller may inspect:
   - viz_path → HTML editorial report
   - json_path → canonical record
   - summary.cfi, summary.cfi_bin, summary.sigma_9, summary.mu_9
   - cost_breakdown.{anthropic_usd, embedding_usd, total_usd, pricing_version}
   - runtime.{henge_version, model_versions, prompts_hash, temperature}
```

## 4 · Manual reproducibility check

```bash
# Run the same question twice with the same release and key set:
/decide should I take the new job?
# answer the scoping questions
# wait for report

# Open report 1: ~/.henge/reports/{id1}/report.json → record summary.cfi
# Open report 2: ~/.henge/reports/{id2}/report.json → record summary.cfi

# Expected (temperature=0): summary.cfi differs by < 0.05 between runs.
# The only legitimate source of drift is MDS random_state on degenerate
# embeddings — which only affects visualisation, not the cosine distances
# CFI is computed from. If you see a wider drift, file an issue.
```

## 5 · Comparing two reports

Two reports are **directly comparable** iff:

```
report_a.runtime.henge_version    == report_b.runtime.henge_version
report_a.runtime.prompts_hash      == report_b.runtime.prompts_hash
report_a.runtime.model_versions    == report_b.runtime.model_versions
report_a.runtime.embed.model       == report_b.runtime.embed.model
report_a.runtime.temperature       == report_b.runtime.temperature
report_a.cost_breakdown.pricing_version == report_b.cost_breakdown.pricing_version
```

If any field differs, you can still inspect the reports side by side, but
treat the CFI comparison as cross-version, not cross-run.

## 6 · Building a benchmark (v0.6, planned)

Henge-50 will be a CSV of 50 historical decisions with known outcomes:

```
id, year, question, context, ground_truth_outcome, source
1, 2000, "Should Blockbuster acquire Netflix for $50M?", "...", "decline (bankruptcy 2010)", "..."
...
```

Validation is not part of v0.5.0. The methodology, when it lands, will be:

1. Run Henge over each row with `skip_scoping=True` (context is the
   pre-collected case description, no live scoping).
2. Record CFI, consensus net-lean, and tenth-man failure-mode titles.
3. Score:
   - did the consensus net-lean match the historical outcome?
   - did any tenth-man failure mode describe the actual failure that
     materialised?
4. Aggregate over the 50 cases. Report point estimate + 95% CI.

The benchmark will be public so anyone can replicate.

## 7 · Failure modes of the protocol itself

This is not the same as §11 (LIMITS.md) — these are operational failure
modes:

- **Fewer than 8 frames succeed.** Run aborts with a structured error
  identifying the failed frames. Cost is partial (frames that ran are
  billed). Re-run after addressing the API issue.
- **Embed provider down.** Run aborts after frames + tenth-man complete;
  cost is full Anthropic + 0 embedding. The user gets the textual responses
  but no map / no CFI. Future versions will degrade gracefully to
  text-only mode.
- **Same question, different runs, different verdicts.** Should not happen
  with `temperature=0`. If it does:
  1. Confirm `runtime.temperature == 0` in both reports.
  2. Confirm `prompts_hash` matches.
  3. Confirm `model_versions` match.
  4. Confirm `embed.model` matches.
  If all match and verdicts differ, file an issue with both `report.json`
  files attached.
