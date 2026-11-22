"""Organization display preferences, separate from immutable deployment identity."""
import secrets
import time
from .accounts import AccountError, require_csrf
from .studio import admin
from .storage import database


def route(method, data, user, environ):
    if not user:
        raise AccountError('Sign in to continue.', 401)
    if method == 'POST':
        admin(user)
        require_csrf(environ, user)
        if not isinstance(data, dict):
            raise AccountError('Expected organization display details.')
        if set(data) - {'name', 'description'}:
            raise AccountError('Only organization display details can be changed here.')
        name, description = data.get('name'), data.get('description', '')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
            raise AccountError('Organization name must be 1–80 characters.')
        if not isinstance(description, str) or len(description.strip()) > 160:
            raise AccountError('Description must be at most 160 characters.')
        if any(ord(c) < 32 or ord(c) == 127 for c in name + description):
            raise AccountError('Use single-line organization details without control characters.')
        with database() as db:
            db.execute('UPDATE workspace_settings SET name=?,description=?,updated_at=? WHERE id=1',
                       (name.strip(), description.strip(), time.time()))
            db.execute('INSERT INTO access_audit(id,actor_id,action,target,created_at) VALUES (?,?,?,?,?)',
                       (secrets.token_hex(16), user['id'], 'workspace.updated', 'organization-display', time.time()))
    elif method != 'GET':
        raise AccountError('Method not allowed.', 405)
    with database() as db:
        return dict(db.execute('SELECT name,description,updated_at FROM workspace_settings WHERE id=1').fetchone())
