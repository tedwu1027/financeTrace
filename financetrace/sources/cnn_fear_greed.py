"""CNN Fear & Greed Index — contrarian sentiment read."""
from __future__ import annotations

import requests

from financetrace.config import HTTP_TIMEOUT, USER_AGENT
from financetrace.sources.base import IndicatorResult, Lean
from financetrace.sources.fred import _lean_to_score

CNN_API = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
CNN_PAGE = "https://edition.cnn.com/markets/fear-and-greed"


def fear_and_greed() -> IndicatorResult:
    """Read the CNN composite 0-100. Contrarian: extreme greed -> bear, extreme fear -> bull."""
    try:
        resp = requests.get(
            CNN_API,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://edition.cnn.com",
                "Referer": "https://edition.cnn.com/",
            },
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        fg = payload.get("fear_and_greed") or {}
        score = fg.get("score")
        rating = fg.get("rating")
        timestamp = fg.get("timestamp")
        if score is None:
            return IndicatorResult.errored("CNN Fear & Greed", CNN_PAGE, "score missing in payload", weight=0.7)
        score = float(score)
        if score < 20:
            lean = Lean.STRONG_BULL
        elif score < 40:
            lean = Lean.BULL
        elif score < 60:
            lean = Lean.NEUTRAL
        elif score < 80:
            lean = Lean.BEAR
        else:
            lean = Lean.STRONG_BEAR
        return IndicatorResult(
            name="CNN Fear & Greed",
            value=score,
            asof=str(timestamp)[:10] if timestamp else None,
            lean=lean,
            score=_lean_to_score(lean),
            notes=(
                f"index = {score:.0f} ({rating}). Contrarian: extreme greed flags euphoric tops, "
                "extreme fear flags capitulation lows."
            ),
            source_url=CNN_PAGE,
            weight=0.7,
        )
    except Exception as exc:
        return IndicatorResult.errored("CNN Fear & Greed", CNN_PAGE, str(exc), weight=0.7)
