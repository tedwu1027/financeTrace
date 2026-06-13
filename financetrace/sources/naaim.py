"""NAAIM Exposure Index — sentiment of active managers.

Source: https://www.naaim.org/programs/naaim-exposure-index/

NAAIM publishes the index weekly. The page exposes the current reading
inline; we scrape the most-recent value. User rule of thumb: readings near
100 are sell signals (managers fully long = euphoric).
"""
from __future__ import annotations

import re

import requests

from financetrace.config import HTTP_TIMEOUT, USER_AGENT
from financetrace.sources.base import IndicatorResult, Lean
from financetrace.sources.fred import _lean_to_score

NAAIM_URL = "https://www.naaim.org/programs/naaim-exposure-index/"

# NAAIM page exposes "NAAIM Exposure Index" + the latest number nearby; rather
# than relying on positional HTML structure, find the most recent percentage
# in the leading content block.
_NUMBER_NEAR_LABEL = re.compile(
    r"NAAIM\s+Exposure\s+Index[^0-9-]{0,80}(-?\d{1,3}(?:\.\d+)?)",
    re.IGNORECASE,
)
_RECENT_NUMBER = re.compile(r"(-?\d{1,3}(?:\.\d+)?)\s*%?")


def naaim_exposure() -> IndicatorResult:
    try:
        resp = requests.get(
            NAAIM_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        html = resp.text
        match = _NUMBER_NEAR_LABEL.search(html)
        if not match:
            return IndicatorResult.errored("NAAIM Exposure Index", NAAIM_URL, "could not locate value in page", weight=1.0)
        value = float(match.group(1))
        if value < 20:
            lean = Lean.STRONG_BULL
        elif value < 50:
            lean = Lean.BULL
        elif value < 80:
            lean = Lean.NEUTRAL
        elif value < 95:
            lean = Lean.BEAR
        else:
            lean = Lean.STRONG_BEAR
        return IndicatorResult(
            name="NAAIM Exposure Index",
            value=value,
            asof=None,
            lean=lean,
            score=_lean_to_score(lean),
            notes=(
                f"exposure = {value:.1f}. Readings near/above 100 indicate active managers "
                "fully invested — historically a contrarian topping signal."
            ),
            source_url=NAAIM_URL,
            weight=1.0,
        )
    except Exception as exc:
        return IndicatorResult.errored("NAAIM Exposure Index", NAAIM_URL, str(exc), weight=1.0)
