"""Local accounts, revocable browser sessions and personal dashboard storage."""
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from http.cookies import SimpleCookie
from .storage import database, postgres_enabled
from .metrics import PANELS

SESSION_SECONDS = 12 * 3600
ITERATIONS = 600_000

class AccountError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status

def password_hash(password, salt=None):
    if not isinstance(password, str) or not 8 <= len(password) <= 256:
        raise AccountError('Use a password of 8–256 characters.')
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return f'{ITERATIONS}${salt}${digest}'

def password_matches(password, encoded):
    if not isinstance(password, str) or len(password) > 256:
        return False
    iterations, salt, digest = encoded.split('$')
    candidate = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(iterations)).hex()
    return hmac.compare_digest(digest, candidate)

def create_account(username, name, password):
    username = username.strip().lower()
    if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{2,63}', username):
        raise AccountError('Username must be 3–64 letters, numbers, dots, dashes or underscores.')
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
        raise AccountError('Display name must be 1–100 characters.')
    encoded = password_hash(password)
    with database() as db:
        # Account creation is an operator-only CLI action, never a public HTTP endpoint.
        if db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone():
            raise AccountError('This username already exists.')
        db.execute('INSERT INTO users(id,username,name,email,password_hash,created_at) VALUES (?,?,?,?,?,?)',
                   (secrets.token_hex(16), username, name.strip(), '', encoded, time.time()))
        if username=='admin':
            row=db.execute('SELECT id FROM users WHERE username=?',(username,)).fetchone()
            db.execute("INSERT INTO user_roles(user_id,role) VALUES (?,'admin') ON CONFLICT(user_id) DO NOTHING",(row['id'],))

def public_user(row):
    result={key: row[key] for key in ('id', 'username', 'name', 'email', 'created_at')}
    with database() as db:
        role=db.execute('SELECT role FROM user_roles WHERE user_id=?',(row['id'],)).fetchone()
    result['role']=role[0] if role else 'viewer'
    return result

def session(environ):
    cookie = SimpleCookie()
    try:
        cookie.load(environ.get('HTTP_COOKIE', ''))
        raw = cookie['montralog_session'].value if 'montralog_session' in cookie else ''
    except Exception:
        return None
    if not re.fullmatch('[A-Za-z0-9_-]{43}', raw):
        return None
    digest = hashlib.sha256(raw.encode()).hexdigest()
    with database() as db:
        row = db.execute('SELECT u.*,s.csrf,s.token_hash,s.expires_at FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token_hash=? AND s.expires_at>?', (digest, time.time())).fetchone()
    if not row:return None
    result=dict(row)
    with database() as db:
        role=db.execute('SELECT role FROM user_roles WHERE user_id=?',(row['id'],)).fetchone()
    result['role']=role[0] if role else 'viewer'
    return result

def require_csrf(environ, user):
    if not hmac.compare_digest(environ.get('HTTP_X_CSRF_TOKEN', ''), user['csrf']):
        raise AccountError('Session verification failed. Reload the page.', 403)

def cookie(value, expired=False):
    secure = '; Secure' if os.getenv('MONTRALOG_COOKIE_SECURE', '').lower() == 'true' else ''
    return ('Set-Cookie', f'montralog_session={value}; Path=/; HttpOnly; SameSite=Strict; Max-Age={0 if expired else SESSION_SECONDS}{secure}')

def login(data, environ):
    username = str(data.get('username', '')).strip().lower()[:64]
    # A database-backed rate limit works across workers and replicas. Never trust
    # forwarded client headers unless a trusted proxy has been configured outside.
    key = hashlib.sha256((environ.get('REMOTE_ADDR', '') + ':' + username).encode()).hexdigest()
    now = time.time()
    with database() as db:
        db.execute('DELETE FROM login_attempts WHERE attempted_at<?', (now-900,))
        count = db.execute('SELECT COUNT(*) FROM login_attempts WHERE attempt_key=?', (key,)).fetchone()[0]
        if count >= 10:
            raise AccountError('Too many attempts. Try again in 15 minutes.', 429)
        db.execute('INSERT INTO login_attempts(id,attempt_key,attempted_at) VALUES (?,?,?)', (secrets.token_hex(16), key, now))
        row = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
    # Equal-cost verification for unknown usernames avoids easy account enumeration.
    encoded = row['password_hash'] if row else f'{ITERATIONS}$' + '00'*16 + '$' + '00'*32
    valid = password_matches(data.get('password'), encoded)
    if not row or not valid:
        raise AccountError('Username or password is incorrect.', 401)
    raw, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    with database() as db:
        if not postgres_enabled():
            db.execute('BEGIN IMMEDIATE')
        lock = ' FOR UPDATE' if postgres_enabled() else ''
        current = db.execute('SELECT password_hash FROM users WHERE id=?'+lock, (row['id'],)).fetchone()
        if not current or current['password_hash'] != encoded:
            raise AccountError('Credentials changed. Sign in again.', 401)
        db.execute('DELETE FROM sessions WHERE expires_at<?', (now,))
        db.execute('DELETE FROM login_attempts WHERE attempt_key=?', (key,))
        db.execute('INSERT INTO sessions(token_hash,user_id,csrf,created_at,expires_at) VALUES (?,?,?,?,?)',
                   (hashlib.sha256(raw.encode()).hexdigest(), row['id'], csrf, now, now+SESSION_SECONDS))
    return {'user': public_user(row), 'csrf': csrf}, cookie(raw)

def account_route(path, method, data, environ, user):
    if not user:
        raise AccountError('Sign in to continue.', 401)
    if method != 'GET':
        require_csrf(environ, user)
    if path == '/api/account' and method == 'GET':
        return {'user': public_user(user), 'csrf': user['csrf'], 'expires_at': user['expires_at']}, []
    if path == '/api/account/logout' and method == 'POST':
        with database() as db:
            db.execute('DELETE FROM sessions WHERE token_hash=?', (user['token_hash'],))
        return {'ok': True}, [cookie('', True)]
    if path == '/api/account/profile' and method == 'POST':
        name, email = data.get('name', ''), data.get('email', '')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
            raise AccountError('Display name must be 1–100 characters.')
        if not isinstance(email, str) or len(email) > 254 or (email and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email)):
            raise AccountError('Enter a valid email address or leave it empty.')
        with database() as db:
            db.execute('UPDATE users SET name=?,email=? WHERE id=?', (name.strip(), email, user['id']))
        user.update(name=name.strip(), email=email)
        return {'user': public_user(user)}, []
    if path == '/api/account/password' and method == 'POST':
        if not password_matches(data.get('current_password'), user['password_hash']):
            raise AccountError('Current password is incorrect.', 400)
        encoded = password_hash(data.get('password'))
        with database() as db:
            db.execute('UPDATE users SET password_hash=? WHERE id=?', (encoded, user['id']))
            db.execute('DELETE FROM sessions WHERE user_id=?', (user['id'],))
        return {'ok': True}, [cookie('', True)]
    if path == '/api/account/sessions' and method == 'GET':
        with database() as db:
            items = [dict(row) for row in db.execute('SELECT token_hash,created_at,expires_at FROM sessions WHERE user_id=? AND expires_at>? ORDER BY created_at DESC', (user['id'], time.time()))]
        for item in items:
            item['current'] = item.pop('token_hash') == user['token_hash']
        return {'items': items}, []
    if path == '/api/account/revoke' and method == 'POST':
        with database() as db:
            db.execute('DELETE FROM sessions WHERE user_id=? AND token_hash<>?', (user['id'], user['token_hash']))
        return {'ok': True}, []
    if path == '/api/saved-dashboards' and method == 'GET':
        with database() as db:
            items = [dict(row) for row in db.execute('SELECT id,name,definition,updated_at FROM dashboards WHERE user_id=? ORDER BY updated_at DESC', (user['id'],))]
        for item in items:
            item['definition'] = json.loads(item['definition'])
        return {'items': items}, []
    if path == '/api/saved-dashboards' and method == 'POST':
        name, definition = data.get('name', ''), data.get('definition', {})
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or not isinstance(definition, dict):
            raise AccountError('Provide a dashboard name of 1–80 characters.')
        from .studio import clean_definition
        clean=clean_definition(definition)
        ident=str(data.get('id',''))
        if ident:
            with database() as db:
                if not db.execute('SELECT id FROM dashboards WHERE id=? AND user_id=?',(ident,user['id'])).fetchone():
                    raise AccountError('Dashboard not found.',404)
                db.execute('UPDATE dashboards SET name=?,definition=?,updated_at=? WHERE id=? AND user_id=?',(name.strip(),json.dumps(clean),time.time(),ident,user['id']))
            return {'id':ident},[]
        ident=secrets.token_hex(16)
        with database() as db:
            if db.execute('SELECT COUNT(*) FROM dashboards WHERE user_id=?', (user['id'],)).fetchone()[0] >= 50:
                raise AccountError('Limit of 50 personal dashboards reached.')
            db.execute('INSERT INTO dashboards(id,user_id,name,definition,updated_at) VALUES (?,?,?,?,?)', (ident, user['id'], name.strip(), json.dumps(clean), time.time()))
        return {'id': ident}, []
    if path == '/api/saved-dashboards/delete' and method == 'POST':
        with database() as db:
            db.execute('DELETE FROM dashboards WHERE id=? AND user_id=?', (str(data.get('id', '')), user['id']))
        return {'ok': True}, []
    raise AccountError('Not found', 404)
