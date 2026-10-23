"""Create credentials once. Never overwrites an existing .env."""
import base64
import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / '.env'
try:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
except FileExistsError:
    raise SystemExit('.env already exists; preserving your credentials.')
with os.fdopen(fd, 'w') as out:
    out.write('MONTRALOG_READ_TOKEN=' + secrets.token_urlsafe(36) + '\n')
    out.write('MONTRALOG_INGEST_TOKEN=' + secrets.token_urlsafe(36) + '\n')
    out.write('MONTRALOG_ENCRYPTION_KEY=' + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('ascii') + '\n')
    out.write('RETENTION_DAYS=7\n')
print('Created .env. Keep it private and restrict Windows file permissions.')
print('Run: docker compose build gateway, then docker compose up -d --no-build --wait')
print('Create a browser account: docker compose exec gateway python -m montralog create-user --username admin --name Administrator')
print('Sign in at http://localhost:8080 with that account. Keep API tokens in .env private.')
