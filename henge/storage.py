"""Persistence for Henge reports — HTML + JSON per run + browseable index.

Layout (under HENGE_REPORTS_DIR or ~/.henge/reports):

    20260430-143559_should-i-leave-pm-job/
        report.html       # full editorial visualization
        report.json       # raw data (question, context, 10 responses, distances, summary)
        assets/
            header-painting.png  # hero background, copied from package on each run
    index.html            # auto-regenerated browseable ledger of all reports

The JSON is the canonical record. The HTML is a rendered view of it. The index
is rebuilt from scratch every time write_index() runs, so deleting a report
directory removes it from the ledger on the next invocation.
"""
import html as html_mod
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from .viz import detect_locale

REPORTS_DIR = Path(os.environ.get("HENGE_REPORTS_DIR", "~/.henge/reports")).expanduser()
PACKAGE_ASSETS_DIR = Path(__file__).parent / "assets"


# ───────── Index locale ─────────
# Resolution order:
#   1. HENGE_LOCALE env var, if set to en|es.
#   2. Locale of the most recent report's question (consistency with what the
#      user just generated).
#   3. System locale (LANG / LC_ALL) — es* → es, else en.
#   4. Fallback en.

INDEX_TRANSLATIONS = {
    "en": {
        "title": "Henge · Decision history",
        "eyebrow": "Ledger · disagreement maps",
        "h1_a": "Past ",
        "h1_em": "decisions",
        "h1_tail": ".",
        "sub": "Every disagreement map you've generated. Nine voices aligned aren't signal — just coherent noise. Newest first.",
        "th_date": "Date",
        "th_question": "Question",
        "th_verdict": "Verdict",
        "th_d10": "d 10",
        "open": "open ↗",
        "empty_a": "No decisions recorded yet. Run ",
        "empty_code": "/decidir",
        "empty_b": " in Claude Code to create your first report.",
        "count_singular": "report",
        "count_plural": "reports",
        "updated": "updated",
        "verdict_aligned": "aligned",
        "verdict_fragile": "fragile consensus",
        "verdict_divided": "divided",
        "version_label": "v0.5",
    },
    "es": {
        "title": "Henge · Historial de decisiones",
        "eyebrow": "Registro · mapas de desacuerdo",
        "h1_a": "Decisiones ",
        "h1_em": "anteriores",
        "h1_tail": ".",
        "sub": "Cada mapa de desacuerdo que has generado. Nueve voces alineadas no son señal — son ruido coherente. Los más recientes primero.",
        "th_date": "Fecha",
        "th_question": "Pregunta",
        "th_verdict": "Veredicto",
        "th_d10": "d 10",
        "open": "abrir ↗",
        "empty_a": "Aún no hay decisiones registradas. Ejecuta ",
        "empty_code": "/decidir",
        "empty_b": " en Claude Code para crear tu primer reporte.",
        "count_singular": "reporte",
        "count_plural": "reportes",
        "updated": "actualizado",
        "verdict_aligned": "alineado",
        "verdict_fragile": "consenso frágil",
        "verdict_divided": "disperso",
        "version_label": "v0.5",
    },
}


def _detect_index_locale(records: list) -> str:
    forced = os.environ.get("HENGE_LOCALE", "").strip().lower()
    if forced in ("en", "es"):
        return forced
    if records:
        latest_question = records[0].get("question", "")
        if latest_question:
            return detect_locale(latest_question)
    sys_locale = (os.environ.get("LC_ALL") or os.environ.get("LANG") or "").lower()
    if sys_locale.startswith("es"):
        return "es"
    return "en"


def _it(locale: str, key: str) -> str:
    return INDEX_TRANSLATIONS.get(locale, INDEX_TRANSLATIONS["en"]).get(key, key)


def slugify(question: str, max_len: int = 60) -> str:
    """Lowercase ASCII slug for filesystem use. Strips accents to plain letters."""
    text = question.lower()
    # Strip common Spanish accents to keep filesystem-friendly slugs
    accent_map = str.maketrans("áéíóúñü", "aeiounu")
    text = text.translate(accent_map)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text or "report"


def make_report_id(question: str) -> str:
    """Returns ``{YYYYMMDD-HHMMSS}_{slug}`` — collision-resistant within one second."""
    return f"{datetime.now().strftime('%Y%m%d-%H%M%S')}_{slugify(question)}"


def make_report_dir(report_id: str) -> Path:
    path = REPORTS_DIR / report_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_record(report_dir: Path, html: str, payload: dict) -> tuple[Path, Path]:
    """Writes ``report.html`` + ``report.json`` into report_dir. Returns both paths.

    Also copies the static hero painting from the package into ``report_dir/assets/``
    so the relative ``assets/header-painting.png`` reference in the rendered HTML
    resolves regardless of where the report is opened from.
    """
    html_path = report_dir / "report.html"
    json_path = report_dir / "report.json"
    html_path.write_text(html, encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    assets_dir = report_dir / "assets"
    assets_dir.mkdir(exist_ok=True)
    painting_src = PACKAGE_ASSETS_DIR / "header-painting.jpg"
    if painting_src.exists():
        shutil.copyfile(painting_src, assets_dir / "header-painting.jpg")

    return html_path, json_path


def list_records() -> list:
    """Scan REPORTS_DIR for ``report.json`` files. Returns desc by timestamp.

    Malformed JSON is skipped silently — the ledger should not break because
    of a corrupted run.
    """
    if not REPORTS_DIR.exists():
        return []
    records = []
    for json_path in sorted(REPORTS_DIR.glob("*/report.json")):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        # Stamp the on-disk dir name so we can build relative links even
        # if the in-file id drifts from the directory name.
        data["_dir"] = json_path.parent.name
        records.append(data)
    records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return records


def _format_row(record: dict, locale: str) -> str:
    rid = record.get("_dir") or record.get("id", "")
    ts = record.get("timestamp", "")
    try:
        dt = datetime.fromisoformat(ts)
        date_str = dt.strftime("%Y·%m·%d")
        time_str = dt.strftime("%H:%M")
    except Exception:
        date_str = ts[:10] if ts else "—"
        time_str = ts[11:16] if len(ts) > 11 else ""

    question = record.get("question", "")
    if len(question) > 110:
        question = question[:108].rsplit(" ", 1)[0] + "…"

    summary = record.get("summary", {})
    state = summary.get("consensus_state")
    fragility = summary.get("consensus_fragility", "—")
    state_to_key = {
        "aligned-stable": "verdict_aligned",
        "aligned-fragile": "verdict_fragile",
        "divided": "verdict_divided",
    }
    if state in state_to_key:
        verdict = _it(locale, state_to_key[state])
        verdict_state = state
    else:
        lowered = fragility.lower()
        if "frágil" in lowered or "fragile" in lowered:
            verdict = _it(locale, "verdict_fragile")
            verdict_state = "aligned-fragile"
        elif "alineados" in lowered or "aligned" in lowered:
            verdict = _it(locale, "verdict_aligned")
            verdict_state = "aligned-stable"
        elif "divididos" in lowered or "divided" in lowered or "moderate" in lowered:
            verdict = _it(locale, "verdict_divided")
            verdict_state = "divided"
        else:
            verdict = fragility[:32]
            verdict_state = "unknown"

    tenth_d = summary.get("tenth_man_distance")
    tenth_str = f"{tenth_d:.3f}" if isinstance(tenth_d, (int, float)) else "—"

    q_safe = html_mod.escape(question)
    rid_safe = html_mod.escape(rid)
    state_safe = html_mod.escape(verdict_state)
    open_label = html_mod.escape(_it(locale, "open"))
    return (
        f"<tr>"
        f"<td class=\"date\"><div class=\"d\">{date_str}</div>"
        f"<div class=\"t\">{time_str}</div></td>"
        f"<td class=\"q\">{q_safe}</td>"
        f"<td class=\"v\"><span class=\"v-pill v-{state_safe}\">{html_mod.escape(verdict)}</span></td>"
        f"<td class=\"td\">{tenth_str}</td>"
        f"<td class=\"link\"><a href=\"./{rid_safe}/report.html\">{open_label}</a></td>"
        f"</tr>"
    )


def _index_html(records: list) -> str:
    locale = _detect_index_locale(records)
    lang_attr = locale
    if records:
        rows_html = "\n".join(_format_row(r, locale) for r in records)
        body = (
            "<table class=\"ledger\">"
            "<thead><tr>"
            f"<th class=\"date\">{html_mod.escape(_it(locale, 'th_date'))}</th>"
            f"<th class=\"q\">{html_mod.escape(_it(locale, 'th_question'))}</th>"
            f"<th class=\"v\">{html_mod.escape(_it(locale, 'th_verdict'))}</th>"
            f"<th class=\"td\">{html_mod.escape(_it(locale, 'th_d10'))}</th>"
            "<th class=\"link\"></th>"
            "</tr></thead>"
            f"<tbody>{rows_html}</tbody>"
            "</table>"
        )
    else:
        body = (
            "<p class=\"empty\">"
            f"{html_mod.escape(_it(locale, 'empty_a'))}"
            f"<code>{html_mod.escape(_it(locale, 'empty_code'))}</code>"
            f"{html_mod.escape(_it(locale, 'empty_b'))}</p>"
        )

    count = len(records)
    count_word = _it(locale, "count_singular" if count == 1 else "count_plural")
    count_label = f"{count} {count_word}"
    updated_word = _it(locale, "updated")
    updated = datetime.now().strftime("%Y·%m·%d · %H:%M")
    updated_label = f"{updated_word} {updated}"
    title = _it(locale, "title")
    eyebrow = _it(locale, "eyebrow")
    h1_a = _it(locale, "h1_a")
    h1_em = _it(locale, "h1_em")
    h1_tail = _it(locale, "h1_tail")
    sub = _it(locale, "sub")
    version_label = _it(locale, "version_label")

    return f"""<!doctype html>
<html lang="{lang_attr}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html_mod.escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,450;9..40,500;9..40,600&family=Fraunces:opsz,wght@9..144,400;9..144,500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --midnight-navy: #1b2540;
    --deep-cosmos: #001033;
    --chartreuse: #d0f100;
    --ghost-canvas: #f8f9fc;
    --pure: #ffffff;
    --slate-ink: #6b7184;
    --ash: #7c8293;
    --storm: #596075;
    --fog: #b1b5c0;

    --rule:   rgba(0,39,80,0.08);
    --rule-2: rgba(0,39,80,0.05);

    --serif: 'Fraunces', Georgia, serif;
    --sans:  'DM Sans', ui-sans-serif, system-ui, sans-serif;
    --mono:  'JetBrains Mono', ui-monospace, monospace;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{
    font-family: var(--sans);
    background: var(--ghost-canvas);
    color: var(--midnight-navy);
    font-size: 16px;
    line-height: 1.5;
    letter-spacing: -0.16px;
    -webkit-font-smoothing: antialiased;
  }}
  ::selection {{ background: var(--chartreuse); color: var(--midnight-navy); }}

  /* Compact masthead — mirrors report.html */
  .masthead {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 18px 32px 14px;
    display: flex; align-items: center; justify-content: space-between;
    gap: 16px; flex-wrap: wrap;
    border-bottom: 1px solid var(--rule);
  }}
  .logo {{
    display: flex; align-items: center; gap: 10px;
    font-family: var(--serif);
    font-weight: 500; font-size: 18px; letter-spacing: -0.01em;
    color: var(--midnight-navy);
  }}
  .logo .mk {{
    width: 22px; height: 22px; border-radius: 6px;
    background: var(--midnight-navy);
    display: inline-flex; align-items: center; justify-content: center;
    color: var(--chartreuse);
    font-family: var(--mono); font-size: 11px; font-weight: 500;
  }}
  .mast-meta {{
    font-family: var(--mono); font-size: 12px;
    color: var(--slate-ink); letter-spacing: 0.02em;
  }}
  .mast-meta b {{ color: var(--midnight-navy); font-weight: 500; }}
  .mast-meta .sep {{ color: var(--fog); margin: 0 8px; }}

  /* Page wrapper */
  .page {{ max-width: 1200px; margin: 0 auto; padding: 56px 32px 96px; }}

  /* Hero */
  .hero {{
    margin-bottom: 56px;
  }}
  .hero-eyebrow {{
    font-family: var(--mono); font-size: 11px;
    letter-spacing: 0.14em; text-transform: uppercase;
    color: var(--slate-ink);
    margin: 0 0 18px;
  }}
  h1.hero-h {{
    font-family: var(--serif);
    font-weight: 400;
    font-size: clamp(40px, 5.5vw, 64px);
    line-height: 1.04;
    letter-spacing: -0.02em;
    margin: 0 0 14px;
    color: var(--midnight-navy);
  }}
  h1.hero-h em {{
    font-style: italic;
    color: var(--midnight-navy);
    background: var(--chartreuse);
    padding: 0 .15em;
    font-weight: 400;
  }}
  .sub {{
    font-family: var(--serif);
    font-style: italic;
    font-weight: 400;
    font-size: 19px;
    line-height: 1.45;
    color: var(--storm);
    margin: 0;
    max-width: 60ch;
  }}

  /* Empty state */
  .empty {{
    margin: 80px 0;
    text-align: center;
    color: var(--slate-ink);
    font-family: var(--serif);
    font-style: italic;
    font-size: 18px;
  }}
  .empty code {{
    font-family: var(--mono);
    font-style: normal;
    font-size: 13px;
    background: var(--pure);
    padding: 3px 9px;
    border-radius: 4px;
    border: 1px solid var(--rule);
    color: var(--midnight-navy);
  }}

  /* Ledger table */
  table.ledger {{
    width: 100%;
    border-collapse: collapse;
    border-top: 1px solid var(--midnight-navy);
    border-bottom: 1px solid var(--rule);
    background: var(--pure);
    border-radius: 4px;
    overflow: hidden;
  }}
  table.ledger thead th {{
    text-align: left;
    padding: 14px 18px 14px 24px;
    font-family: var(--mono);
    font-size: 10.5px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--slate-ink);
    font-weight: 500;
    border-bottom: 1px solid var(--rule);
    background: var(--ghost-canvas);
  }}
  table.ledger tbody tr {{
    border-bottom: 1px solid var(--rule-2);
    transition: background .12s ease;
  }}
  table.ledger tbody tr:last-child {{ border-bottom: none; }}
  table.ledger tbody tr:hover {{ background: var(--ghost-canvas); }}
  table.ledger td {{
    padding: 18px 18px 18px 24px;
    vertical-align: middle;
  }}
  td.date {{ width: 120px; white-space: nowrap; }}
  td.date .d {{
    font-family: var(--mono);
    font-size: 12px;
    color: var(--midnight-navy);
    font-variant-numeric: tabular-nums;
    font-weight: 500;
  }}
  td.date .t {{
    font-family: var(--mono);
    font-size: 11px;
    color: var(--slate-ink);
    font-variant-numeric: tabular-nums;
    margin-top: 2px;
  }}
  td.q {{
    font-family: var(--serif);
    font-weight: 400;
    font-size: 17px;
    line-height: 1.35;
    color: var(--midnight-navy);
    padding-right: 24px;
  }}
  td.v {{ width: 180px; white-space: nowrap; }}
  .v-pill {{
    display: inline-block;
    font-family: var(--mono);
    font-size: 10.5px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 4px 9px;
    border-radius: 999px;
    border: 1px solid var(--rule);
    color: var(--storm);
    background: var(--ghost-canvas);
  }}
  .v-aligned-stable {{
    color: var(--midnight-navy);
    background: var(--chartreuse);
    border-color: transparent;
  }}
  .v-aligned-fragile {{
    color: var(--midnight-navy);
    background: var(--pure);
    border-color: rgba(0,39,80,0.18);
  }}
  .v-divided {{
    color: var(--pure);
    background: var(--midnight-navy);
    border-color: transparent;
  }}
  td.td {{
    width: 76px;
    font-family: var(--mono);
    font-size: 12px;
    color: var(--storm);
    text-align: right;
    font-variant-numeric: tabular-nums;
  }}
  td.link {{ width: 90px; text-align: right; padding-right: 24px; }}
  td.link a {{
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--midnight-navy);
    text-decoration: none;
    padding: 6px 10px;
    border-radius: 999px;
    border: 1px solid var(--rule);
    background: var(--pure);
    transition: background .12s ease, color .12s ease, border-color .12s ease;
    white-space: nowrap;
  }}
  td.link a:hover {{
    background: var(--midnight-navy);
    color: var(--chartreuse);
    border-color: var(--midnight-navy);
  }}

  footer {{
    margin-top: 48px;
    padding-top: 22px;
    border-top: 1px solid var(--rule);
    font-family: var(--mono);
    font-size: 10.5px;
    letter-spacing: 0.08em;
    color: var(--slate-ink);
    display: flex;
    justify-content: space-between;
    text-transform: uppercase;
  }}
  footer b {{ color: var(--midnight-navy); font-weight: 500; }}

  @media (max-width: 720px) {{
    .page {{ padding: 36px 22px 64px; }}
    .masthead {{ padding: 14px 22px 12px; }}
    table.ledger thead th, table.ledger td {{ padding-left: 16px; padding-right: 12px; }}
    td.v, td.td {{ display: none; }}
    table.ledger thead th.v, table.ledger thead th.td {{ display: none; }}
  }}
</style>
</head>
<body>

  <header class="masthead">
    <div class="logo"><span class="mk">10</span> Henge</div>
    <div class="mast-meta">
      <b>{html_mod.escape(count_label)}</b><span class="sep">·</span>{html_mod.escape(updated_label)}<span class="sep">·</span>{html_mod.escape(version_label)}
    </div>
  </header>

<main class="page">
  <section class="hero">
    <p class="hero-eyebrow">{html_mod.escape(eyebrow)}</p>
    <h1 class="hero-h">{html_mod.escape(h1_a)}<em>{html_mod.escape(h1_em)}</em>{html_mod.escape(h1_tail)}</h1>
    <p class="sub">{html_mod.escape(sub)}</p>
  </section>
  {body}
  <footer>
    <span><b>{html_mod.escape(count_label)}</b></span>
    <span>{html_mod.escape(updated_label)}</span>
  </footer>
</main>
</body>
</html>
"""


def write_index() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    records = list_records()
    index_path = REPORTS_DIR / "index.html"
    index_path.write_text(_index_html(records), encoding="utf-8")
    return index_path
