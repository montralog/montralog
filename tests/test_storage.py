import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from montralog import storage
from montralog.ingestion import ingest

class MigrationTests(unittest.TestCase):
    def test_parallel_startup_has_one_migration(self):
        root=Path(__file__).resolve().parents[1]/'work'
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as tmp,patch.dict(os.environ,{'MONTRALOG_DATABASE_URL':''}):
            with patch.object(storage,'DB',Path(tmp)/'parallel.db'):
                with ThreadPoolExecutor(max_workers=4) as pool:
                    list(pool.map(lambda _: storage.initialize(),range(8)))
                with storage.database() as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0],storage.SCHEMA_VERSION)

    def test_newer_schema_is_rejected(self):
        root=Path(__file__).resolve().parents[1]/'work'
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as tmp,patch.dict(os.environ,{'MONTRALOG_DATABASE_URL':''}):
            with patch.object(storage,'DB',Path(tmp)/'future.db'):
                storage.initialize()
                with storage.database() as db:
                    db.execute('INSERT INTO schema_migrations VALUES (?,?)',(999,time.time()))
                with self.assertRaises(storage.StorageError):
                    storage.initialize()
    def test_legacy_sqlite_migration_preserves_rows(self):
        root=Path(__file__).resolve().parents[1]/'work'
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as tmp,patch.dict(os.environ,{'MONTRALOG_DATABASE_URL':''}):
            with patch.object(storage,'DB',Path(tmp)/'old.db'):
                storage.initialize()
                ingest('logs',[{'service':'api','message':'keep me'}])
                with storage.database() as db:
                    db.execute('DROP TABLE schema_migrations')
                storage.initialize()
                storage.initialize()
                with storage.database() as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM logs').fetchone()[0],1)
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0],storage.SCHEMA_VERSION)

    def test_retention_removes_expired_spans(self):
        root=Path(__file__).resolve().parents[1]/'work'
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as tmp,patch.dict(os.environ,{'MONTRALOG_DATABASE_URL':'','RETENTION_DAYS':'7'}):
            with patch.object(storage,'DB',Path(tmp)/'spans.db'):
                storage.initialize()
                ingest('spans',[{'service':'api','trace_id':'ab'*16,'span_id':'cd'*8,'time':time.time()-9*86400},
                                {'service':'api','trace_id':'ab'*16,'span_id':'ef'*8}])
                storage.prune()
                with storage.database() as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM spans').fetchone()[0],1)
