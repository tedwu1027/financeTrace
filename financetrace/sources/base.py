from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Protocol


_REDACT_PATTERNS = [
    # api_key=XXXX, api-key=XXXX, &key=XXXX in query strings
    re.compile(r"(?i)(api[_-]?key=)[^&\s\"'<>]+"),
    re.compile(r"(?i)([?&]key=)[^&\s\"'<>]+"),
]


def redact_secrets(text: str) -> str:
    """Strip api-key style tokens out of strings before they get persisted.

    Applied to error messages so a transient HTTP failure cannot leak the
    user's API key into reports, JSON snapshots, or workflow logs.
    """
    if not text:
        return text
    for pat in _REDACT_PATTERNS:
        text = pat.sub(r"\1<redacted>", text)
    return text


class Lean(str, Enum):
    STRONG_BULL = "strong_bull"
    BULL = "bull"
    NEUTRAL = "neutral"
    BEAR = "bear"
    STRONG_BEAR = "strong_bear"
    UNKNOWN = "unknown"


LEAN_SCORE = {
    Lean.STRONG_BULL: 100,
    Lean.BULL: 50,
    Lean.NEUTRAL: 0,
    Lean.BEAR: -50,
    Lean.STRONG_BEAR: -100,
    Lean.UNKNOWN: 0,
}


@dataclass
class IndicatorResult:
    """One observation from one data source.

    score is bounded to [-100, 100]; positive = bullish for equities,
    negative = bearish. lean is a categorical summary. notes is the
    short rationale shown in the report.
    """

    name: str
    value: Optional[float]
    asof: Optional[str]  # ISO date string, source's most recent observation
    lean: Lean
    score: float
    notes: str
    source_url: str
    weight: float = 1.0
    error: Optional[str] = None
    extra: dict = field(default_factory=dict)

    @classmethod
    def errored(cls, name: str, source_url: str, error: str, weight: float = 1.0) -> "IndicatorResult":
        safe = redact_secrets(error)
        return cls(
            name=name,
            value=None,
            asof=None,
            lean=Lean.UNKNOWN,
            score=0.0,
            notes=f"unavailable: {safe}",
            source_url=source_url,
            weight=weight,
            error=safe,
        )


class Indicator(Protocol):
    name: str
    weight: float
    source_url: str

    def fetch(self) -> IndicatorResult: ...
