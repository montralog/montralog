import hashlib
import io
import json
import os
from pathlib import Path
from contextlib import closing
import socket
import sqlite3
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from cryptography.fernet import Fernet
import test_gateway
from montralog import accounts,backup,ingestion,outbound,secret_store,security,storage,tenancy


class AssuranceTests(unittest.TestCase):
    setUp=test_gateway.GatewayTests.setUp
    tearDown=test_gateway.GatewayTests.tearDown
    call=test_gateway.GatewayTests.call
    write=test_gateway.GatewayTests.write

    def test_varying_usernames_is_limited_before_password_hashing(self):
        with patch.object(accounts,'password_matches',return_value=False) as verifier:
            statuses=[]
            for number in range(40):
                try:accounts.login({'username':'unknown-'+str(number),'password':'invalid-fixture'},{'REMOTE_ADDR':'192.0.2.1'})
                except accounts.AccountError as error:statuses.append(error.status)
        self.assertEqual(statuses.count(401),30);self.assertEqual(statuses.count(429),10)
        self.assertEqual(verifier.call_count,30)
        with storage.database() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM login_attempts').fetchone()[0],120)

    def test_concurrent_throttling_is_atomic(self):
        def attempt(number):
            try:accounts.login({'username':'attacker','password':'fixture'},{'REMOTE_ADDR':'192.0.2.2'})
            except accounts.AccountError as error:return error.status
        with patch.object(accounts,'password_matches',return_value=False) as verifier,ThreadPoolExecutor(max_workers=8) as workers:
            statuses=list(workers.map(attempt,range(20)))
        self.assertEqual(statuses.count(401),10);self.assertEqual(statuses.count(429),10)
        self.assertEqual(verifier.call_count,10)

    def test_translation_and_tunnel_destinations_cannot_reach_socket(self):
        for address in ('64:ff9b::a9fe:a9fe','64:ff9b:1::a9fe:a9fe','2002:a9fe:a9fe::','2001:0:4136:e378:8000:63bf:3fff:fdd2'):
            with self.subTest(address=address),patch.object(socket,'getaddrinfo',return_value=[(socket.AF_INET6,socket.SOCK_STREAM,6,'',(address,443))]):
                with self.assertRaises(outbound.DestinationError):outbound.destination('https://review.example')

    def test_silo_tokens_remain_bound_even_if_operator_copies_secret(self):
        key=security.machine_token('read','customer-a')
        with patch.dict(os.environ,{'MONTRALOG_TENANT_ID':'customer-b','MONTRALOG_SILO_STRICT':'true','MONTRALOG_READ_TOKEN':key}):
            self.assertFalse(security.token_matches('MONTRALOG_READ_TOKEN',key))
        for suffix in ('','predictable','x'*32):
            self.assertFalse(security.valid_machine_token('mtls1.customer-b.read.'+suffix,'read','customer-b'))

    def test_tenant_derived_cipher_cannot_decrypt_with_reused_master_key(self):
        key=Fernet.generate_key().decode()
        with patch.dict(os.environ,{'MONTRALOG_ENCRYPTION_KEY':key,'MONTRALOG_TENANT_ID':'customer-a'}):
            ciphertext=secret_store.seal('fixture-credential')
        with patch.dict(os.environ,{'MONTRALOG_ENCRYPTION_KEY':key,'MONTRALOG_TENANT_ID':'customer-b'}):
            with self.assertRaises(storage.StorageError):secret_store.reveal(ciphertext)

    def test_legacy_cipher_migrates_to_tenant_bound_format(self):
        key=Fernet.generate_key().decode()
        legacy='enc:v1:'+Fernet(key.encode()).encrypt(b'legacy-fixture').decode()
        with storage.database() as db:db.execute('INSERT INTO notification_channels VALUES (?,?,?,?,?,?)',('legacy','Legacy','slack',legacy,0,0))
        with patch.dict(os.environ,{'MONTRALOG_ENCRYPTION_KEY':key}):
            self.assertEqual(secret_store.verify_existing().get('legacy'),1)
            self.assertEqual(secret_store.encrypt_existing(),1)
            self.assertEqual(secret_store.encrypt_existing(),0)
            with storage.database() as db:stored=db.execute('SELECT secret FROM notification_channels').fetchone()[0]
            self.assertTrue(stored.startswith('enc:v2:'));self.assertEqual(secret_store.reveal(stored),'legacy-fixture')

    def test_backup_private_integrity_restore_and_wrong_silo_key(self):
        # Initialize a separate database with key binding from its first startup.
        key=Fernet.generate_key().decode()
        with patch.dict(os.environ,{'MONTRALOG_ENCRYPTION_KEY':key}),patch.object(storage,'DB',Path(self.tmp.name)/'bound.db'):
            storage.initialize();ingestion.ingest('logs',[{'service':'restore','message':'private fixture'}])
            path=Path(self.tmp.name)/'backup.db';backup.create(path)
            self.assertEqual(backup.verify(path)['tenant_id'],'default')
            if os.name=='posix':self.assertEqual(path.stat().st_mode&0o777,0o600)
            with self.assertRaises(FileExistsError):backup.create(path)
            restored=Path(self.tmp.name)/'restored.db';backup.restore(path,restored)
            with closing(sqlite3.connect(restored)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM logs').fetchone()[0],1)
            for changed in ({'MONTRALOG_TENANT_ID':'other'},{'MONTRALOG_ENCRYPTION_KEY':Fernet.generate_key().decode()}):
                with patch.dict(os.environ,changed),self.assertRaises(ValueError):backup.verify(path)
            with path.open('ab') as corrupt:corrupt.write(b'tampered')
            with self.assertRaises(ValueError):backup.verify(path)

    def test_atomic_idempotent_ingestion_replay_conflict_and_parallel_clients(self):
        items=[{'service':'payments','message':'once'}];receipt=('fixture-key',hashlib.sha256(json.dumps(items).encode()).hexdigest())
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(list(pool.map(lambda _:ingestion.ingest('logs',items,receipt),range(12))),[1]*12)
        self.assertEqual(self.call('/api/overview')[1]['totals']['logs'],1)
        with self.assertRaises(ingestion.IdempotencyConflict):ingestion.ingest('logs',items,('fixture-key','different-hash'))
        with storage.database() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM ingest_receipts').fetchone()[0],1)

    def test_invalid_payload_does_not_commit_idempotency_receipt(self):
        with self.assertRaises(ValueError):ingestion.ingest('logs',[{'service':'ok','message':'valid'},{'message':'invalid'}],('rollback','hash'))
        with storage.database() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM logs').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM ingest_receipts').fetchone()[0],0)

    def test_http_idempotency_replay_conflict_and_private_digest(self):
        key='synthetic-receipt-001'
        items=[{'service':'checkout','message':'password=low-entropy'}]
        args=('/api/logs','POST',items,'w'*40)
        self.assertEqual(self.call(*args,idempotency_key=key)[0]['status'],201)
        self.assertEqual(self.call(*args,idempotency_key=key)[0]['status'],201)
        self.assertEqual(self.call('/api/logs','POST',[{'service':'checkout','message':'changed'}],'w'*40,idempotency_key=key)[0]['status'],409)
        self.assertEqual(self.call('/api/overview')[1]['totals']['logs'],1)
        with storage.database() as db:stored=db.execute('SELECT body_hash FROM ingest_receipts').fetchone()[0]
        self.assertNotEqual(stored,hashlib.sha256(json.dumps(items).encode()).hexdigest())
