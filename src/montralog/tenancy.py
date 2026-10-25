"""Silo tenancy: one immutable tenant identity per database and gateway stack."""
import os
import re


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
    row = db.execute('SELECT tenant_id FROM deployment_identity WHERE id=1').fetchone()
    if not row or row[0] != tenant_id():
        raise StorageError('Database tenant binding does not match this deployment.')


def bind(db):
    db.execute('INSERT INTO deployment_identity(id,tenant_id) VALUES (1,?) ON CONFLICT(id) DO NOTHING', (tenant_id(),))
    check_binding(db)
