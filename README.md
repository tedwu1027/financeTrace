# financeTrace

Daily aggregator of US macro and sentiment indicators. Produces a one-page
markdown report with an overall **market-direction** verdict (strongly
bullish → strongly bearish) and a JSON snapshot of each indicator.

The composite is built from twelve indicators across three buckets:

| Bucket | Indicator | Source |
|---|---|---|
| Macro | 10Y-2Y Treasury spread | FRED `T10Y2Y` |
| Macro | JOLTS job openings | FRED `JTSJOL` |
| Macro | WTI crude oil | FRED `DCOILWTICO` |
| Macro | CPI rent YoY | FRED `CUUR0000SEHA` |
| Macro | Inventory-to-sales ratio | FRED `ISRATIO` |
| Macro | Credit card delinquency | FRED `DRCCLACBS` |
| Macro | Strategic Petroleum Reserve | EIA `MCSSTUS1` |
| Valuation | Buffett indicator (Wilshire/GDP) | FRED `WILL5000PRFC` / `GDP` |
| Valuation | Current Market Valuation composite | currentmarketvaluation.com |
| Sentiment | NAAIM exposure index | naaim.org |
| Sentiment | AAII bull-bear spread | aaii.com |
| Sentiment | CNN Fear & Greed | edition.cnn.com |

Sentiment indicators are read **contrarian** (extreme greed → bearish).

## Setup

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env  # then fill in FRED_API_KEY and EIA_API_KEY
```

Both API keys are free:
- FRED: https://fred.stlouisfed.org/docs/api/api_key.html
- EIA: https://www.eia.gov/opendata/register.php

## Run

```sh
financetrace               # prints the markdown report and writes reports/YYYY-MM-DD.{md,json}
financetrace --no-write    # stdout only
financetrace --json-only   # JSON to stdout
python -m financetrace     # equivalent
```

## Daily schedule

A simple cron entry (replace paths):

```cron
30 14 * * 1-5 cd /path/to/financeTrace && /path/to/.venv/bin/financetrace >> logs/daily.log 2>&1
```

Or as a GitHub Actions workflow (sketch — runs at 14:30 UTC each weekday):

```yaml
name: daily-report
on:
  schedule:
    - cron: "30 14 * * 1-5"
  workflow_dispatch:
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e .
      - env:
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
          EIA_API_KEY: ${{ secrets.EIA_API_KEY }}
        run: financetrace
      - uses: actions/upload-artifact@v4
        with:
          name: report
          path: reports/
```

## Tests

```sh
pip install pytest
pytest
```

The unit tests cover the scoring/aggregation and report layers using
fixtures — no network access required.

## Design notes

- Each source returns an `IndicatorResult` with a normalized score in
  `[-100, +100]`, a categorical `Lean`, and a free-text rationale.
- The composite is a weight-averaged mean over indicators that returned
  data; errored fetchers are listed under "Indicators with errors" but
  do not zero-out the composite.
- The MacroMicro proprietary "Bull and Bear" indicator is not available
  via a public API; primary-source equivalents (Buffett, NAAIM, AAII,
  CMV, F&G) cover the same ground.
- Scrapers (NAAIM, AAII, CMV) parse public web pages and will need
  occasional maintenance when those sites change their markup.

## Not investment advice.
