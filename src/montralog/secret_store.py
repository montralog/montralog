"""Authenticated encryption of integration credentials with an operator-held key."""
import json
import os
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.fernet import Fernet, InvalidToken
from .storage import StorageError, database

PREFIX = 'enc:v2:'
LEGACY_PREFIX = 'enc:v1:'


def cipher(required=False):
    key = os.getenv('MONTRALOG_ENCRYPTION_KEY', '')
    if not key:
        if required or os.getenv('MONTRALOG_ENCRYPTION_REQUIRED', '').lower() == 'true':
            raise StorageError('Integration encryption key is required.')
        return None
    try:
        return Fernet(key.encode('ascii'))
    except (ValueError, UnicodeError):
        raise StorageError('Integration encryption key is invalid.') from None


def seal(value):
    encryptor = cipher()
    if not value:
        return value
    if encryptor:
        from .tenancy import tenant_id
        derived=HKDF(algorithm=hashes.SHA256(),length=32,salt=None,info=('montralog/integration/v2/'+tenant_id()).encode()).derive(base64.urlsafe_b64decode(os.environ['MONTRALOG_ENCRYPTION_KEY']))
        return PREFIX+Fernet(base64.urlsafe_b64encode(derived)).encrypt(value.encode()).decode('ascii')
    return value


def reveal(value):
    if not value.startswith((PREFIX,LEGACY_PREFIX)):
        if value.startswith('enc:'):raise StorageError('Unsupported integration encryption format.')
        return value
    try:
        encryptor=cipher(required=True)
        if value.startswith(PREFIX):
            from .tenancy import tenant_id
            derived=HKDF(algorithm=hashes.SHA256(),length=32,salt=None,info=('montralog/integration/v2/'+tenant_id()).encode()).derive(base64.urlsafe_b64decode(os.environ['MONTRALOG_ENCRYPTION_KEY']))
            encryptor=Fernet(base64.urlsafe_b64encode(derived))
        return encryptor.decrypt(value.split(':',2)[2].encode('ascii')).decode()
    except (InvalidToken, ValueError, UnicodeError):
        raise StorageError('Integration credential cannot be decrypted; check the encryption key.') from None


def encrypt_existing():
    # Validate every encrypted value too. A wrong key aborts the whole transaction.
    cipher(required=True)
    changed = 0
    with database() as db:
        for table in ('data_sources', 'notification_channels'):
            for row in list(db.execute('SELECT id,secret FROM ' + table)):
                value = row['secret']
                if value.startswith(PREFIX):
                    reveal(value)
                elif value:
                    value=reveal(value)
                    db.execute('UPDATE ' + table + ' SET secret=? WHERE id=?', (seal(value), row['id']))
                    changed += 1
        for row in list(db.execute('SELECT provider,config FROM identity_providers')):
            config = json.loads(row['config'])
            value = config.get('client_secret', '')
            if value.startswith(PREFIX):
                reveal(value)
            elif value:
                value=reveal(value)
                config['client_secret'] = seal(value)
                db.execute('UPDATE identity_providers SET config=? WHERE provider=?', (json.dumps(config), row['provider']))
                changed += 1
    return changed


def verify_existing():
    """Read-only verification for restoration and upgrade acceptance."""
    cipher(required=True)
    encrypted = plaintext = legacy = 0
    with database() as db:
        values = [row[0] for table in ('data_sources', 'notification_channels')
                  for row in db.execute('SELECT secret FROM ' + table)]
        values += [json.loads(row[0]).get('client_secret', '') for row in db.execute('SELECT config FROM identity_providers')]
        for value in values:
            if value.startswith((PREFIX,LEGACY_PREFIX)):
                reveal(value)
                encrypted += 1
                if value.startswith(LEGACY_PREFIX):legacy+=1
            elif value:
                plaintext += 1
    return {'encrypted': encrypted, 'plaintext': plaintext, **({'legacy':legacy} if legacy else {})}
