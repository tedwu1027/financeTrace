import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

FRED_API_KEY = os.getenv("FRED_API_KEY", "").strip()
EIA_API_KEY = os.getenv("EIA_API_KEY", "").strip()

REPORT_DIR = Path(os.getenv("FINANCETRACE_REPORT_DIR", "reports")).expanduser()
HTTP_TIMEOUT = float(os.getenv("FINANCETRACE_HTTP_TIMEOUT", "20"))
USER_AGENT = os.getenv(
    "FINANCETRACE_USER_AGENT",
    "financetrace/0.1 (+https://github.com/tedwu1027/financetrace)",
)
