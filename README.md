# TenthAI MCP · Structured Dissent for AI Agents

TenthAI MCP is a Model Context Protocol server that helps AI agents avoid premature consensus.

It runs multiple cognitive frames over a decision, measures alignment, and generates structured dissent only when needed.

> Agreement is not a signal. It's just coherent noise — unless you measure it.

---

## What it does

TenthAI MCP gives compatible AI clients a tool for decision stress-testing.

Instead of asking one model for one answer, it:

1. Generates multiple cognitive perspectives
2. Measures agreement between them
3. Detects whether consensus is strong, weak, or fragmented
4. Produces a steel-man dissent when useful
5. Returns a structured decision report

---

## Why MCP

MCP makes TenthAI available as a reusable reasoning tool inside:

- Claude Desktop
- Cursor
- local AI workflows
- agent builders
- custom orchestration systems

The goal is not to replace the main AI assistant.

The goal is to give it a specialized tool for:

- avoiding groupthink
- questioning consensus
- comparing assumptions
- improving decision quality

---

## Setup

**1. Clone and install dependencies**

```bash
git clone https://github.com/ChrisPiz/TenthAI-MCP.git
cd TenthAI-MCP
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**2. Configure API keys**

```bash
cp .env.example .env
# Edit .env:
#   ANTHROPIC_API_KEY  (required — runs the 9 frames + the tenth-man)
#   OPENAI_API_KEY     (default embedding provider; cheaper, most devs already have one)
#   VOYAGE_API_KEY     (optional — better quality for Spanish; uncomment EMBED_PROVIDER=voyage)
```

Verify keys:

```bash
python -m tenthai.server   # should print "✓ keys validated" then wait for stdio
```

**3. Register the MCP server with Claude Code**

```bash
claude mcp add -s user tenthai \
  "$(pwd)/.venv/bin/python" -- -m tenthai.server
```

The `-s user` flag makes it available globally (any project). Drop the flag to scope it to the current directory only.

Or, if you prefer editing config by hand, add to `~/.claude.json` (or your client's `mcp.json`):

```json
{
  "mcpServers": {
    "tenthai": {
      "command": "/absolute/path/to/TenthAI-MCP/.venv/bin/python",
      "args": ["-m", "tenthai.server"]
    }
  }
}
```

Restart Claude Code (or your MCP client). Verify with `claude mcp list` — `tenthai` should report `✓ Connected`.

**4. Optional: add a `/decidir` slash command**

```bash
mkdir -p ~/.claude/commands
cat > ~/.claude/commands/decidir.md <<'MD'
---
description: Invokes TenthAI — disagreement map of 9 advisors + 1 dissenter.
---
Use the `decide` MCP tool from the `tenthai` server to analyze: $ARGUMENTS

When the JSON returns: cite `viz_path`, summarize the consensus first,
list the 9 advisors' conclusions, then quote the tenth-man verbatim.
MD
```

**5. Run the tests (optional)**

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

5 critical tests on design invariants + 2 smoke tests + provider-error handling. Suite runs in <5s with mocked SDK calls.

---

## Core principle

TenthAI does not blindly contradict.

If there is no real consensus, forcing disagreement only adds noise.

The tenth-man activates when the system detects meaningful alignment between the other frames.

---

## Available tool

### `tenthai_analyze`

Runs a structured dissent analysis over a user question.

**Input:**

```json
{
  "question": "Should I hire someone or keep working alone in my business?",
  "context": "Monthly revenue is CLP 2.4M. Hiring would cost around CLP 500K/month. I have family expenses and limited runway."
}
```

**Output:**

```json
{
  "consensus_strength": "weak",
  "most_aligned_frame": "first-principles",
  "most_divergent_frame": "analogical",
  "tenth_man_activated": false,
  "verdict": "No strong consensus detected. Do not force dissent.",
  "recommendation": "Validate whether the operational bottleneck is truly limiting revenue before hiring."
}
```

---

## Cognitive frames

TenthAI can reason through frames such as:

- empirical
- historical
- first-principles
- systemic
- ethical
- analogical
- soft-contrarian
- radical-optimist
- pre-mortem
- tenth-man

---

## Compared to simple prompting

| Approach | Problem | TenthAI MCP |
|----------|---------|-------------|
| Single prompt | One confident answer | Multiple frames |
| Multi-agent debate | Often noisy | Measures agreement |
| Devil's advocate | Always contradicts | Conditional dissent |
| Tenth-man rule | Fixed opposition | Data-driven dissent |

---

## Use cases

- Founder decisions
- Product strategy
- Hiring and investment decisions
- Risk analysis
- Agent orchestration
- Pre-mortems
- High-uncertainty choices

---

## Not goals

TenthAI MCP is not:

- a chatbot
- a debate simulator
- a generic agent framework
- a replacement for judgment

It is a focused reasoning tool for structured disagreement.

---

## Example

User asks:

> Should I hire someone for my 3D printing business?

TenthAI MCP may produce:

> The nine frames converge around caution:
> validate demand before creating a fixed cost.
>
> The tenth-man challenges that:
> waiting for perfect validation may be the mechanism that keeps the founder stuck in operational work.
>
> Final verdict:
> externalize first, measure impact, then convert to a fixed role only if time liberated becomes measurable revenue.

---

## Roadmap

- MCP tool schema refinement
- Consensus strength scoring
- Dissent impact scoring
- HTML/PDF report export
- Embedding-based disagreement map
- Claude Desktop / Cursor usage examples

---

## License

MIT
