from __future__ import annotations

from dataclasses import dataclass

from financetrace.sources.base import IndicatorResult, Lean


@dataclass
class Verdict:
    label: str
    score: float  # weighted average in [-100, 100]
    confidence: float  # 0..1, proportion of indicators that returned data
    contributing: int
    total: int


def aggregate(results: list[IndicatorResult]) -> Verdict:
    """Weighted-average score across indicators that returned data.

    Errored indicators (lean == UNKNOWN) are excluded from the average but
    counted in the confidence ratio so the user sees how complete the read is.
    """
    usable = [r for r in results if r.lean is not Lean.UNKNOWN and r.weight > 0]
    total_weight = sum(r.weight for r in usable)
    if total_weight == 0:
        return Verdict(
            label="Insufficient data",
            score=0.0,
            confidence=0.0,
            contributing=0,
            total=len(results),
        )
    weighted_sum = sum(r.score * r.weight for r in usable)
    score = weighted_sum / total_weight
    label = _label_for(score)
    confidence = len(usable) / len(results) if results else 0.0
    return Verdict(
        label=label,
        score=score,
        confidence=confidence,
        contributing=len(usable),
        total=len(results),
    )


def _label_for(score: float) -> str:
    if score >= 60:
        return "Strongly bullish"
    if score >= 25:
        return "Bullish"
    if score > -25:
        return "Neutral"
    if score > -60:
        return "Bearish"
    return "Strongly bearish"
