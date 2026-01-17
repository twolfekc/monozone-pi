"""
MonoZone Pi Controller Configuration
"""
import os
from pathlib import Path

# iTach Connection (TCP to IP-RS232 bridge)
ITACH_HOST = os.getenv("ITACH_HOST", "192.168.1.100")
ITACH_PORT = int(os.getenv("ITACH_PORT", "4999"))
ITACH_TIMEOUT = 2.0
ITACH_RECONNECT_DELAY = 5.0

# API Server
API_HOST = "0.0.0.0"
API_PORT = int(os.getenv("API_PORT", "8080"))

# Database
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "monozone.db"

# Zone Configuration
NUM_ZONES = 6
ZONE_ADDR_OFFSET = 10  # Zone 1 = 11, Zone 6 = 16

# Polling
POLL_INTERVAL = 2.0  # seconds between zone state polls
POLL_ENABLED = True

# Volume limits (safety)
MAX_VOLUME = 38
DEFAULT_VOLUME = 20

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
