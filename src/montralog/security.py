import hmac
import os
import secrets
import re


def valid_machine_token(raw,scope,tenant):
    prefix='mtls1.'+tenant+'.'+scope+'.'
    return isinstance(raw,str) and raw.startswith(prefix) and re.fullmatch(r'[A-Za-z0-9_-]{43,128}',raw[len(prefix):]) is not None


def machine_token(scope, tenant=None):
    from .tenancy import tenant_id
    return 'mtls1.'+(tenant or tenant_id())+'.'+scope+'.'+secrets.token_urlsafe(36)


def token_matches(env, candidate):
    from .tenancy import tenant_id
    scope='ingest' if env=='MONTRALOG_INGEST_TOKEN' else 'read'
    if candidate.startswith('mtls1.') and not candidate.startswith('mtls1.'+tenant_id()+'.'+scope+'.'):
        return False
    expected = os.getenv(env,'')
    if os.getenv('MONTRALOG_SILO_STRICT','').lower()=='true' and not valid_machine_token(expected,scope,tenant_id()):
        return False
    if len(expected) >= 32 and hmac.compare_digest(expected, candidate):return True
    if candidate.startswith('mtl_'):
        if os.getenv('MONTRALOG_SILO_STRICT','').lower()=='true' and not candidate.startswith('mtl_'+tenant_id()+'.'):return False
        from .studio import token_valid
        return token_valid(candidate,'ingest' if env=='MONTRALOG_INGEST_TOKEN' else 'read')
    return False

def validate_config():
    from .secret_store import cipher
    cipher()
    for name in ('MONTRALOG_READ_TOKEN','MONTRALOG_INGEST_TOKEN'):
        if len(os.getenv(name,'')) < 32:
            raise SystemExit(f'{name} must contain at least 32 characters')
        if os.getenv('MONTRALOG_SILO_STRICT','').lower()=='true':
            from .tenancy import tenant_id
            scope='read' if name=='MONTRALOG_READ_TOKEN' else 'ingest'
            if not valid_machine_token(os.environ[name],scope,tenant_id()):
                raise SystemExit('Strict silo mode requires customer-bound machine tokens; use the upgrade guide.')
    if os.environ['MONTRALOG_READ_TOKEN'] == os.environ['MONTRALOG_INGEST_TOKEN']:
        raise SystemExit('Read and ingest tokens must differ')
