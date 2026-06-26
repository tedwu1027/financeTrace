"""EIA Strategic Petroleum Reserve."""
from __future__ import annotations

import requests

from financetrace.config import EIA_API_KEY, HTTP_TIMEOUT, USER_AGENT
from financetrace.sources.base import IndicatorResult, Lean
from financetrace.sources.fred import _lean_to_score

SPR_SERIES_ID = "MCSSTUS1"
SPR_URL = (
    "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx"
    "?n=pet&s=mcsstus1&f=m"
)
SPR_API = "https://api.eia.gov/v2/petroleum/stoc/wstk/data/"


def spr_level() -> IndicatorResult:
    """U.S. Strategic Petroleum Reserve stocks (thousand barrels), monthly.

    Refilling SPR = improving energy security buffer (mild bull tone).
    Persistent drawdowns at low levels = strategic vulnerability (mild bear).
    Weight kept low — this is more of a context indicator than a market-timing signal.
    """
    if not EIA_API_KEY:
        return IndicatorResult.errored("Strategic Petroleum Reserve", SPR_URL, "EIA_API_KEY not set", weight=0.3)
    try:
        resp = requests.get(
            SPR_API,
            params={
                "api_key": EIA_API_KEY,
                "frequency": "monthly",
                "data[0]": "value",
                "facets[series][]": SPR_SERIES_ID,
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "length": "14",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json().get("response", {}).get("data", [])
        if not data:
            return IndicatorResult.errored("Strategic Petroleum Reserve", SPR_URL, "no data", weight=0.3)
        latest = data[0]
        latest_val = float(latest["value"])
        asof = latest.get("period")
        yoy = None
        for row in data:
            if row.get("period") and asof and row["period"][:4] == str(int(asof[:4]) - 1) and row["period"][5:7] == asof[5:7]:
                try:
                    prior = float(row["value"])
                    yoy = ((latest_val / prior) - 1.0) * 100.0
                except (TypeError, ValueError):
                    pass
                break
        if yoy is None:
            lean = Lean.NEUTRAL
        elif yoy > 5:
            lean = Lean.BULL
        elif yoy < -10:
            lean = Lean.BEAR
        else:
            lean = Lean.NEUTRAL
        notes_parts = [f"SPR = {latest_val/1000:.0f}M barrels"]
        if yoy is not None:
            notes_parts.append(f"YoY {yoy:+.1f}%")
        notes_parts.append("refill phase supports energy security; sustained drawdown is a tail risk")
        return IndicatorResult(
            name="Strategic Petroleum Reserve",
            value=latest_val,
            asof=asof,
            lean=lean,
            score=_lean_to_score(lean),
            notes=". ".join(notes_parts) + ".",
            source_url=SPR_URL,
            weight=0.3,
            extra={"yoy_percent": yoy},
        )
    except Exception as exc:
        return IndicatorResult.errored("Strategic Petroleum Reserve", SPR_URL, str(exc), weight=0.3)
