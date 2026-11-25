
from pathlib import Path
import os
from dotenv import load_dotenv

# ==========================================
# PROJECT CONFIGURATION
# ==========================================

PROJECT_DIR = Path(
    r"C:\Users\adity\Downloads\Historical data\BharatMarket_AI"
)

UPSTOX_DIR = PROJECT_DIR / "upstox_integration"

# ==========================================
# DIRECTORY PATHS
# ==========================================

DATA_DIR = UPSTOX_DIR / "data"
CONFIG_DIR = UPSTOX_DIR / "config"
LOG_DIR = UPSTOX_DIR / "logs"

RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
FEATURES_DIR = PROJECT_DIR / "data" / "features"

STAGING_DIR = DATA_DIR / "historical_staging"
BACKUP_DIR = UPSTOX_DIR / "backups"

# ==========================================
# ENVIRONMENT VARIABLES
# ==========================================

load_dotenv(PROJECT_DIR / ".env", override=True)

UPSTOX_ACCESS_TOKEN = os.getenv(
    "UPSTOX_ACCESS_TOKEN", ""
).strip()

if not UPSTOX_ACCESS_TOKEN:
    raise ValueError(
        "UPSTOX_ACCESS_TOKEN not found in project .env file."
    )

# ==========================================
# UPSTOX API
# ==========================================

BASE_URL = "https://api.upstox.com"

HISTORICAL_CANDLE_URL = (
    BASE_URL + "/v3/historical-candle"
)

LIVE_QUOTE_URL = (
    BASE_URL + "/v3/market-quote/quotes"
)

API_HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}"
}

# ==========================================
# INSTRUMENTS
# ==========================================

INSTRUMENTS = [
    "NIFTY50",
    "BANKNIFTY",
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
    "SBIN",
    "ITC",
    "LT",
]

# ==========================================
# FILE CONFIGURATION
# ==========================================

MAPPING_FILE = DATA_DIR / "instrument_mapping.csv"

# ==========================================
# CREATE REQUIRED DIRECTORIES
# ==========================================

for directory in [
    DATA_DIR,
    CONFIG_DIR,
    LOG_DIR,
    RAW_DIR,
    PROCESSED_DIR,
    FEATURES_DIR,
    STAGING_DIR,
    BACKUP_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)
