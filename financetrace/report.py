from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from financetrace.scoring import Verdict
from financetrace.sources.base import IndicatorResult, Lean

LEAN_BADGE = {
    Lean.STRONG_BULL: "++ bull",
    Lean.BULL: "+ bull",
    Lean.NEUTRAL: "neutral",
    Lean.BEAR: "- bear",
    Lean.STRONG_BEAR: "-- bear",
    Lean.UNKNOWN: "n/a",
}


def render_markdown(results: list[IndicatorResult], verdict: Verdict, asof: date) -> str:
    lines: list[str] = []
    lines.append(f"# financeTrace daily — {asof.isoformat()}")
    lines.append("")
    lines.append(f"**Overall: {verdict.label}** (score {verdict.score:+.1f} / 100, "
                 f"confidence {verdict.confidence:.0%}, "
                 f"{verdict.contributing}/{verdict.total} indicators reporting)")
    lines.append("")
    lines.append("| Indicator | Lean | Value | As of | Notes |")
    lines.append("|---|---|---|---|---|")
    for r in results:
        value_str = _fmt_value(r.value)
        asof_str = r.asof or "—"
        notes = r.notes.replace("\n", " ")
        lines.append(
            f"| [{r.name}]({r.source_url}) | {LEAN_BADGE[r.lean]} | {value_str} | {asof_str} | {notes} |"
        )
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append(
        "Each indicator is mapped to a lean (-100 strong bear ... +100 strong bull). "
        "The overall score is a weight-averaged composite. Sentiment indicators are read "
        "**contrarian** (extreme greed → bearish, extreme fear → bullish). "
        "This is a research tool, not investment advice."
    )
    errored = [r for r in results if r.error]
    if errored:
        lines.append("")
        lines.append("## Indicators with errors")
        for r in errored:
            lines.append(f"- **{r.name}**: {r.error} ({r.source_url})")
    return "\n".join(lines) + "\n"


def render_json(results: list[IndicatorResult], verdict: Verdict, asof: date) -> str:
    payload = {
        "asof": asof.isoformat(),
        "verdict": {
            "label": verdict.label,
            "score": verdict.score,
            "confidence": verdict.confidence,
            "contributing": verdict.contributing,
            "total": verdict.total,
        },
        "indicators": [
            {
                "name": r.name,
                "value": r.value,
                "asof": r.asof,
                "lean": r.lean.value,
                "score": r.score,
                "weight": r.weight,
                "notes": r.notes,
                "source_url": r.source_url,
                "error": r.error,
                "extra": r.extra,
            }
            for r in results
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def write_reports(
    report_dir: Path,
    md: str,
    js: str,
    asof: date,
    html_body: str | None = None,
    site_dir: Path | None = None,
) -> dict[str, Path]:
    """Persist the daily artifacts. `site_dir`, if given, also gets an
    index.html (latest snapshot) and archive/<date>.html so a GitHub Pages
    deployment can publish the dir directly.
    """
    report_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    paths["md"] = report_dir / f"{asof.isoformat()}.md"
    paths["json"] = report_dir / f"{asof.isoformat()}.json"
    paths["md"].write_text(md, encoding="utf-8")
    paths["json"].write_text(js, encoding="utf-8")
    if html_body is not None:
        paths["html"] = report_dir / f"{asof.isoformat()}.html"
        paths["html"].write_text(html_body, encoding="utf-8")
        if site_dir is not None:
            site_dir.mkdir(parents=True, exist_ok=True)
            archive = site_dir / "archive"
            archive.mkdir(parents=True, exist_ok=True)
            (site_dir / "index.html").write_text(html_body, encoding="utf-8")
            (archive / f"{asof.isoformat()}.html").write_text(html_body, encoding="utf-8")
            (site_dir / "latest.json").write_text(js, encoding="utf-8")
            paths["site_index"] = site_dir / "index.html"
    return paths


def _fmt_value(v: float | None) -> str:
    if v is None:
        return "—"
    av = abs(v)
    if av >= 1000:
        return f"{v:,.0f}"
    if av >= 10:
        return f"{v:.2f}"
    return f"{v:.3f}"
