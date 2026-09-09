"""Application settings and environment variable configuration.

Safely loads configuration from .env with production fallbacks.
Prevents any hardcoding of sensitive parameters.
"""

import os
from pathlib import Path

# Try importing python-dotenv if available
try:
    from dotenv import load_dotenv
    _has_dotenv = True
except ImportError:
    _has_dotenv = False

# Base Directory of the repository
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file if available
ENV_PATH = BASE_DIR / ".env"
if _has_dotenv and ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# Application Meta
APP_NAME = os.getenv("APP_NAME", "Cisco Historical Unused Port Scanner")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
APP_ENV = os.getenv("APP_ENV", "production")

# Excel Storage Configuration
PORT_HISTORY_FILE = os.getenv("PORT_HISTORY_FILE", str(BASE_DIR / "data" / "port_history.xlsx"))
BACKUP_DIR = os.getenv("BACKUP_DIR", str(BASE_DIR / "backups" / "excel_history"))
AUTO_BACKUP_STORAGE = os.getenv("AUTO_BACKUP_STORAGE", "true").lower() in ("true", "1", "yes")

# Scanner Default Settings
DEFAULT_THRESHOLD_DAYS = int(os.getenv("DEFAULT_THRESHOLD_DAYS", "60"))
DEFAULT_SSH_TIMEOUT = int(os.getenv("DEFAULT_SSH_TIMEOUT", "20"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "5"))

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(BASE_DIR / "data" / "app.log"))
