# TenthAI

> Map the disagreement between 9 AI agents + 1 obligatory dissenter.

Multi-agent MCP server. Your question → 9 cognitive frames + 1 steel-man dissenter → 2D map of the response space.

Inspired by the **tenth man rule** (Israeli intelligence post-Yom Kippur, popularized in *World War Z*): if 9 advisors agree, the 10th is OBLIGATED to dissent and build the coherent counter-case.

The output is not an answer. It's a visual map: you see where consensus is robust and where it's fragile.

## Quick install (5 min)

```bash
git clone https://github.com/ChrisPiz/tenthai.git
cd tenthai
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with ANTHROPIC_API_KEY (required) + OPENAI_API_KEY (default embed)
python -m tenthai.server  # should print "✓ keys validated"
```

Voyage is optional for better Spanish-language quality: uncomment `EMBED_PROVIDER=voyage` and `VOYAGE_API_KEY=...` in `.env`.

## Configure Claude Code

Edit `~/.config/claude-code/mcp.json`:

```json
{
  "mcpServers": {
    "tenthai": {
      "command": "python",
      "args": ["-m", "tenthai.server"],
      "cwd": "/path/to/TenthAI"
    }
  }
}
```

Restart Claude Code.

## How to invoke

**Option A — `/decide` slash command (recommended):**

Create `~/.claude/commands/decide.md` with this content:

```markdown
---
description: Invokes TenthAI — disagreement map of 9 frames + 1 dissenter.
---
Use the `decide` MCP tool from the `tenthai` server to analyze:

$ARGUMENTS

When you receive the JSON: cite `viz_path`, summarize the consensus of the 9, quote the 10th verbatim, report `tenth_man_distance` and `max_frame_distance`. Do not interpret the decision for the user.
```

Then from any project in Claude Code:

```
/decide whether to charge USD 4k or 6k for the Acme contract
```

**Option B — free-form prompt:**

Since it's an MCP tool, you can also ask Claude to use it without a slash command:

- "**Use TenthAI to help me decide** whether to accept the Acme contract."
- "**With TenthAI**, evaluate whether this PR's architecture is correct."
- "**Run TenthAI on**: Postgres or DynamoDB for this workload?"

After ~60-150s, the browser opens with the 2D map showing 9 frames + the dissenter.

## What it returns

The `decide()` tool returns JSON with:

- `viz_path` — absolute path to the HTML (auto-opens in browser).
- `responses` — 10 entries: role, frame, status, distance_to_centroid_of_9, embedding_2d, response.
- `summary` — tenth_man_distance, max_frame_distance, n_frames_succeeded, embed_provider.
- `cost_clp` — approximate cost in CLP.

## The 9 frames + 1

Each frame produces a distinct angle on your question:

1. **Empirical** — data, base rates, evidence.
2. **Historical** — precedent, analogous cases.
3. **First principles** — basic physical/economic atoms.
4. **Analogical** — cross-domain (biology, military, finance).
5. **Systemic** — second-order effects, feedback loops.
6. **Ethical** — deontological vs consequentialist.
7. **Soft-contrarian** — challenges one assumption without inverting everything.
8. **Radical optimist** — the 10× better case.
9. **Pre-mortem** — assume it already failed, describe why.
10. **Tenth man** — steel-man of the dissent against the consensus of the 9.

## Cost

~USD 0.30-0.60 per invocation. Logged in every output.

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

5 critical tests on design invariants + 2 smoke tests + provider-error handling. Suite runs in <5s with mocked SDK calls.

## Limitations

- **MDS not PCA:** The map uses classical MDS over cosine distance. This preserves pairwise distances faithfully (better than PCA with N=10 in high dim, which is statistically trivial). Still, validate the distance ranking against your own human judgment on the first 3 invocations.
- **MVP scope:** no persistence, no streaming, no auto-tool-use across the 9 agents. Each invocation is independent.
- **Only tested on Claude Code.** Other MCP clients should work (standard stdio transport) but are not validated.

## License

MIT.
