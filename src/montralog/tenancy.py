"""Silo tenancy: one immutable tenant identity per database and gateway stack."""
import os
import re
import hashlib
import hmac


def tenant_id():
    ident = os.getenv('MONTRALOG_TENANT_ID', 'default')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', ident):
        raise ValueError('MONTRALOG_TENANT_ID must be 1-48 lowercase letters, numbers or dashes.')
    if os.getenv('MONTRALOG_TENANCY_MODE', 'isolated') != 'isolated':
        raise ValueError('Only isolated Docker stacks are supported; shared tenancy is disabled.')
    return ident


def cookie_name(base):
    ident = tenant_id()
    return base if ident == 'default' else base + '_' + ident


def check_binding(db):
    from .storage import StorageError
    row = db.execute('SELECT tenant_id,key_fingerprint FROM deployment_identity WHERE id=1').fetchone()
    if not row or row[0] != tenant_id():
        raise StorageError('Database tenant binding does not match this deployment.')
    if row[1] and not hmac.compare_digest(row[1],key_fingerprint()):
        raise StorageError('Database encryption key binding does not match this deployment.')


def key_fingerprint():
    key=os.getenv('MONTRALOG_ENCRYPTION_KEY','')
    return hashlib.sha256(key.encode()).hexdigest() if key else ''


def bind(db):
    db.execute('INSERT INTO deployment_identity(id,tenant_id) VALUES (1,?) ON CONFLICT(id) DO NOTHING', (tenant_id(),))
    row=db.execute('SELECT key_fingerprint FROM deployment_identity WHERE id=1').fetchone()
    if not row[0] and key_fingerprint():
        # Validate legacy ciphertext before pinning an upgraded database to a key.
        import json
        from .secret_store import reveal
        for table in ('data_sources','notification_channels'):
            for item in db.execute('SELECT secret FROM '+table):reveal(item[0])
        for item in db.execute('SELECT config FROM identity_providers'):
            reveal(json.loads(item[0]).get('client_secret',''))
        db.execute('UPDATE deployment_identity SET key_fingerprint=? WHERE id=1',(key_fingerprint(),))
    check_binding(db)
