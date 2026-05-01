"""Demo render — produces a screenshot-ready English HTML report without spending tokens.

Mocks the 10 advisor responses + consensus + tenth-man with hand-crafted English
content, runs MDS on synthetic embeddings, then calls viz.render. The new TenthAI
v3 template is already English-native, so no chrome post-processing is needed.

Usage:
    python examples/demo_render.py            # writes docs/demo.html and opens it
    python examples/demo_render.py --no-open  # writes only

Produces a stable filename (docs/demo.html) so screenshots can be regenerated
without breaking links from the README.
"""
import argparse
import sys
import webbrowser
from pathlib import Path

import numpy as np

# Make henge importable when running the script directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from henge.embed import project_mds  # noqa: E402
from henge.viz import render  # noqa: E402


QUESTION = (
    "Should I leave my Senior PM job at a Series C unicorn to start a B2B SaaS in clinical research?"
)

CONSENSUS = """# Quit on the back of a contract — not on the back of confidence

## (1) Where the nine converge

The financial setup is workable but unforgiving — 9 months of runway is enough for a wedge but not for a category, and a toddler in the household compresses your willingness to extend that runway under stress. The healthtech background materially de-risks the idea: niche workflow tools for clinical research coordinators are exactly the kind of unsexy, sticky software that compounds when sold to people the founder already understands. Domain-insider founders in regulated B2B verticals fail at much lower rates than outsiders, and that asymmetry is the strongest signal in the dataset.

## (2) Internal tension

Tension persists on **whether *now* is the right moment**. The systemic and pre-mortem frames want one more thing nailed before the quit — a paying design partner, or a side-project prototype that three coordinators are already using. The optimist and first-principles frames argue the cost of waiting another six months is higher than it looks: your context window on the buyer degrades from the inside the longer you stay at the unicorn. Both sides are pricing the same risk; they disagree on which clock runs faster.

## (3) Net lean

**Net lean:** lean *out* of the job, but not blindly. Secure one paying design partner before the quit, then go full-time on the back of that contract. Don't quit and figure it out — quit and execute on a contract you already signed. The sequencing matters more than the timing."""


FRAMES = {
    "empirical": """## Base rates and the math

The empirical record on healthcare-vertical SaaS founded by domain insiders is more favorable than the generic SaaS base rate: ~28% of YC healthtech alumni reach Series A within 24 months versus ~18% across all verticals. **Domain insider** is doing most of the work in that statistic — outsider founders in regulated B2B verticals fail at much higher rates because the sales cycle eats their runway.

**Cash math:** $80k savings + 9 months runway implies ~$8.9k/month burn. That's tight for a coastal US founder with a toddler. Industry data on first-product GTM in clinical research suggests 4–7 months from first conversation to first paid pilot ($2–10k/month), and 9–14 months to a meaningful $5k+ MRR floor. Your runway covers the optimistic case, not the realistic one.

**Conclusion:** the numbers are not a green light by themselves — they're a yellow. The realistic GTM curve consumes ~80% of your runway before MRR can sustain household burn. The variable that determines outcome is whether you can compress that curve by walking in with one design partner already in hand."""

,
    "historical": """## What the comparable companies actually did

Look at the founders of TrialKit, Florence Healthcare, and ClinCapture in their pre-seed phase: all three had **domain employer relationships that converted into design-partner contracts before the founder quit**. The pattern is consistent across the regulatory-software vertical — the ones who waited to formalize that relationship until after quitting burned 30–50% more runway than the ones who locked it in first.

There's also a counter-pattern worth naming: the founders who *over*-validated and never quit. They stayed in their PM roles "just one more milestone" for 18+ months and watched the window close. The clinical research tooling space had three meaningful entrants in 2023–2024 alone; assuming nobody else moves while you decide is wrong.

**Conclusion:** history strongly favors *quit with one paid design partner already signed*. The risk-adjusted path isn't "decide between job and startup" — it's "manufacture the design-partner moment, then quit on the back of it.\""""

,
    "first-principles": """## The atoms underneath the question

Strip away the narrative. The atoms are: **(a)** your time has a market value (~$220k base + equity), **(b)** the value of building this product is a function of how much time + focus + buyer-empathy you can pour into it before someone else does, **(c)** buyer-empathy is a wasting asset — it decays month-by-month once you stop being adjacent to clinical research operators, **(d)** $80k buys you ~9 months of runway in your geography.

The convention says *validate before you quit*. The convention is right when buyer-empathy is durable. **Buyer-empathy is not durable here** — leaving the unicorn cuts you off from the 30+ adjacent conversations per week that compound your understanding. Every month you stay validating, you're also accumulating the option premium of more savings *and* paying down the option of walking in with current insider knowledge.

**Conclusion:** the right move is whichever path maximizes paid contact with real clinical research coordinators in the next 3 months. If the job blocks that contact, leave. If it accelerates it (because your role gives you intros), stay 90 more days and then leave. Don't optimize for runway; optimize for buyer-time."""

,
    "analogical": """## Cross-domain: the climber and the route

This decision is structurally identical to a multi-pitch climber deciding whether to commit to a hard route after climbing two pitches at the base. Continuing has cost (gear, weather window, daylight). Retreating has cost (the route doesn't get easier next year, and your conditioning peaks now). The mistake climbers make isn't pushing on or retreating — it's *deciding at the base of pitch three* without a pre-committed framework.

In military strategy, the same shape shows up as the **OODA loop's Decide phase**: the failure mode is collecting information forever and never closing the loop. John Boyd's insight was that decision speed beats decision quality past a certain threshold — because the environment moves while you're optimizing.

**Conclusion:** the analogical answer is *pre-commit the criterion now, and then execute when the criterion is hit*. "I'll quit when I have one signed paid design partner at $3k+/month" is a clean, falsifiable criterion. Don't leave it as a feeling. Leave it as a trigger."""

,
    "systemic": """## Second-order effects on the household and the buyer

**Loop #1 — household:** quitting before paid validation puts your partner under cognitive load they didn't sign up to absorb daily. They said "I support you" once; they will say it 200 more times under different stress conditions. The marriage variable compounds badly when financial uncertainty is unresolved for >6 months. *Resolve the design-partner contract first specifically because it shortens that window.*

**Loop #2 — buyer trust:** clinical research coordinators are a small, gossipy market. Your first three conversations get repeated to twenty more. If you walk in as "I just quit my job to build this for you" you signal commitment but also desperation. If you walk in as "my employer lets me work on this 1 day a week and I'd love your input" you signal craft but also non-commitment. **Neither is right after month 4** — the buyer wants to bet on someone who has bet on themselves, but not on someone who needs them to close.

**Conclusion:** the systemic answer is staged commitment — moonlight 60 days to land the design partner, quit on the back of the contract, sell from a position of paid traction. The household and the buyer both reward that sequencing."""

,
    "ethical": """## Stakeholders and trade-offs

Three stakeholders: you, your partner, your toddler. Your partner has informed consent on the financial risk; your toddler doesn't. That asymmetry matters. It doesn't mean don't quit — parents quit jobs to start companies all the time and their kids are fine — but it means the threshold for *paying yourself something* should be lower, not zero. A founder who refuses to pay themselves "until traction" is making a moral choice about whose burden the cost falls on, and the answer in this household is the partner.

There's also a softer ethical layer: the clinical research coordinators you'll be selling to are not abstract buyers. They are mostly underpaid women holding regulated, life-affecting work together with duct-taped Excel. Building this badly — over-promising, under-shipping, ghosting after raising — does real damage. The ethical floor is *if you quit, you ship something useful in 90 days and you don't disappear*.

**Conclusion:** quit if and only if the household budget includes a small founder salary from month 4 onward (≥$3k/month) and you commit publicly to a 90-day shipping cadence the buyers can hold you to. Anything looser is asking your partner and your buyers to absorb risk that's properly yours."""

,
    "soft-contrarian": """## The premise nobody questioned

Everyone is debating *when to quit*. Reframe: **what if the right move is to renegotiate the unicorn role into a 4-day week with a side-project carve-out, and not quit at all for the next 6 months?**

This sounds like cope, but it's actually leverage. Senior PMs at Series C unicorns with healthtech specialization are not fungible. The company does not want to lose you mid-cycle. A 4-day week request, framed as "I want to stay long-term and need bandwidth to recharge", lands ~40% of the time at this seniority. That's a free month of runway every month plus continued buyer-adjacent context plus equity vesting.

The objection: "but I'd be giving 80% of my brain to someone else's product." Counter: you're already only giving ~70% — the other 30% is meetings, status, slack. A 4-day week doesn't lose you much real output and buys you 1 dedicated day per week to land the design partner without burning savings.

**Conclusion:** before quitting, run the renegotiation play. If it lands, you've bought 6 months of optionality cheap. If it fails, you have a clean reason to leave and probably a more honest read on how much the company values you."""

,
    "radical-optimist": """## The 10× scenario nobody is pricing

If you ship a clinical research coordinator workflow tool in 2025, the upside scenario looks like this: you land 8 paid design partners by month 9, ARR hits $250k by month 14, you raise a $2.5M seed at $12M post on the back of "domain insider, 15 paying clinical sites, 87% retention". Your equity is worth $1.5–3M on paper inside 18 months.

That's not a fantasy — it's the **Florence Healthcare trajectory** shifted forward 18 months, which is exactly the kind of compression AI tooling enables for solo founders now. The thing the cautious frames are mispricing isn't the downside risk (they're pricing it correctly). They're mispricing the *probability of the upside scenario*, which is materially higher than 10% for a domain-insider founder in a regulated vertical with a thin moat against generic AI tools.

The asymmetry is real: capped downside (you can return to a $250k PM job in 12 months — that's not catastrophic, that's a sabbatical with extra steps), uncapped upside ($3M+ on paper). When you have an asymmetric bet and the buyer-empathy clock is ticking, you take the bet.

**Conclusion:** the optimist's argument isn't *quit blindly*. It's *don't let pre-mortem reasoning anchor you to the median outcome when you have an asymmetric bet*. The upside is large enough that even if you have to come back to PM-land in 18 months, the option value of having tried was probably worth more than the salary you forewent."""

,
    "pre-mortem": """## It's month 14 and it failed. Why?

It's not because the product was bad. It's because the *sequence* was wrong.

**Failure mode 1 (most likely):** you quit, spent month 1–3 building a polished MVP based on assumptions from your insider knowledge, then discovered in month 4 that two of the three core assumptions were stale — the workflows you remembered from 2023 had been partially eaten by Veeva updates. By month 7 you'd rebuilt twice, runway was at 4 months, and the design partner you'd been talking to since month 2 finally said "we'll wait for v2" — meaning never.

**Failure mode 2:** you quit, the household stress you'd modeled as "manageable" became unmanageable around month 5 (toddler illness + your partner's review cycle + your runway anxiety converged). You took a consulting contract to bridge — 60% time — and the startup got 25% of you. By month 10 you were a consultant who also had a startup.

**Failure mode 3:** you actually shipped a great v1 in month 4, signed two design partners, raised a small angel round in month 7 — and then realized in month 11 that the market was real but the *acquisition cost* was wrong. Each design partner took 6 weeks to close. You couldn't raise a seed because the revenue was too lumpy.

**Conclusion:** all three failure modes share one root: **the design partner relationship was treated as a milestone instead of a precondition**. The pre-mortem says *do not quit until you have a signed paid contract from one clinical site*. Everything else is recoverable. That sequencing is not."""
}

TENTH_MAN = """## §1 Premises I accept

I accept the financial math, the household constraints, the domain-insider thesis, the buyer-empathy decay argument, and the consensus that a paying design partner before the quit is the cleanest path. The nine analyses are competent and internally consistent.

## §2 Where the consensus fails

The nine frames are answering a *career-optimization* question. **The actual question is identity.**

> The hidden question isn't "is this the right time to start a company." It's "do I want to be a founder, or a Senior PM who briefly tried." The financial framing is a way to defer the identity question by making it feel quantitative.

The consensus says: *secure a paid design partner, then quit*. Sounds prudent. It is also the perfect mechanism for never quitting. Six months from now, with one paid pilot at $4k/month, the same nine frames will produce the same advice — *one more design partner first, then quit*. The criterion is unfalsifiable in practice because each milestone hit raises the bar for the next.

## §3 The question behind the question

What if the founders who succeed in regulated B2B verticals aren't the ones who optimized the quit-timing? What if they're the ones who **forced themselves into the identity first and let the financials catch up?** Quitting is the dispositive act — it converts a curious PM into a founder in the eyes of every buyer they meet for the next 18 months. A moonlighting PM with a side project has 30% the credibility of a full-time founder with the same product. Buyers pattern-match on commitment and they pay accordingly. The nine frames price the financial cost of quitting too early. They do not price the credibility cost of quitting too late.

[FAILURE_MODES]
### Validation infinite-loop
Each milestone hit raises the bar for the next. "One paid design partner" becomes "one with retention", then "with expansion revenue". The criterion never lets you quit.

### Buyer-empathy decay
Every month inside the unicorn dulls your context window on the clinical-research operator. By the time you "feel ready", you are no longer the domain insider you were when the idea was hot.

### Identity hedging
Moonlighting signals you bet on yourself with one foot still planted. Buyers pattern-match on commitment. A full-time founder with no contract closes design partners faster than a part-time PM with two pilots.
[/FAILURE_MODES]"""


def _make_demo_embeddings(rng: np.random.Generator) -> list:
    """9 frames cluster moderately + tenth-man pushed firmly out.

    Calibrated so the visual landing in the SVG ring system is well-spread:
    frames between rings 1–3, tenth-man on or just past ring 3.
    """
    base = rng.normal(0, 0.18, size=(9, 1024))
    base[:, 0] += 0.6   # bias the cluster off-center along axis 0
    base = base / np.linalg.norm(base, axis=1, keepdims=True)
    outlier = rng.normal(0, 0.12, size=(1, 1024))
    outlier[:, 0] -= 1.4
    outlier[:, 1] += 0.6
    outlier = outlier / np.linalg.norm(outlier, axis=1, keepdims=True)
    return np.vstack([base, outlier]).tolist()


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a screenshot-ready demo report.")
    parser.add_argument("--no-open", action="store_true", help="Don't open the browser after writing.")
    args = parser.parse_args()

    rng = np.random.default_rng(11)
    embeds = _make_demo_embeddings(rng)
    proj = project_mds(embeds)

    frame_order = [
        "empirical", "historical", "first-principles", "analogical",
        "systemic", "ethical", "soft-contrarian", "radical-optimist", "pre-mortem",
    ]
    results = [(name, FRAMES[name], "ok") for name in frame_order]
    results.append(("tenth-man", TENTH_MAN, "ok"))

    html = render(
        question=QUESTION,
        results=results,
        consensus=CONSENSUS,
        coords_2d=proj["coords_2d"],
        distances=proj["distance_to_centroid_of_9"],
        provider="openai",
        model="text-embedding-3-small",
        cost_estimate_usd=0.65,
    )

    out_dir = Path(__file__).resolve().parent.parent / "docs"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "demo.html"
    out_file.write_text(html, encoding="utf-8")

    # Mirror the bundled hero painting next to demo.html so the relative
    # `assets/header-painting.jpg` reference resolves on GitHub Pages.
    import shutil
    pkg_assets = Path(__file__).resolve().parent.parent / "henge" / "assets"
    demo_assets = out_dir / "assets"
    demo_assets.mkdir(exist_ok=True)
    painting = pkg_assets / "header-painting.jpg"
    if painting.exists():
        shutil.copyfile(painting, demo_assets / "header-painting.jpg")

    print(f"Demo report written to: {out_file}")
    if not args.no_open:
        webbrowser.open(f"file://{out_file.absolute()}")


if __name__ == "__main__":
    main()
