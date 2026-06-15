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

The included `.github/workflows/daily.yml` runs at 14:30 UTC every day,
publishes the dashboard to GitHub Pages, and (if Gmail secrets are set)
emails the rendered report.

### Repo secrets needed

| Secret | Used for | Required |
|---|---|---|
| `FRED_API_KEY` | FRED data fetchers | yes (else all FRED indicators are unavailable) |
| `EIA_API_KEY` | EIA SPR fetcher | yes (else SPR is unavailable) |
| `GMAIL_USER` | SMTP from-address | only if you want email delivery |
| `GMAIL_APP_PASSWORD` | SMTP auth | only if you want email delivery |

`GMAIL_APP_PASSWORD` is **not** your normal Google password — generate
an app-specific password at https://myaccount.google.com/apppasswords
(requires 2-Step Verification enabled on your Google account). The
workflow sends to `tedwu1027@gmail.com`; edit `to:` in `daily.yml` to
change the recipient.

### Publishing to GitHub Pages

Repo Settings → Pages → Source = **GitHub Actions**. The first
workflow run will publish `site/index.html` (latest dashboard) at
`https://<owner>.github.io/<repo>/` and archive each day's snapshot
under `archive/<date>.html`.

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
