"""Environment configuration shared by application modules."""
import os
from pathlib import Path

VERSION = '0.6.0'
ROOT = Path(__file__).parent
MAX_BODY = 2 * 1024 * 1024
MAX_BATCH = 1000

def database_url():
    return os.getenv('MONTRALOG_DATABASE_URL', '')
