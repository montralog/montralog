"""Operator commands for local preview, retention, migrations and SQLite backup."""
import argparse
import sqlite3
from contextlib import closing
from pathlib import Path
from . import storage
from .http import application
from .security import validate_config

def main():
    parser=argparse.ArgumentParser(prog='montralog')
    parser.add_argument('command',choices=['serve','prune','backup','migrate','create-user','reset-password'],default='serve',nargs='?')
    parser.add_argument('--destination')
    parser.add_argument('--username')
    parser.add_argument('--name')
    args=parser.parse_args()
    storage.initialize()
    if args.command in ('create-user','reset-password'):
        from getpass import getpass
        from .accounts import create_account
        if not args.username or (args.command=='create-user' and not args.name):
            parser.error('--username required; --name also required when creating an account')
        password=getpass('Password (8+ characters): ')
        if password != getpass('Confirm password: '):
            parser.error('Passwords do not match')
        if args.command=='create-user':
            create_account(args.username,args.name,password)
            print('Account created. Sign in through the browser.')
        else:
            from .accounts import password_hash
            encoded=password_hash(password)
            with storage.database() as db:
                user=db.execute('SELECT id FROM users WHERE username=?',(args.username.strip().lower(),)).fetchone()
                if not user:
                    parser.error('Account does not exist')
                db.execute('UPDATE users SET password_hash=? WHERE id=?',(encoded,user['id']))
                db.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],))
            print('Password reset. All sessions revoked.')
    elif args.command=='migrate':
        print('Schema migrations applied')
    elif args.command=='prune':
        print(f'Retention applied: {storage.prune()} days')
    elif args.command=='backup':
        if storage.postgres_enabled():
            parser.error('Use PostgreSQL native backups/PITR; this command backs up SQLite only')
        if not args.destination:
            parser.error('--destination required')
        destination=Path(args.destination)
        if destination.exists() or destination.resolve()==storage.DB.resolve():
            parser.error('Backup destination must be a new file')
        with storage.database() as source,closing(sqlite3.connect(destination)) as target:
            source.backup(target)
        print('Backup completed')
    else:
        validate_config()
        from wsgiref.simple_server import make_server
        print('Montralog local preview: http://127.0.0.1:8080',flush=True)
        with make_server('127.0.0.1',8080,application) as server:
            server.serve_forever()
