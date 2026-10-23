import hmac
import os


def token_matches(env, candidate):
    expected = os.getenv(env,'')
    if len(expected) >= 32 and hmac.compare_digest(expected, candidate):return True
    if candidate.startswith('mtl_'):
        from .studio import token_valid
        return token_valid(candidate,'ingest' if env=='MONTRALOG_INGEST_TOKEN' else 'read')
    return False

def validate_config():
    from .secret_store import cipher
    cipher()
    for name in ('MONTRALOG_READ_TOKEN','MONTRALOG_INGEST_TOKEN'):
        if len(os.getenv(name,'')) < 32:
            raise SystemExit(f'{name} must contain at least 32 characters')
    if os.environ['MONTRALOG_READ_TOKEN'] == os.environ['MONTRALOG_INGEST_TOKEN']:
        raise SystemExit('Read and ingest tokens must differ')
