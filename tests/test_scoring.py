from datetime import date

from financetrace.html_report import render_html
from financetrace.report import render_markdown
from financetrace.scoring import aggregate
from financetrace.sources.base import IndicatorResult, Lean


def _res(name: str, lean: Lean, score: float, weight: float = 1.0) -> IndicatorResult:
    return IndicatorResult(
        name=name,
        value=1.0,
        asof="2026-06-01",
        lean=lean,
        score=score,
        notes="test fixture",
        source_url="https://example.com",
        weight=weight,
    )


def test_aggregate_returns_strongly_bullish_for_all_bull():
    results = [
        _res("a", Lean.STRONG_BULL, 100),
        _res("b", Lean.BULL, 50),
        _res("c", Lean.BULL, 50),
    ]
    v = aggregate(results)
    assert v.contributing == 3
    assert v.total == 3
    assert v.label in {"Bullish", "Strongly bullish"}
    assert v.score > 25


def test_aggregate_handles_errored_indicators():
    err = IndicatorResult.errored("z", "https://example.com", "boom", weight=1.0)
    results = [
        _res("a", Lean.BEAR, -50, weight=2.0),
        err,
    ]
    v = aggregate(results)
    assert v.contributing == 1
    assert v.total == 2
    assert v.confidence == 0.5
    assert v.label == "Bearish"
    assert v.score == -50.0


def test_weighted_average_respects_weights():
    results = [
        _res("heavy_bear", Lean.STRONG_BEAR, -100, weight=3.0),
        _res("light_bull", Lean.STRONG_BULL, 100, weight=1.0),
    ]
    v = aggregate(results)
    assert v.score == -50.0
    assert v.label == "Bearish"


def test_markdown_renders_without_crashing():
    results = [
        _res("a", Lean.BULL, 50),
        IndicatorResult.errored("b", "https://example.com", "boom"),
    ]
    md = render_markdown(results, aggregate(results), date(2026, 6, 13))
    assert "# financeTrace daily" in md
    assert "Indicators with errors" in md
    assert "boom" in md


def test_html_renders_with_healthy_and_errored_sections():
    results = [
        _res("ten-two", Lean.BULL, 50),
        _res("buffett", Lean.STRONG_BEAR, -100),
        IndicatorResult.errored("missing-key", "https://example.com", "no key"),
    ]
    html = render_html(results, aggregate(results), date(2026, 6, 13))
    assert "<!doctype html>" in html
    assert "financeTrace" in html
    assert "Indicators" in html
    assert "Unavailable" in html
    # Verdict and badges should render labels
    assert "Strong Bear" in html or "Bull" in html
    # The error message itself should be visible in the unavailable card
    assert "no key" in html
