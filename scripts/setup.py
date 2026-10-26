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
if hasattr(os, 'geteuid') and os.geteuid() == 0:
    # A root helper container must not leave a mode-600 file owned by root
    # when the bind-mounted checkout belongs to a non-root host operator.
    owner = root.stat()
    os.fchown(fd, owner.st_uid, owner.st_gid)
tenant='tenant-'+secrets.token_hex(8)
with os.fdopen(fd, 'w') as out:
    out.write('MONTRALOG_TENANT_ID=' + tenant + '\n')
    out.write('MONTRALOG_READ_TOKEN=mtls1.'+tenant+'.read.' + secrets.token_urlsafe(36) + '\n')
    out.write('MONTRALOG_INGEST_TOKEN=mtls1.'+tenant+'.ingest.' + secrets.token_urlsafe(36) + '\n')
    out.write('MONTRALOG_ENCRYPTION_KEY=' + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('ascii') + '\n')
    out.write('MONTRALOG_ENCRYPTION_REQUIRED=true\nMONTRALOG_SILO_STRICT=true\n')
    out.write('RETENTION_DAYS=7\n')
print('Created .env. Keep it private and restrict Windows file permissions.')
print('Run: docker compose pull, then docker compose up -d --wait')
print('Create a browser account: docker compose exec gateway python -m montralog create-user --username admin --name Administrator')
print('Sign in at http://localhost:8080 with that account. Keep API tokens in .env private.')
