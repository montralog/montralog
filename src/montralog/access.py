"""Administrator-managed organizational membership; no telemetry isolation."""
import secrets
import time
from .accounts import AccountError, require_csrf
from .storage import database, postgres_enabled
from .studio import admin


def route(method, data, user, environ):
    admin(user)
    if method not in ('GET', 'POST'):
        raise AccountError('Not found', 404)
    if method == 'POST':
        require_csrf(environ, user)
    with database() as db:
        if method == 'POST':
            # Serialize role changes, including the last-administrator check.
            if postgres_enabled():
                db.execute('SELECT pg_advisory_xact_lock(76674702)')
            else:
                db.execute('BEGIN IMMEDIATE')
            actor = db.execute('SELECT role FROM user_roles WHERE user_id=?', (user['id'],)).fetchone()
            if not actor or actor[0] != 'admin':
                raise AccountError('Administrator access changed. Sign in again.', 403)
            action = data.get('action')
            target = str(data.get('id', ''))
            if action == 'create':
                kind, name = data.get('kind'), data.get('name')
                if kind not in ('team', 'group') or not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
                    raise AccountError('Choose team or group and a name of 1â€“80 characters.')
                name = name.strip()
                if db.execute('SELECT id FROM access_collections WHERE kind=? AND name=?', (kind, name)).fetchone():
                    raise AccountError('That name already exists.')
                if db.execute('SELECT COUNT(*) FROM access_collections').fetchone()[0] >= 200:
                    raise AccountError('Limit of 200 teams and groups reached.')
                target = secrets.token_hex(16)
                db.execute('INSERT INTO access_collections(id,kind,name,created_at) VALUES (?,?,?,?)', (target, kind, name, time.time()))
            elif action in ('member-add', 'member-remove', 'delete'):
                if not db.execute('SELECT id FROM access_collections WHERE id=?', (target,)).fetchone():
                    raise AccountError('Team or group not found.', 404)
                if action == 'delete':
                    if db.execute('SELECT user_id FROM access_members WHERE collection_id=? LIMIT 1', (target,)).fetchone():
                        raise AccountError('Remove members before deleting this team or group.')
                    db.execute('DELETE FROM access_members WHERE collection_id=?', (target,))
                    db.execute('DELETE FROM access_collections WHERE id=?', (target,))
                else:
                    uid = str(data.get('user_id', ''))
                    if not db.execute('SELECT id FROM users WHERE id=?', (uid,)).fetchone():
                        raise AccountError('User not found.', 404)
                    if action == 'member-add':
                        db.execute('INSERT INTO access_members(collection_id,user_id) VALUES (?,?) ON CONFLICT(collection_id,user_id) DO NOTHING', (target, uid))
                    else:
                        db.execute('DELETE FROM access_members WHERE collection_id=? AND user_id=?', (target, uid))
                    target += ':' + uid
            elif action == 'role':
                role = data.get('role')
                if role not in ('admin', 'viewer'):
                    raise AccountError('Choose administrator or viewer.')
                if not db.execute('SELECT id FROM users WHERE id=?', (target,)).fetchone():
                    raise AccountError('User not found.', 404)
                old = db.execute('SELECT role FROM user_roles WHERE user_id=?', (target,)).fetchone()
                if old and old[0] == 'admin' and role != 'admin' and db.execute("SELECT COUNT(*) FROM user_roles WHERE role='admin'").fetchone()[0] <= 1:
                    raise AccountError('Keep at least one administrator.')
                db.execute('INSERT INTO user_roles(user_id,role) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET role=excluded.role', (target, role))
                target += ':' + role
            else:
                raise AccountError('Unknown access action.')
            db.execute('INSERT INTO access_audit(id,actor_id,action,target,created_at) VALUES (?,?,?,?,?)', (secrets.token_hex(16), user['id'], action, target, time.time()))
            return {'ok': True}
        users = [dict(r) for r in db.execute("SELECT u.id,u.username,u.name,COALESCE(r.role,'viewer') AS role FROM users u LEFT JOIN user_roles r ON r.user_id=u.id ORDER BY u.username")]
        collections = [dict(r) for r in db.execute('SELECT * FROM access_collections ORDER BY kind,name')]
        members = [dict(r) for r in db.execute('SELECT * FROM access_members')]
        audit = [dict(r) for r in db.execute('SELECT * FROM access_audit ORDER BY created_at DESC LIMIT 100')]
        return {'users': users, 'collections': collections, 'members': members, 'audit': audit}
