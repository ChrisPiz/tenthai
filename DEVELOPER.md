# Henge · Developer reference

Integration guide for developers and integrators. For the user-facing pitch, install instructions, and conceptual overview, see [README.md](README.md). The [Quickstart](README.md#quickstart--claude-code-30s) at the top of the README is enough for normal use — you only need this document if you are writing code against the Henge MCP server, hand-configuring it for a host other than Claude Code, or debugging a setup.

## Manual install

| Client          | Install                                          |
| --------------- | ------------------------------------------------ |
| Claude Code     | One-shot — see [Quickstart](README.md#quickstart--claude-code-30s) |
| Claude Desktop  | Manual config edit                               |
| Cursor          | Manual config edit                               |
| Anything else   | Manual `pip install -e .` + run as MCP server    |

All paths reach the same MCP server and call the same `decide` tool. Reports persist at `~/.henge/reports/` and the browseable `index.html` ledger auto-regenerates on every run.

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) and add the `henge` block under `mcpServers`. The server loads `~/Henge/.env` automatically, so `cwd` and inline `env` are not required:

```json
{
  "mcpServers": {
    "henge": {
      "command": "/Users/<you>/Henge/.venv/bin/python",
      "args": ["-m", "henge.server"]
    }
  }
}
```

Use the absolute path to the venv's Python — `~` is not expanded by every host. Quit Claude Desktop fully with **Cmd+Q** (closing the window only hides it; the process keeps running and won't reread the config) and reopen.

After restart, **Claude Desktop requires you to approve the new connector** before it actually starts the server. Open **Settings → Connectors** (or Extensions, depending on the version), find `henge` in the list, and enable/approve it. Editing the config file is not enough on its own. Once approved, the tool is available in any chat — but it does **not** show up as a `/decide` slash command. Ask your decision question in natural language ("Should I hire someone now?") and Claude will pick up the `decide` tool, or invoke it explicitly ("use the decide tool to analyze ...").

### Cursor

Add the same `mcpServers.henge` block to Cursor's MCP config (`Settings → MCP → Edit`).

### Any environment

```bash
git clone --single-branch --depth 1 https://github.com/ChrisPiz/Henge.git ~/Henge
cd ~/Henge
cp .env.example .env
# Open .env and fill in:
#   ANTHROPIC_API_KEY  (required — runs the 9 frames + tenth-man)
#   OPENAI_API_KEY     (embedding provider)

./setup                  # does Python detection, venv, pip install -e .,
                         # key validation, MCP registration, slash command
```

The `setup` script handles every step deterministically. If you'd rather run the pieces yourself: `python3.11 -m venv .venv && .venv/bin/pip install -e .` then register the MCP with your host of choice.

### Setup script flags (optional)

The Quickstart paste runs `./setup` with no flags — the script auto-detects every MCP host on the machine (Claude Code, Claude Desktop, Cursor) and registers Henge for each. Use these flags only to override that default.

```bash
./setup                          # default — auto-detect installed hosts (what the Quickstart runs)
./setup --host claude-code       # register only for Claude Code
./setup --host claude-desktop    # register only for Claude Desktop
./setup --host cursor            # register only for Cursor
./setup --host all               # register for every host even if not detected
./setup --skip-validate          # skip the API-key validation step
```

---

## Tool API

### `decide(question, context=None, skip_scoping=False)`

Two-phase. Phase 1 returns clarifying questions; phase 2 runs the ten advisors with the answers as context.

#### Phase 1 — scoping (default)

```jsonc
// call
{ "question": "Should I hire someone now?" }

// response
{
  "status": "needs_context",
  "questions": [
    "What is your approximate net monthly income?",
    "What's your runway in months?",
    "Is the role revenue-generating or cost-saving?",
    "..."
  ],
  "next_call_hint": "decide(question='...', context='<user answers formatted>')"
}
```

#### Phase 2 — run

```jsonc
// call
{
  "question": "Should I hire someone now?",
  "context": "Net income USD 2.6K / month, runway 8 months, role: senior engineer, ..."
}

// response: full disagreement-map JSON (see `Output structure` below)
```

#### Skip scoping

```jsonc
{ "question": "...", "skip_scoping": true }   // when the question already has rich context
```

---

## Example usage (agent)

```ts
const phase1 = await mcp.tools.decide({
  question: "Should I expand my business?"
})
// phase1.questions → present to user, collect answers

const phase2 = await mcp.tools.decide({
  question: "Should I expand my business?",
  context: "Revenue USD 2.6K, expenses 550, 8 months runway, ..."
})
// phase2.viz_path → opens HTML
// phase2.summary.consensus_state → drives downstream agent logic
```

---

## Output structure (v0.5.0)

```jsonc
{
  "viz_path": "/Users/you/.henge/reports/20260501-2247_should-i-hire-now/report.html",
  "report_id": "20260501-2247_should-i-hire-now",
  "report_dir": "/Users/you/.henge/reports/20260501-2247_should-i-hire-now",
  "consensus": "# Validate before hiring — asymmetric risk dominates\n\n## (1) Where the nine converge ...",
  "frames": [
    { "frame": "empirical",        "status": "ok", "distance": 0.046, "summary": "..." },
    { "frame": "first-principles", "status": "ok", "distance": 0.069, "summary": "..." }
    // 7 more
  ],
  "tenth_man": {
    "distance": 0.148,
    "response": "## §1 Facts I accept\n... ## §2 Where the consensus fails ..."
  },
  "summary": {
    // legacy (deprecated, kept until v1.0)
    "tenth_man_distance": 0.148,
    "max_frame_distance": 0.085,
    "consensus_state": "aligned-stable",
    "consensus_fragility": "Advisors aligned — dissent sounds reasonable but consensus holds.",
    "n_frames_succeeded": 9,
    "embed_provider": "openai",
    "embed_model": "text-embedding-3-small",

    // v0.5 — Consensus Fragility Index, pre-registered in docs/cfi-spec.md
    "cfi": 0.198,
    "cfi_bin": "aligned-stable",        // "aligned-stable" | "aligned-fragile" | "divided"
    "mu_9": 0.063,
    "sigma_9": 0.018,
    "henge_version": "0.5.0",
    "prompts_hash": "3bb5924c03e4c761",

    // present only when k_runs > 1
    "k_runs_distribution": null
  },
  "cost_breakdown": {
    "anthropic_usd": 0.4203,
    "embedding_usd": 0.000050,
    "total_usd":     0.420350,
    "pricing_version": "2026-05-01"
  },
  "cost_usd": 0.420350    // deprecated alias of cost_breakdown.total_usd, kept until v1.0
}
```

The persisted `report.json` adds `runtime` (model versions, temperature, prompts_hash) and `usage` (per-call token counts) blocks; see `henge/server.py` for the full payload shape. `schema_version` was bumped from `"1"` (v0.4) to `"2"` (v0.5).

The HTML at `viz_path` ships with the disagreement map, sortable frames table, consensus card, Tenth Man dissent (built via steel-manning), the new CFI/σ line under the verdict card, and a per-run hero painting bundled inside `report_dir/assets/`.

### K-runs mode (v0.5)

```jsonc
// call
{ "question": "...", "context": "...", "k_runs": 5, "run_temperature": 0.7 }

// response.summary.k_runs_distribution
{
  "k_requested": 5,
  "k_completed": 5,
  "run_temperature": 0.7,
  "cfi_mean": 0.214,
  "cfi_stddev": 0.041,
  "cfi_ci95_half_width": 0.036,
  "cfi_samples": [0.198, 0.272, 0.183, 0.241, 0.176],
  "bin_distribution": { "aligned-stable": 5 },
  "total_cost_usd": 2.08,
  "errors": []
}
```

K-runs > 1 requires `run_temperature > 0` and `context` (or `skip_scoping=True`); see `WHITEPAPER.md` §4 and `METHODOLOGY.md` §6.

---

## Reports & ledger

Each run writes:

```
~/.henge/reports/
  20260501-224712_should-i-hire-now/
    report.html       # full editorial visualization
    report.json       # canonical record (question, context, 10 responses, distances, summary)
    assets/
      header-v2.jpg   # bundled hero painting
  index.html          # auto-regenerated ledger of every past report
```

The JSON is the source of truth. The HTML is a pure render of it — delete a directory and it disappears from the ledger on the next run.

---

## Architecture

```
henge/
  agents.py        # 9 frames in parallel + tenth-man sequencing
  embed.py         # provider-agnostic embeddings + classical MDS
  scoping.py       # 4–7 clarifying questions (Haiku)
  consensus.py     # synthesis of the nine (Haiku)
  viz.py           # editorial HTML report + disagreement map SVG
  storage.py       # report.json + report.html + ledger
  server.py        # MCP entrypoint
  prompts/         # 10 cognitive-frame markdowns
  assets/          # bundled hero painting
```

---

## Embeddings · provider config

Henge needs to compute distance between the 10 advisor responses to draw the disagreement map, and that requires **embeddings** (text → vector). Anthropic does not currently offer an embeddings API, so a second provider is unavoidable for the math layer.

**OpenAI `text-embedding-3-small`** — ~USD 0.0005/run. Most devs already have a key.

A local-embeddings option (no API key, sentence-transformers on-device) is on the [Roadmap](README.md#roadmap).

---

## MCP integration

Henge speaks Model Context Protocol. Any MCP-compatible client can drive it as a reasoning tool.

Tested with:

- **Claude Code** (one-shot install)
- **Claude Desktop** (manual config)
- **Cursor** (manual config)
- Any other MCP-compatible agent or local AI pipeline

---

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `/decide` says "Henge MCP server doesn't appear to be connected" | Quit every `claude` session and reopen. If still failing → next row. |
| `claude mcp list` shows `henge ✗ Failed` | Run `~/Henge/.venv/bin/python -m henge.server </dev/null` interactively to see the real error. Most common cause: the editable install was skipped — `cd ~/Henge && .venv/bin/pip install -e .` and re-register. |
| `ModuleNotFoundError: No module named 'henge'` | Editable install missing. `cd ~/Henge && .venv/bin/pip install -e .` |
| `git clone` fails with "destination already exists" | The repo is already there. `cd ~/Henge && git pull --ff-only`. |
| `pyenv install` shows an `lzma` warning | Non-fatal, ignore. (Optional cleanup: `brew install xz` and re-run.) |
| Server validates keys then exits immediately | Expected. It's a stdio MCP server; without a client on stdin, it shuts down once `✓ keys validated` is printed. |
| `claude mcp add` rejects the path with $HOME | Pass an absolute path: `~/Henge/.venv/bin/python` (Claude Code expands `~`, but other shells re-expand `$HOME` after registration). |
