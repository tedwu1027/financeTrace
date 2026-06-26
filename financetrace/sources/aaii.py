"""AAII Sentiment Survey — retail-investor sentiment.

The full historical dataset is published as an Excel file. To avoid pulling
in spreadsheet dependencies (xlrd/openpyxl), this fetcher scrapes the public
weekly-results page for bullish/neutral/bearish percentages and computes the
bull-bear spread, which is what the indicator is normally tracked on.

Page: https://www.aaii.com/sentimentsurvey/sent_results
User rule of thumb: bullish % above ~50 is rare and contrarian-bearish.
"""
from __future__ import annotations

import re

import requests

from financetrace.config import HTTP_TIMEOUT, USER_AGENT
from financetrace.sources.base import IndicatorResult, Lean
from financetrace.sources.fred import _lean_to_score

AAII_URL = "https://www.aaii.com/sentimentsurvey/sent_results"

# Look for "Bullish ... XX.X%" patterns. AAII renders the three numbers in
# the same table; the regex is lenient to survive minor markup changes.
_PCT = r"(\d{1,3}(?:\.\d+)?)\s*%"
_BULL_RE = re.compile(rf"Bullish[^%]{{0,80}}{_PCT}", re.IGNORECASE)
_BEAR_RE = re.compile(rf"Bearish[^%]{{0,80}}{_PCT}", re.IGNORECASE)
_NEUTRAL_RE = re.compile(rf"Neutral[^%]{{0,80}}{_PCT}", re.IGNORECASE)


def aaii_sentiment() -> IndicatorResult:
    try:
        resp = requests.get(
            AAII_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        html = resp.text
        b = _BULL_RE.search(html)
        r = _BEAR_RE.search(html)
        n = _NEUTRAL_RE.search(html)
        if not (b and r):
            return IndicatorResult.errored("AAII Sentiment", AAII_URL, "could not parse bull/bear values", weight=1.0)
        bull = float(b.group(1))
        bear = float(r.group(1))
        neutral = float(n.group(1)) if n else max(0.0, 100.0 - bull - bear)
        spread = bull - bear
        if spread <= -25:
            lean = Lean.STRONG_BULL
        elif spread <= -10:
            lean = Lean.BULL
        elif spread < 15:
            lean = Lean.NEUTRAL
        elif spread < 30:
            lean = Lean.BEAR
        else:
            lean = Lean.STRONG_BEAR
        bull_lean_override = bull >= 50
        if bull_lean_override and lean in (Lean.NEUTRAL, Lean.BEAR):
            lean = Lean.STRONG_BEAR
        return IndicatorResult(
            name="AAII Sentiment (Bull-Bear Spread)",
            value=spread,
            asof=None,
            lean=lean,
            score=_lean_to_score(lean),
            notes=(
                f"bull {bull:.1f}% / neutral {neutral:.1f}% / bear {bear:.1f}% "
                f"=> spread {spread:+.1f}. Contrarian: bull% above 50 historically rare "
                "and tied to local tops; deeply negative spread tied to durable lows."
            ),
            source_url=AAII_URL,
            weight=1.0,
            extra={"bull": bull, "bear": bear, "neutral": neutral},
        )
    except Exception as exc:
        return IndicatorResult.errored("AAII Sentiment", AAII_URL, str(exc), weight=1.0)
