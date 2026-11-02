"""Exercise hardened published-image defaults using temporary fixture data."""
import os
from pathlib import Path
import platform
import secrets
import tempfile
from cryptography.fernet import Fernet
import psycopg
from montralog.config import VERSION
from montralog.security import machine_token

assert VERSION == '0.8.1'
assert os.geteuid() == 10001
assert platform.machine() == 'x86_64'
assert not Path('/app/.env').exists()
assert os.getenv('MONTRALOG_ENCRYPTION_REQUIRED') == 'true'
with tempfile.TemporaryDirectory(prefix='montralog-runtime-') as temporary:
    os.environ.update(MONTRALOG_DB=str(Path(temporary)/'runtime.db'), MONTRALOG_DATABASE_URL='',
        MONTRALOG_READ_TOKEN=machine_token('read'), MONTRALOG_INGEST_TOKEN=machine_token('ingest'),
        MONTRALOG_ENCRYPTION_KEY='')
    from montralog.secret_store import cipher, seal, reveal
    from montralog.storage import StorageError
    try:
        cipher()
    except StorageError:
        pass
    else:
        raise AssertionError('Image accepted a missing required encryption key')
    os.environ['MONTRALOG_ENCRYPTION_KEY'] = Fernet.generate_key().decode()
    from montralog.wsgi import application
    encrypted = seal('isolated-runtime-fixture')
    assert encrypted.startswith('enc:v2:') and reveal(encrypted)=='isolated-runtime-fixture'
    assert psycopg.pq.version() > 0
print('PASS: version, non-root runtime, architecture, crypto, PostgreSQL driver and required-key startup')
