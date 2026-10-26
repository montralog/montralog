"""Transactional storage with versioned schema and bounded database waits.

SQLite supports local single-replica installations. PostgreSQL supports replicated
gateways. PostgreSQL availability, backup and failover remain operator responsibilities.
"""
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from .config import database_url, ROOT

DB = Path(os.getenv('MONTRALOG_DB',str(Path.cwd()/'data'/'montralog.db')))
SCHEMA_VERSION = 7

class StorageError(Exception):
    """A storage failure safe to expose as a generic HTTP 503."""

def postgres_enabled():
    return bool(database_url())

class Row(dict):
    def __getitem__(self,key):
        return list(self.values())[key] if isinstance(key,int) else super().__getitem__(key)

class Result:
    def __init__(self,cursor):
        self.cursor=cursor
    def fetchone(self):
        row=self.cursor.fetchone()
        return Row(row) if row is not None else None
    def __iter__(self):
        return (Row(row) for row in self.cursor)

class PostgresConnection:
    def __init__(self,connection):
        self.connection=connection
        self.total_changes=0
    def execute(self,sql,params=()):
        cursor=self.connection.execute(sql.replace('?', '%s'),params)
        if cursor.statusmessage.startswith(('INSERT','UPDATE','DELETE')):
            self.total_changes+=max(0,cursor.rowcount)
        return Result(cursor)
    def executemany(self,sql,rows):
        with self.connection.cursor() as cursor:
            cursor.executemany(sql.replace('?', '%s'),rows)
            self.total_changes+=max(0,cursor.rowcount)

@contextmanager
def database(check_tenant=True):
    if postgres_enabled():
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as error:
            raise StorageError('Install the PostgreSQL dependency') from error
        try:
            # No credentials or raw connection strings are logged.
            with psycopg.connect(database_url(),connect_timeout=5,row_factory=dict_row,
                                 options='-c statement_timeout=10000 -c lock_timeout=5000') as connection:
                db = PostgresConnection(connection)
                if check_tenant:
                    from .tenancy import check_binding
                    check_binding(db)
                yield db
        except psycopg.Error as error:
            raise StorageError('PostgreSQL operation failed') from error
    else:
        try:
            DB.parent.mkdir(parents=True,exist_ok=True)
            connection=sqlite3.connect(DB,timeout=5)
            connection.row_factory=sqlite3.Row
            try:
                # WAL activation can briefly race during first worker startup.
                # Retry only this idempotent connection setup, never user writes.
                setup_deadline=time.monotonic()+5
                while True:
                    try:
                        connection.execute('PRAGMA journal_mode=WAL')
                        break
                    except sqlite3.OperationalError as error:
                        if 'locked' not in str(error).lower() or time.monotonic()>=setup_deadline:
                            raise
                        time.sleep(0.05)
                # Interrupt unexpectedly expensive reads/writes after 10 seconds.
                deadline=time.monotonic()+10
                connection.set_progress_handler(lambda: int(time.monotonic()>deadline),10000)
                with connection:
                    if check_tenant:
                        from .tenancy import check_binding
                        check_binding(connection)
                    yield connection
            finally:
                connection.close()
        except (sqlite3.Error,OSError) as error:
            raise StorageError('SQLite operation failed') from error

def initialize():
    dialect='postgresql' if postgres_enabled() else 'sqlite'
    with database(check_tenant=False) as db:
        if postgres_enabled():
            db.execute('SELECT pg_advisory_xact_lock(76674701)')
        else:
            # Serialize worker/retention startup before adopting a legacy schema.
            db.execute('BEGIN IMMEDIATE')
        db.execute('CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at DOUBLE PRECISION NOT NULL)')
        version=db.execute('SELECT COALESCE(MAX(version),0) AS version FROM schema_migrations').fetchone()[0]
        if version>SCHEMA_VERSION:
            raise StorageError('Database schema is newer than this application')
        for migration in range(version+1, SCHEMA_VERSION+1):
            filename = {1:'001_initial.sql',2:'002_accounts.sql',3:'003_studio.sql',4:'004_connections.sql',5:'005_access.sql',6:'006_tenancy.sql',7:'007_assurance.sql'}[migration]
            sql=(ROOT/'migrations'/dialect/filename).read_text(encoding='utf-8')
            for statement in sql.split(';'):
                if statement.strip():
                    if migration==7 and statement.strip().startswith('ALTER TABLE'):
                        parts=statement.split();table,column=parts[2],parts[5]
                        if postgres_enabled():
                            exists=db.execute('SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=? AND column_name=?',(table,column)).fetchone()
                        else:
                            exists=any(row['name']==column for row in db.execute('PRAGMA table_info('+table+')'))
                        if exists:continue
                    db.execute(statement)
            db.execute('INSERT INTO schema_migrations(version,applied_at) VALUES (?,?)',(migration,time.time()))
        from .tenancy import bind
        bind(db)

def prune():
    days=int(os.getenv('RETENTION_DAYS','7'))
    if not 1<=days<=365:
        raise ValueError('RETENTION_DAYS must be 1-365')
    cutoff=time.time()-days*86400
    # Commit between bounded batches to avoid a single giant delete transaction.
    for table in ('logs','spans','samples','events'):
        key='(trace_id,span_id)' if table=='spans' else 'id'
        projection='trace_id,span_id' if table=='spans' else 'id'
        while True:
            with database() as db:
                before=db.total_changes
                db.execute(f'DELETE FROM {table} WHERE {key} IN (SELECT {projection} FROM {table} WHERE time < ? LIMIT 5000)',(cutoff,))
                deleted=db.total_changes-before
            if deleted<5000:
                break
    return days
