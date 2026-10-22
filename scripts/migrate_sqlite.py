"""Import a consistent legacy SQLite snapshot into an EMPTY PostgreSQL database.

The source snapshot is opened read-only and is never modified. Use operator-native
PostgreSQL backups and disable ingestion while running this one-time import.
"""
import argparse
import os
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from montralog.storage import database,initialize,postgres_enabled

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('snapshot',type=Path)
    args=parser.parse_args()
    if not postgres_enabled():
        parser.error('Set MONTRALOG_DATABASE_URL for the target PostgreSQL database')
    if not args.snapshot.is_file():
        parser.error('Source SQLite snapshot does not exist')
    initialize()
    source=sqlite3.connect(args.snapshot.resolve().as_uri()+'?mode=ro',uri=True)
    source.row_factory=sqlite3.Row
    tables=('logs','spans','samples','events')
    totals={}
    try:
        with database() as target:
            target.execute('SELECT pg_advisory_xact_lock(76674702)')
            # One all-or-nothing import; all target tables must be empty.
            for table in tables:
                target.execute(f'LOCK TABLE {table} IN EXCLUSIVE MODE')
                if target.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]:
                    raise RuntimeError('Target telemetry tables must be empty; aborting without importing')
            for table in tables:
                cursor=source.execute(f'SELECT * FROM {table}')
                columns=[x[0] for x in cursor.description]
                sql=f'INSERT INTO {table} ({",".join(columns)}) VALUES ({",".join("?" for _ in columns)})'
                count=0
                while rows:=cursor.fetchmany(500):
                    target.executemany(sql,[tuple(row) for row in rows])
                    count+=len(rows)
                totals[table]=count
                if 'id' in columns:
                    target.execute(f"SELECT setval(pg_get_serial_sequence('{table}','id'), COALESCE((SELECT MAX(id) FROM {table}),1), EXISTS(SELECT 1 FROM {table}))")
        print('Import committed:',totals)
    finally:
        source.close()

if __name__=='__main__':
    main()
