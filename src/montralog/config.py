"""Environment configuration shared by application modules."""
import os
from pathlib import Path

VERSION = '0.8.1'
ROOT = Path(__file__).parent
MAX_BODY = 2 * 1024 * 1024
MAX_BATCH = 1000

def database_url():
    return os.getenv('MONTRALOG_DATABASE_URL', '')
