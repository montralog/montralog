"""Authenticated encryption of integration credentials with an operator-held key."""
import json
import os
from cryptography.fernet import Fernet, InvalidToken
from .storage import StorageError, database

PREFIX = 'enc:v1:'


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
    return PREFIX + encryptor.encrypt(value.encode()).decode('ascii') if encryptor else value


def reveal(value):
    if not value.startswith(PREFIX):
        return value
    try:
        return cipher(required=True).decrypt(value[len(PREFIX):].encode('ascii')).decode()
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
                    db.execute('UPDATE ' + table + ' SET secret=? WHERE id=?', (seal(value), row['id']))
                    changed += 1
        for row in list(db.execute('SELECT provider,config FROM identity_providers')):
            config = json.loads(row['config'])
            value = config.get('client_secret', '')
            if value.startswith(PREFIX):
                reveal(value)
            elif value:
                config['client_secret'] = seal(value)
                db.execute('UPDATE identity_providers SET config=? WHERE provider=?', (json.dumps(config), row['provider']))
                changed += 1
    return changed


def verify_existing():
    """Read-only verification for restoration and upgrade acceptance."""
    cipher(required=True)
    encrypted = plaintext = 0
    with database() as db:
        values = [row[0] for table in ('data_sources', 'notification_channels')
                  for row in db.execute('SELECT secret FROM ' + table)]
        values += [json.loads(row[0]).get('client_secret', '') for row in db.execute('SELECT config FROM identity_providers')]
        for value in values:
            if value.startswith(PREFIX):
                reveal(value)
                encrypted += 1
            elif value:
                plaintext += 1
    return {'encrypted': encrypted, 'plaintext': plaintext}
