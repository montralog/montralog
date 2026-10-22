"""OIDC authorization-code login for three explicitly configured providers."""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import urllib.parse
import urllib.request
from http.cookies import SimpleCookie
from . import accounts
from .accounts import AccountError
from .storage import database, postgres_enabled
from .studio import admin

PROVIDERS = {'microsoft': 'Microsoft Entra ID', 'google': 'Google Workspace', 'okta': 'Okta'}


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def endpoint(url, provider):
    p = urllib.parse.urlsplit(url)
    host = p.hostname or ''
    allowed = (host == 'login.microsoftonline.com' if provider == 'microsoft' else
               host in ('accounts.google.com', 'oauth2.googleapis.com', 'www.googleapis.com') if provider == 'google' else
               bool(re.fullmatch(r'[a-z0-9-]+\.(okta\.com|oktapreview\.com|okta-emea\.com)', host)))
    if p.scheme != 'https' or not allowed or p.username or p.password or p.port not in (None, 443) or p.fragment or p.query:
        raise AccountError('Use the supported provider HTTPS endpoint.')
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request_json(url, provider, form=None):
    endpoint(url, provider)
    req = urllib.request.Request(url, data=urllib.parse.urlencode(form).encode() if form else None,
                                 headers={'Accept': 'application/json'})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=8) as response:
            raw = response.read(2*1024*1024+1)
        if len(raw) > 2*1024*1024:
            raise ValueError()
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError()
        return result
    except Exception:
        raise AccountError('Provider request failed. Check registration and network access.', 400) from None


def metadata(config):
    provider = config['provider']
    result = request_json(config['issuer']+'/.well-known/openid-configuration', provider)
    if result.get('issuer') != config['issuer']:
        raise AccountError('Provider issuer does not match the configured issuer.')
    for name in ('authorization_endpoint', 'token_endpoint', 'jwks_uri'):
        endpoint(result.get(name, ''), provider)
    return result


def safe(config):
    return {k: v for k, v in config.items() if k != 'client_secret'} | {'has_secret': bool(config.get('client_secret'))}


def settings(method, data, user, environ):
    admin(user)
    with database() as db:
        configs = {r['provider']: json.loads(r['config']) for r in db.execute('SELECT * FROM identity_providers')}
    if method == 'GET':
        return {'items': [safe(c) for c in configs.values()], 'providers': PROVIDERS}
    if method != 'POST':
        raise AccountError('Not found', 404)
    accounts.require_csrf(environ, user)
    provider = data.get('provider')
    if provider not in PROVIDERS:
        raise AccountError('Unknown identity provider.')
    old = configs.get(provider, {})
    if data.get('action') == 'disable':
        with database() as db:
            db.execute('DELETE FROM sessions WHERE user_id IN (SELECT user_id FROM external_identities WHERE provider=?)', (provider,))
            db.execute('DELETE FROM identity_providers WHERE provider=?', (provider,))
            db.execute('DELETE FROM identity_states WHERE provider=?', (provider,))
        return {'ok': True}
    config = {k: str(data.get(k, '')).strip() for k in ('issuer', 'client_id', 'redirect_uri', 'domain')}
    config.update(provider=provider, client_secret=str(data.get('client_secret') or old.get('client_secret', '')))
    if provider == 'google':
        config['issuer'] = 'https://accounts.google.com'
        if not re.fullmatch(r'[a-z0-9][a-z0-9.-]{0,251}\.[a-z]{2,63}', config['domain']):
            raise AccountError('Set your exact Google Workspace hosted domain.')
    endpoint(config['issuer'], provider)
    if provider == 'microsoft' and not re.fullmatch(r'https://login.microsoftonline.com/[0-9a-fA-F-]{36}/v2.0', config['issuer']):
        raise AccountError('Use a tenant-specific Microsoft issuer with the tenant UUID.')
    redirect = urllib.parse.urlsplit(config['redirect_uri'])
    if redirect.scheme != 'https' and not (redirect.scheme == 'http' and redirect.hostname in ('localhost', '127.0.0.1')):
        raise AccountError('Use HTTPS callback, or loopback HTTP for local testing.')
    if redirect.scheme == 'https' and os.getenv('MONTRALOG_COOKIE_SECURE', '').lower() != 'true':
        raise AccountError('Enable MONTRALOG_COOKIE_SECURE=true before configuring remote HTTPS sign-in.')
    if not redirect.hostname or redirect.username or redirect.password or redirect.query or redirect.fragment or redirect.path != '/auth/oidc/callback/'+provider:
        raise AccountError('Callback path must be /auth/oidc/callback/'+provider)
    if not 1 <= len(config['client_id']) <= 512 or not 1 <= len(config['client_secret']) <= 4096:
        raise AccountError('Provide client ID and secret.')
    metadata(config)
    if data.get('action') == 'test':
        return {'ok': True, 'message': 'Discovery reachable. A real sign-in is still required to verify the registration.'}
    with database() as db:
        db.execute('INSERT INTO identity_providers(provider,config) VALUES (?,?) ON CONFLICT(provider) DO UPDATE SET config=excluded.config', (provider, json.dumps(config)))
        db.execute('DELETE FROM identity_states WHERE provider=?', (provider,))
        db.execute('INSERT INTO access_audit(id,actor_id,action,target,created_at) VALUES (?,?,?,?,?)', (secrets.token_hex(16), user['id'], 'identity-configure', provider, time.time()))
    return {'ok': True}


def public_providers():
    with database() as db:
        return {'items': [{'id': r['provider'], 'name': PROVIDERS[r['provider']]} for r in db.execute('SELECT provider FROM identity_providers ORDER BY provider')]}


def binding_cookie(value, secure, expired=False):
    return ('Set-Cookie', 'montralog_oidc='+value+'; Path=/auth/oidc/; HttpOnly; SameSite=Lax; Max-Age='+('0' if expired else '600')+('; Secure' if secure else ''))


def flow(path, params, environ):
    provider = path.rsplit('/', 1)[-1]
    if provider not in PROVIDERS:
        raise AccountError('Unknown provider.', 404)
    with database() as db:
        row = db.execute('SELECT config FROM identity_providers WHERE provider=?', (provider,)).fetchone()
    if not row:
        raise AccountError('This provider is not configured.', 404)
    config = json.loads(row[0]); secure = config['redirect_uri'].startswith('https:')
    if '/start/' in path:
        state, browser, nonce, verifier = [secrets.token_urlsafe(32) for _ in range(4)]
        now = time.time(); source = digest(environ.get('REMOTE_ADDR', ''))
        with database() as db:
            if not postgres_enabled(): db.execute('BEGIN IMMEDIATE')
            else: db.execute('SELECT pg_advisory_xact_lock(76674703)')
            db.execute('DELETE FROM identity_states WHERE expires_at<?', (now,))
            if db.execute('SELECT COUNT(*) FROM identity_states WHERE source=?', (source,)).fetchone()[0] >= 20:
                raise AccountError('Too many sign-in starts. Try again in ten minutes.', 429)
            db.execute('INSERT INTO identity_states(state_hash,provider,binding_hash,nonce,verifier,source,expires_at) VALUES (?,?,?,?,?,?,?)', (digest(state), provider, digest(browser), nonce, verifier, source, now+600))
        meta = metadata(config)
        query = dict(client_id=config['client_id'], redirect_uri=config['redirect_uri'], response_type='code', scope='openid profile email', state=state, nonce=nonce, code_challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('='), code_challenge_method='S256')
        if provider == 'google': query['hd'] = config['domain']
        return meta['authorization_endpoint']+'?'+urllib.parse.urlencode(query), [binding_cookie(browser, secure)]
    cookies = SimpleCookie()
    try:
        cookies.load(environ.get('HTTP_COOKIE', ''))
        binding = cookies['montralog_oidc'].value
    except Exception:
        raise AccountError('Sign-in browser verification failed. Start again.', 401) from None
    with database() as db:
        if not postgres_enabled(): db.execute('BEGIN IMMEDIATE')
        else: db.execute('SELECT pg_advisory_xact_lock(76674703)')
        row = db.execute('SELECT * FROM identity_states WHERE state_hash=? AND provider=? AND binding_hash=? AND expires_at>?', (digest(params.get('state', '')), provider, digest(binding), time.time())).fetchone()
        if not row: raise AccountError('Sign-in expired or already used. Start again.', 401)
        state = dict(row)
        db.execute('DELETE FROM identity_states WHERE state_hash=?', (state['state_hash'],))
    if params.get('error') or not params.get('code'):
        raise AccountError('Provider sign-in was not completed.', 401)
    meta = metadata(config)
    tokens = request_json(meta['token_endpoint'], provider, dict(grant_type='authorization_code', code=params['code'], redirect_uri=config['redirect_uri'], client_id=config['client_id'], client_secret=config['client_secret'], code_verifier=state['verifier']))
    claims = verify(tokens.get('id_token', ''), request_json(meta['jwks_uri'], provider), config, state['nonce'])
    with database() as db:
        if not postgres_enabled(): db.execute('BEGIN IMMEDIATE')
        else: db.execute('SELECT pg_advisory_xact_lock(76674703)')
        # Refuse in-flight login if configuration changed or was disabled.
        current = db.execute('SELECT config FROM identity_providers WHERE provider=?', (provider,)).fetchone()
        if not current or json.loads(current[0]) != config: raise AccountError('Provider configuration changed. Start again.', 401)
        existing = db.execute('SELECT user_id FROM external_identities WHERE provider=? AND issuer=? AND subject=?', (provider, config['issuer'], claims['sub'])).fetchone()
        if existing: uid = existing[0]
        else:
            uid = secrets.token_hex(16)
            # Never merge by email or inherit external admin/group claims.
            db.execute('INSERT INTO users(id,username,name,email,password_hash,created_at) VALUES (?,?,?,?,?,?)', (uid, provider+'-'+uid, str(claims.get('name') or PROVIDERS[provider]+' user')[:100], '', accounts.password_hash(secrets.token_urlsafe(48)), time.time()))
            db.execute('INSERT INTO external_identities(provider,issuer,subject,user_id) VALUES (?,?,?,?)', (provider, config['issuer'], claims['sub'], uid))
        raw, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        db.execute('DELETE FROM sessions WHERE expires_at<?', (time.time(),))
        db.execute('INSERT INTO sessions(token_hash,user_id,csrf,created_at,expires_at) VALUES (?,?,?,?,?)', (digest(raw), uid, csrf, time.time(), time.time()+accounts.SESSION_SECONDS))
    return '/', [accounts.cookie(raw), binding_cookie('', secure, True)]


def verify(token, jwks, config, nonce):
    from joserfc import jwt
    from joserfc.jwk import KeySet
    try:
        decoded = jwt.decode(token, KeySet.import_key_set(jwks), algorithms=['RS256'])
        c = decoded.claims
        jwt.JWTClaimsRegistry(leeway=30, iss={'essential': True, 'value': config['issuer']}, aud={'essential': True, 'value': config['client_id']}, exp={'essential': True}, iat={'essential': True}, sub={'essential': True}, nonce={'essential': True, 'value': nonce}).validate(c)
        if not isinstance(c['sub'], str) or not 1 <= len(c['sub']) <= 255: raise ValueError()
        if c['iat'] > time.time()+30: raise ValueError()
        if (isinstance(c['aud'], list) and len(c['aud']) > 1 or 'azp' in c) and c.get('azp') != config['client_id']: raise ValueError()
        if config['provider'] == 'google' and (c.get('hd') != config['domain'] or c.get('email_verified') is not True): raise ValueError()
        return c
    except Exception:
        raise AccountError('Provider identity verification failed.', 401) from None
