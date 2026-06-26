"""FRED (St. Louis Fed) indicators.

All series share the same observations endpoint and API-key auth. Each
indicator builds on `fetch_series` and adds its own interpretation rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import requests

from financetrace.config import FRED_API_KEY, HTTP_TIMEOUT, USER_AGENT
from financetrace.sources.base import IndicatorResult, Lean

FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"


def _series_url(series_id: str) -> str:
    return f"https://fred.stlouisfed.org/series/{series_id}"


def fetch_series(series_id: str, limit: int = 24) -> list[dict]:
    """Return most recent observations descending by date.

    Each entry has keys 'date' (YYYY-MM-DD) and 'value' (str, '.' if missing).
    """
    if not FRED_API_KEY:
        raise RuntimeError("FRED_API_KEY not set in environment")
    resp = requests.get(
        FRED_OBSERVATIONS_URL,
        params={
            "series_id": series_id,
            "api_key": FRED_API_KEY,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        },
        headers={"User-Agent": USER_AGENT},
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json().get("observations", [])


def _latest_valid(observations: list[dict]) -> Optional[dict]:
    for obs in observations:
        if obs.get("value") not in (None, "", "."):
            return obs
    return None


def _yoy_change(observations: list[dict]) -> Optional[tuple[float, str]]:
    """Compute YoY percent change from the latest valid monthly value.

    Returns (yoy_percent, asof_date) or None if not enough data.
    """
    valid = [o for o in observations if o.get("value") not in (None, "", ".")]
    if len(valid) < 13:
        return None
    latest = valid[0]
    year_ago = valid[12]
    try:
        latest_v = float(latest["value"])
        prior_v = float(year_ago["value"])
    except (TypeError, ValueError):
        return None
    if prior_v == 0:
        return None
    return ((latest_v / prior_v) - 1.0) * 100.0, latest["date"]


@dataclass
class FredLevelIndicator:
    """Indicator scored from the most recent observed level.

    `thresholds` is a list of (upper_bound, lean) pairs evaluated in order;
    the first pair whose upper bound exceeds the value picks the lean.
    The final pair acts as the catch-all.
    """

    name: str
    series_id: str
    thresholds: list[tuple[float, Lean]]
    interpret: Callable[[float, Lean], str]
    weight: float = 1.0
    invert_for_score: bool = False

    @property
    def source_url(self) -> str:
        return _series_url(self.series_id)

    def fetch(self) -> IndicatorResult:
        try:
            obs = fetch_series(self.series_id, limit=4)
            latest = _latest_valid(obs)
            if not latest:
                return IndicatorResult.errored(self.name, self.source_url, "no recent valid observations", self.weight)
            value = float(latest["value"])
            lean = self._classify(value)
            return IndicatorResult(
                name=self.name,
                value=value,
                asof=latest["date"],
                lean=lean,
                score=_lean_to_score(lean),
                notes=self.interpret(value, lean),
                source_url=self.source_url,
                weight=self.weight,
            )
        except Exception as exc:
            return IndicatorResult.errored(self.name, self.source_url, str(exc), self.weight)

    def _classify(self, value: float) -> Lean:
        for upper, lean in self.thresholds:
            if value < upper:
                return lean
        return self.thresholds[-1][1]


def _lean_to_score(lean: Lean) -> float:
    from financetrace.sources.base import LEAN_SCORE

    return float(LEAN_SCORE[lean])


# ----- Concrete indicators -----

def t10y2y() -> IndicatorResult:
    """10Y minus 2Y Treasury spread. Negative = inverted = recession warning."""
    ind = FredLevelIndicator(
        name="10Y-2Y Treasury Spread",
        series_id="T10Y2Y",
        thresholds=[
            (-0.5, Lean.STRONG_BEAR),
            (0.0, Lean.BEAR),
            (0.5, Lean.NEUTRAL),
            (1.5, Lean.BULL),
            (float("inf"), Lean.STRONG_BULL),
        ],
        interpret=lambda v, lean: (
            f"spread = {v:.2f}%. Inverted curve historically precedes recessions; "
            "steep positive curve signals expansion."
        ),
        weight=1.5,
    )
    return ind.fetch()


def jolts_openings() -> IndicatorResult:
    """JOLTS job openings (thousands). User norm: ~7M is baseline tight labor."""
    ind = FredLevelIndicator(
        name="JOLTS Job Openings",
        series_id="JTSJOL",
        thresholds=[
            (6000, Lean.BEAR),
            (7000, Lean.NEUTRAL),
            (9000, Lean.BULL),
            (float("inf"), Lean.STRONG_BULL),
        ],
        interpret=lambda v, lean: (
            f"openings = {v/1000:.2f}M. Below ~7M suggests cooling labor market; "
            "above suggests demand for workers remains tight."
        ),
        weight=1.0,
    )
    return ind.fetch()


def wti_crude() -> IndicatorResult:
    """WTI spot. Very high oil is a headwind for consumer + Fed; very low signals weak demand."""
    ind = FredLevelIndicator(
        name="WTI Crude Oil",
        series_id="DCOILWTICO",
        thresholds=[
            (40, Lean.BEAR),
            (60, Lean.NEUTRAL),
            (90, Lean.BULL),
            (110, Lean.NEUTRAL),
            (float("inf"), Lean.BEAR),
        ],
        interpret=lambda v, lean: (
            f"WTI = ${v:.2f}. Moderate range (~60-90) is supportive; "
            "extremes in either direction tend to weigh on equities."
        ),
        weight=0.5,
    )
    return ind.fetch()


def inventory_to_sales() -> IndicatorResult:
    """Total Business Inventories/Sales. Lower = expanding economy."""
    ind = FredLevelIndicator(
        name="Inventory-to-Sales Ratio",
        series_id="ISRATIO",
        thresholds=[
            (1.30, Lean.STRONG_BULL),
            (1.40, Lean.BULL),
            (1.45, Lean.NEUTRAL),
            (1.55, Lean.BEAR),
            (float("inf"), Lean.STRONG_BEAR),
        ],
        interpret=lambda v, lean: (
            f"ratio = {v:.2f}. Lower ratio implies inventories drawing down vs "
            "sales — consistent with economic expansion."
        ),
        weight=1.0,
    )
    return ind.fetch()


def credit_card_delinquency() -> IndicatorResult:
    """Credit card delinquency rate (%). Rising = consumer stress."""
    ind = FredLevelIndicator(
        name="Credit Card Delinquency Rate",
        series_id="DRCCLACBS",
        thresholds=[
            (2.0, Lean.BULL),
            (2.8, Lean.NEUTRAL),
            (3.5, Lean.BEAR),
            (float("inf"), Lean.STRONG_BEAR),
        ],
        interpret=lambda v, lean: (
            f"delinquency = {v:.2f}%. Higher rate signals consumer balance-sheet stress, "
            "a drag on discretionary spending."
        ),
        weight=1.0,
    )
    return ind.fetch()


def cpi_rent_yoy() -> IndicatorResult:
    """CPI Rent of Primary Residence YoY%. Higher rent inflation -> hawkish Fed."""
    series_id = "CUUR0000SEHA"
    source_url = _series_url(series_id)
    try:
        obs = fetch_series(series_id, limit=18)
        result = _yoy_change(obs)
        if result is None:
            return IndicatorResult.errored(
                "CPI Rent YoY", source_url, "insufficient observations for YoY", weight=0.8
            )
        yoy, asof = result
        if yoy < 2.5:
            lean = Lean.STRONG_BULL
        elif yoy < 3.5:
            lean = Lean.BULL
        elif yoy < 4.5:
            lean = Lean.NEUTRAL
        elif yoy < 6.0:
            lean = Lean.BEAR
        else:
            lean = Lean.STRONG_BEAR
        return IndicatorResult(
            name="CPI Rent YoY",
            value=yoy,
            asof=asof,
            lean=lean,
            score=_lean_to_score(lean),
            notes=(
                f"rent inflation YoY = {yoy:.2f}%. Sticky shelter inflation keeps the "
                "Fed in restrictive territory; cooling rent is supportive of risk assets."
            ),
            source_url=source_url,
            weight=0.8,
        )
    except Exception as exc:
        return IndicatorResult.errored("CPI Rent YoY", source_url, str(exc), weight=0.8)


def buffett_indicator() -> IndicatorResult:
    """Wilshire 5000 Full Cap / GDP. Classic Buffett ratio for market valuation."""
    will_url = _series_url("WILL5000PRFC")
    source_url = "https://www.currentmarketvaluation.com/models/buffett-indicator.php"
    try:
        will_obs = fetch_series("WILL5000PRFC", limit=10)
        gdp_obs = fetch_series("GDP", limit=4)
        will_latest = _latest_valid(will_obs)
        gdp_latest = _latest_valid(gdp_obs)
        if not will_latest or not gdp_latest:
            return IndicatorResult.errored(
                "Buffett Indicator", source_url, "missing Wilshire or GDP observation", weight=1.0
            )
        will_v = float(will_latest["value"])
        gdp_v = float(gdp_latest["value"])
        ratio = (will_v / gdp_v) * 100.0  # both effectively in $B units
        if ratio < 75:
            lean = Lean.STRONG_BULL
        elif ratio < 110:
            lean = Lean.BULL
        elif ratio < 150:
            lean = Lean.NEUTRAL
        elif ratio < 200:
            lean = Lean.BEAR
        else:
            lean = Lean.STRONG_BEAR
        return IndicatorResult(
            name="Buffett Indicator (Wilshire 5000 / GDP)",
            value=ratio,
            asof=will_latest["date"],
            lean=lean,
            score=_lean_to_score(lean),
            notes=(
                f"market cap / GDP ~ {ratio:.0f}%. Higher ratio implies stocks "
                "expensive vs underlying economy; mean-reversion risk rises."
            ),
            source_url=source_url,
            weight=1.0,
            extra={"wilshire_url": will_url, "wilshire": will_v, "gdp": gdp_v},
        )
    except Exception as exc:
        return IndicatorResult.errored("Buffett Indicator (Wilshire 5000 / GDP)", source_url, str(exc), weight=1.0)


ALL_INDICATORS = [
    t10y2y,
    jolts_openings,
    wti_crude,
    inventory_to_sales,
    credit_card_delinquency,
    cpi_rent_yoy,
    buffett_indicator,
]
