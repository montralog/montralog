"""Disposable browser fixture: never reads an operator env file or database."""
import os
from pathlib import Path
import secrets
import sys
import tempfile
from wsgiref.simple_server import make_server
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from cryptography.fernet import Fernet
from montralog import storage
from montralog.accounts import create_account
from montralog.ingestion import ingest
from montralog.http import application

with tempfile.TemporaryDirectory(prefix='montralog-browser-') as temporary:
    os.environ.update(MONTRALOG_DATABASE_URL='', MONTRALOG_READ_TOKEN=secrets.token_urlsafe(32),
        MONTRALOG_INGEST_TOKEN=secrets.token_urlsafe(32), MONTRALOG_ENCRYPTION_KEY=Fernet.generate_key().decode(),
        MONTRALOG_COOKIE_SECURE='false', PROMETHEUS_URL='', MONTRALOG_COLLECTOR_URL='')
    storage.DB = Path(temporary) / 'browser.db'
    storage.initialize()
    create_account('admin', 'Browser owner', 'Browser-fixture-password-1')
    create_account('paneladmin', 'Browser panel administrator', 'Browser-fixture-password-1')
    with storage.database() as db:
        db.execute("INSERT INTO user_roles(user_id,role) SELECT id,'admin' FROM users WHERE username='paneladmin'")
    create_account('viewer', 'Browser viewer', 'Browser-fixture-password-1')
    ingest('logs', [{'service': 'checkout', 'environment': 'browser-test', 'severity': 'ERROR', 'message': 'Browser fixture error'},
                    {'service': 'checkout', 'environment': 'browser-test', 'message': '<img src=x onerror="window.__montralogXss=1">'}])
    with make_server('127.0.0.1', 8099, application) as server:
        server.serve_forever()
