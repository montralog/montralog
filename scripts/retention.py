import logging
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from montralog.storage import initialize, prune

initialize()
while True:
    try:
        print(f'Retention applied: {prune()} days',flush=True)
    except Exception:
        logging.exception('Retention failed; operator action required')
    time.sleep(3600)
