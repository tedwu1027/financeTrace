from __future__ import annotations

import html
from datetime import date

from financetrace.scoring import Verdict
from financetrace.sources.base import IndicatorResult, Lean

LEAN_CLASS = {
    Lean.STRONG_BULL: "lean-strong-bull",
    Lean.BULL: "lean-bull",
    Lean.NEUTRAL: "lean-neutral",
    Lean.BEAR: "lean-bear",
    Lean.STRONG_BEAR: "lean-strong-bear",
    Lean.UNKNOWN: "lean-unknown",
}

LEAN_LABEL = {
    Lean.STRONG_BULL: "Strong Bull",
    Lean.BULL: "Bull",
    Lean.NEUTRAL: "Neutral",
    Lean.BEAR: "Bear",
    Lean.STRONG_BEAR: "Strong Bear",
    Lean.UNKNOWN: "Unavailable",
}

VERDICT_CLASS = {
    "Strongly bullish": "verdict-strong-bull",
    "Bullish": "verdict-bull",
    "Neutral": "verdict-neutral",
    "Bearish": "verdict-bear",
    "Strongly bearish": "verdict-strong-bear",
    "Insufficient data": "verdict-unknown",
}

_CSS = """
:root {
  color-scheme: light dark;
  --bg: #0f1115;
  --panel: #171a21;
  --panel-2: #1d212b;
  --text: #e8ecf3;
  --muted: #8a93a4;
  --line: #262b36;
  --bull: #16a34a;
  --bull-dim: #14532d;
  --bear: #dc2626;
  --bear-dim: #7f1d1d;
  --neutral: #6b7280;
  --warn: #d97706;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--text);
  font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
main { max-width: 1100px; margin: 0 auto; padding: 32px 20px 80px; }
header { display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-bottom: 24px; }
h1 { font-size: 26px; font-weight: 600; margin: 0; letter-spacing: -0.01em; }
header .asof { color: var(--muted); font-size: 14px; }
.verdict { padding: 22px 24px; border-radius: 12px; margin-bottom: 28px;
  display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;
  background: var(--panel); border: 1px solid var(--line); }
.verdict .label { font-size: 22px; font-weight: 600; }
.verdict .meta { color: var(--muted); font-size: 14px; }
.verdict-strong-bull { border-left: 6px solid var(--bull); }
.verdict-bull        { border-left: 6px solid var(--bull); }
.verdict-neutral     { border-left: 6px solid var(--neutral); }
.verdict-bear        { border-left: 6px solid var(--bear); }
.verdict-strong-bear { border-left: 6px solid var(--bear); }
.verdict-unknown     { border-left: 6px solid var(--warn); }
.score { font-variant-numeric: tabular-nums; font-size: 30px; font-weight: 600; }
.score.positive { color: var(--bull); }
.score.negative { color: var(--bear); }
.score.neutral  { color: var(--muted); }
section h2 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--muted); margin: 28px 0 12px; font-weight: 600; }
.grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
  padding: 14px 16px; display: flex; flex-direction: column; gap: 8px; }
.card.errored { background: var(--panel-2); opacity: 0.75; }
.card .top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.card .name { font-weight: 600; font-size: 14px; line-height: 1.3; }
.card .value { font-size: 26px; font-variant-numeric: tabular-nums; font-weight: 600; letter-spacing: -0.01em; }
.card .asof  { color: var(--muted); font-size: 12px; }
.card .notes { color: var(--muted); font-size: 13px; line-height: 1.45; }
.card a { color: var(--muted); font-size: 12px; text-decoration: none; }
.card a:hover { color: var(--text); text-decoration: underline; }
.badge { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 999px;
  font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.lean-strong-bull { background: rgba(22,163,74,0.15); color: var(--bull); }
.lean-bull        { background: rgba(22,163,74,0.10); color: var(--bull); }
.lean-neutral     { background: rgba(107,114,128,0.18); color: #c5cad3; }
.lean-bear        { background: rgba(220,38,38,0.10); color: var(--bear); }
.lean-strong-bear { background: rgba(220,38,38,0.18); color: var(--bear); }
.lean-unknown     { background: rgba(217,119,6,0.15); color: var(--warn); }
footer { color: var(--muted); font-size: 12px; margin-top: 36px; line-height: 1.6; }
footer a { color: var(--muted); }
@media (prefers-color-scheme: light) {
  :root { --bg:#f7f8fb; --panel:#fff; --panel-2:#f1f3f7; --text:#0b1220;
          --muted:#5b6473; --line:#e4e7ee; }
}
"""


def render_html(results: list[IndicatorResult], verdict: Verdict, asof: date) -> str:
    score_class = "positive" if verdict.score > 0 else "negative" if verdict.score < 0 else "neutral"
    verdict_class = VERDICT_CLASS.get(verdict.label, "verdict-neutral")
    healthy = [r for r in results if r.lean is not Lean.UNKNOWN]
    errored = [r for r in results if r.lean is Lean.UNKNOWN]

    parts: list[str] = []
    parts.append("<!doctype html>")
    parts.append('<html lang="en"><head><meta charset="utf-8">')
    parts.append('<meta name="viewport" content="width=device-width,initial-scale=1">')
    parts.append(f"<title>financeTrace — {asof.isoformat()}</title>")
    parts.append(f"<style>{_CSS}</style>")
    parts.append("</head><body><main>")
    parts.append("<header>")
    parts.append("<h1>financeTrace</h1>")
    parts.append(f'<div class="asof">as of {asof.isoformat()}</div>')
    parts.append("</header>")

    parts.append(f'<div class="verdict {verdict_class}">')
    parts.append("<div>")
    parts.append(f'<div class="label">{html.escape(verdict.label)}</div>')
    parts.append(
        f'<div class="meta">'
        f"{verdict.contributing}/{verdict.total} indicators reporting "
        f"&middot; confidence {verdict.confidence:.0%}"
        f"</div>"
    )
    parts.append("</div>")
    parts.append(f'<div class="score {score_class}">{verdict.score:+.0f}</div>')
    parts.append("</div>")

    if healthy:
        parts.append("<section>")
        parts.append("<h2>Indicators</h2>")
        parts.append('<div class="grid">')
        for r in healthy:
            parts.append(_render_card(r, errored=False))
        parts.append("</div></section>")

    if errored:
        parts.append("<section>")
        parts.append("<h2>Unavailable</h2>")
        parts.append('<div class="grid">')
        for r in errored:
            parts.append(_render_card(r, errored=True))
        parts.append("</div></section>")

    parts.append(
        '<footer>Sentiment indicators are read <strong>contrarian</strong>. '
        "Composite score is a weight-averaged mean over reporting indicators. "
        "Research tool, not investment advice.</footer>"
    )
    parts.append("</main></body></html>")
    return "\n".join(parts) + "\n"


def _render_card(r: IndicatorResult, errored: bool) -> str:
    lean_class = LEAN_CLASS[r.lean]
    lean_label = LEAN_LABEL[r.lean]
    value_str = _fmt_value(r.value)
    asof_str = r.asof or ""
    notes = html.escape(r.notes)
    name = html.escape(r.name)
    url = html.escape(r.source_url)
    classes = "card errored" if errored else "card"
    asof_html = f'<div class="asof">{html.escape(asof_str)}</div>' if asof_str else ""
    value_html = (
        f'<div class="value">{html.escape(value_str)}</div>' if value_str != "—" else ""
    )
    return (
        f'<div class="{classes}">'
        f'  <div class="top">'
        f'    <span class="name">{name}</span>'
        f'    <span class="badge {lean_class}">{lean_label}</span>'
        f"  </div>"
        f"  {value_html}"
        f"  {asof_html}"
        f'  <div class="notes">{notes}</div>'
        f'  <a href="{url}" target="_blank" rel="noopener">source &rarr;</a>'
        f"</div>"
    )


def _fmt_value(v: float | None) -> str:
    if v is None:
        return "—"
    av = abs(v)
    if av >= 1000:
        return f"{v:,.0f}"
    if av >= 10:
        return f"{v:.2f}"
    return f"{v:.3f}"
