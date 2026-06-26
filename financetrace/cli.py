from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from financetrace.config import REPORT_DIR
from financetrace.html_report import render_html
from financetrace.report import render_json, render_markdown, write_reports
from financetrace.scoring import aggregate
from financetrace.sources.aaii import aaii_sentiment
from financetrace.sources.base import IndicatorResult
from financetrace.sources.cmv import market_valuation
from financetrace.sources.cnn_fear_greed import fear_and_greed
from financetrace.sources.eia import spr_level
from financetrace.sources.fred import (
    buffett_indicator,
    cpi_rent_yoy,
    credit_card_delinquency,
    inventory_to_sales,
    jolts_openings,
    t10y2y,
    wti_crude,
)
from financetrace.sources.naaim import naaim_exposure


# Order matters for the report layout: macro first, then valuation, then sentiment.
INDICATOR_FUNCS = [
    t10y2y,
    jolts_openings,
    wti_crude,
    cpi_rent_yoy,
    inventory_to_sales,
    credit_card_delinquency,
    spr_level,
    buffett_indicator,
    market_valuation,
    naaim_exposure,
    aaii_sentiment,
    fear_and_greed,
]


def run_all() -> list[IndicatorResult]:
    results: list[IndicatorResult] = []
    for fn in INDICATOR_FUNCS:
        results.append(fn())
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="financetrace",
        description="Generate today's US macro/sentiment composite report.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Print the report to stdout but do not write files under the report directory.",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Print JSON to stdout instead of the markdown table.",
    )
    parser.add_argument(
        "--site-dir",
        default="site",
        help="Directory to write the dashboard's index.html / latest.json into (default: ./site).",
    )
    args = parser.parse_args(argv)

    today = date.today()
    results = run_all()
    verdict = aggregate(results)

    md = render_markdown(results, verdict, today)
    js = render_json(results, verdict, today)
    html_body = render_html(results, verdict, today)

    if args.json_only:
        sys.stdout.write(js + "\n")
    else:
        sys.stdout.write(md)

    if not args.no_write:
        paths = write_reports(
            REPORT_DIR, md, js, today,
            html_body=html_body,
            site_dir=Path(args.site_dir),
        )
        for label, path in paths.items():
            sys.stderr.write(f"wrote [{label}] {path}\n")
    return 0 if verdict.contributing > 0 else 1
