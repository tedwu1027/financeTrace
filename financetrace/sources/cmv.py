"""Current Market Valuation — composite valuation read."""
from __future__ import annotations

import re

import requests

from financetrace.config import HTTP_TIMEOUT, USER_AGENT
from financetrace.sources.base import IndicatorResult, Lean
from financetrace.sources.fred import _lean_to_score

CMV_URL = "https://www.currentmarketvaluation.com/"

# The site headlines the composite verdict like "Strongly Overvalued" plus a
# percentile. Try to extract the verdict label; fall back to "Overvalued" hits.
_VERDICT_RE = re.compile(
    r"(Strongly\s+Overvalued|Overvalued|Fair\s+Valued|Undervalued|Strongly\s+Undervalued)",
    re.IGNORECASE,
)
_PERCENTILE_RE = re.compile(r"(\d{1,3})(?:st|nd|rd|th)\s+percentile", re.IGNORECASE)


_VERDICT_TO_LEAN = {
    "strongly undervalued": (Lean.STRONG_BULL, "deep value vs history"),
    "undervalued": (Lean.BULL, "below historical norms"),
    "fair valued": (Lean.NEUTRAL, "near historical norms"),
    "overvalued": (Lean.BEAR, "above historical norms"),
    "strongly overvalued": (Lean.STRONG_BEAR, "stretched vs history"),
}


def market_valuation() -> IndicatorResult:
    try:
        resp = requests.get(
            CMV_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        html = resp.text
        verdict_match = _VERDICT_RE.search(html)
        if not verdict_match:
            return IndicatorResult.errored("Current Market Valuation", CMV_URL, "could not parse verdict", weight=1.0)
        verdict_raw = verdict_match.group(1).lower().strip()
        verdict_key = re.sub(r"\s+", " ", verdict_raw)
        lean, rationale = _VERDICT_TO_LEAN.get(verdict_key, (Lean.NEUTRAL, "unrecognized verdict"))
        pct_match = _PERCENTILE_RE.search(html)
        percentile = float(pct_match.group(1)) if pct_match else None
        return IndicatorResult(
            name="Current Market Valuation",
            value=percentile,
            asof=None,
            lean=lean,
            score=_lean_to_score(lean),
            notes=f"verdict: {verdict_key} ({rationale}).",
            source_url=CMV_URL,
            weight=1.0,
            extra={"verdict": verdict_key, "percentile": percentile},
        )
    except Exception as exc:
        return IndicatorResult.errored("Current Market Valuation", CMV_URL, str(exc), weight=1.0)
