# Henge · Limits

This document is a list of things Henge **does not** measure, validate, or
claim. It is referenced from the README and the WHITEPAPER and exists so that
the marketing surface stays honest about what's load-bearing and what isn't.

If you find a limitation that belongs here and isn't, open an issue.

---

## 1 · Embedding distance is not propositional disagreement

Henge measures the cosine distance between text embeddings. Two responses can
phrase the **same** conclusion in different vocabulary and embed far apart.
Two responses can phrase **opposing** conclusions in similar style and embed
close. The embedding distance reflects lexical-semantic similarity, not
logical conflict.

Implication: a high CFI is necessary but not sufficient for "the dissent
contradicts the consensus on a substantive premise". Read the tenth-man
response itself before acting. CFI is a triage signal, not a conclusion.

## 2 · `text-embedding-3-small` is style-sensitive

The default embedding model encodes register and phrasing alongside meaning.
Frames that share a stylistic opener ("considering …", "the data shows …")
land closer to one another than their content alone would imply. This biases
the centroid toward shared vocabulary rather than shared reasoning.

Mitigation: Voyage `voyage-3-large` is opt-in and tends to be more
content-driven; semantic-only models (e.g. instructor-style) are on the
roadmap.

## 3 · Single-provider cognitive diversity

All ten advisors use Anthropic models. They share training corpora, RLHF
preference signals, and refusal patterns. The "diversity of perspectives"
delivered by Henge is largely *prompt-induced* — different system prompts on
the same backbone. Real cross-model heterogeneity (Gemini, GPT, local) would
likely produce structurally different distances.

Status: roadmap, post-v0.6.

## 4 · The tenth-man is not independent of the nine

By design, the tenth-man receives every successful frame's response and is
prompted to construct the strongest opposing case. Its position in embedding
space is therefore partly a self-fulfilling consequence of the prompt
("disagree with these"). This is a deliberate design decision — the tenth-man
is *reactive* steel-manning, not an eleventh frame — but it means CFI captures
*how far the dissenter was asked to go*, not just how far it actually went on
its own.

## 5 · MDS at N=10 is a chart, not analysis

Classical MDS over 10 points in 1024+ dimensions is illustrative. The 2-D
projection helps a human read the relative geometry; it does not justify any
quantitative claim about cluster structure beyond what the raw cosine
distances say. Distances reported by Henge are computed in the original
embedding space — the MDS layer is purely for visualisation.

## 6 · Verdict thresholds are pre-registered, not optimised

`TIGHT_SIGMA = 0.03`, `CFI_K = 6`, and `CFI_FRAGILE_THRESHOLD = 0.33` are
pre-registered constants (see [`docs/cfi-spec.md`](docs/cfi-spec.md)). They
were chosen as conservative defaults during v0.4–v0.5 development. They have
not been calibrated against a ground-truth benchmark because no benchmark
exists yet (see §10).

If the v0.6 Henge-50 benchmark suggests different thresholds, they will move
in a new spec version; reports stamped with the v0.5 spec remain valid for
that spec only.

## 7 · Cost is computed, not measured at the API edge

The `cost_breakdown` field in every report is derived from the `usage` field
returned by the Anthropic SDK and the published rate card encoded in
[`henge/pricing.py`](henge/pricing.py). If Anthropic or OpenAI changes
prices and we have not bumped the rate card, the recorded cost is wrong.
Every report records a `pricing_version` for traceability; for billing
purposes use the provider's invoice, not Henge's number.

The embedding cost line item is currently a **floor** — embedding token
counts are not yet propagated from the embed module. The total understates
the true cost by ~$0.0005/run. TODO v0.6.

## 8 · No reproducibility guarantee across embedding-model versions

Provider embedding models are versioned, and providers occasionally roll
silent updates. The `embed.model` field in each report records the model name
the run was issued against, but cannot guarantee bit-identity over time. Two
reports run against `text-embedding-3-small` six months apart may differ by a
small amount even with `temperature=0` on the Anthropic side.

## 9 · No privacy guarantees on persisted reports

Reports are written in plain JSON to `~/.henge/reports/`. They include the
full question and context (which may contain personal financials, employment
information, family details, etc.). There is no encryption, no auto-redaction,
and no TTL. If you do not want a question persisted, do not run it through
Henge — there is currently no opt-out path short of `rm` after the fact.

A no-persistence flag is on the roadmap for sensitive decisions.

## 10 · No outcome-validated benchmark yet

Henge's central marketing claim — that forced steel-man dissent surfaces
failure modes single-LLM review misses — is **not yet validated against
ground truth**. The v0.6 Henge-50 benchmark is the planned validation: 50
historical decisions with known outcomes, scored against Henge's tenth-man
output. Until then, treat Henge as a structural tool with a reproducible
metric, not a validated instrument of decision quality.

## 11 · Structural metric, not normative

CFI describes the relative position of the dissenter in the embedding
geometry of the ten responses. It does not measure:

- whether the consensus is correct
- whether the dissent is well-founded
- whether the user should follow the consensus or the dissent
- the magnitude of the stakes
- the reversibility of the decision

A high CFI on a low-stakes reversible decision is less actionable than a low
CFI on a one-way-door decision. Henge does not encode that distinction;
the user must.
