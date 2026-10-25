import json
import os
import unittest
import sqlite3
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from cryptography.fernet import Fernet
import test_gateway
import test_functional_review
from montralog import connections, identity, notifications, secret_store, storage


class SecretStoreTests(unittest.TestCase):
    setUp = test_gateway.GatewayTests.setUp
    tearDown = test_gateway.GatewayTests.tearDown
    request = test_functional_review.FunctionalReviewTests.request
    login = test_functional_review.FunctionalReviewTests.login

    def test_roundtrip_wrong_key_missing_key_and_required_configuration(self):
        key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {'MONTRALOG_ENCRYPTION_KEY': key}):
            encoded = secret_store.seal('private-integration-credential')
            self.assertNotIn('private-integration-credential', encoded)
            self.assertEqual(secret_store.reveal(encoded), 'private-integration-credential')
            self.assertEqual(secret_store.reveal('legacy'), 'legacy')
        for candidate in ('', Fernet.generate_key().decode(), 'malformed'):
            with patch.dict(os.environ, {'MONTRALOG_ENCRYPTION_KEY': candidate}), self.assertRaises(storage.StorageError):
                secret_store.reveal(encoded)
        with patch.dict(os.environ, {'MONTRALOG_ENCRYPTION_KEY': '', 'MONTRALOG_ENCRYPTION_REQUIRED': 'true'}):
            with self.assertRaises(storage.StorageError): secret_store.seal('credential')

    def test_api_storage_is_encrypted_and_delivery_receives_plaintext_only_in_memory(self):
        self.login()
        key = Fernet.generate_key().decode()
        webhook = 'https://hooks.slack.com/services/TEST/CHANNEL/test-secret'
        with patch.dict(os.environ, {'MONTRALOG_ENCRYPTION_KEY': key}):
            with patch.object(connections, 'query', return_value={'available': True, 'data': {'result': []}}):
                created = self.request('/api/control/data-sources', 'POST', {'name': 'Metrics', 'url': 'https://127.0.0.1:9090', 'auth_type': 'bearer', 'secret': 'metrics-secret'})
            self.assertEqual(created['status'], 200)
            created = self.request('/api/control/channels', 'POST', {'name': 'Slack', 'webhook': webhook})
            self.assertEqual(created['status'], 200)
            channel = created['body']['id']
            config = {'provider': 'google', 'issuer': 'https://accounts.google.com', 'client_id': 'client', 'client_secret': 'oidc-secret', 'redirect_uri': 'http://localhost:8080/auth/oidc/callback/google', 'domain': 'company.example'}
            with patch.object(identity, 'metadata', return_value={}):
                self.assertEqual(self.request('/api/control/identity', 'POST', config)['status'], 200)
            with storage.database() as db:
                for table in ('data_sources', 'notification_channels'):
                    self.assertTrue(db.execute('SELECT secret FROM '+table).fetchone()[0].startswith(secret_store.PREFIX))
                stored = json.loads(db.execute('SELECT config FROM identity_providers').fetchone()[0])
                self.assertTrue(stored['client_secret'].startswith(secret_store.PREFIX))
            self.assertNotIn('oidc-secret', json.dumps(self.request('/api/control/identity')['body']))
            self.assertEqual(self.request('/api/control/channels', 'POST', {'action': 'test', 'id': channel})['status'], 200)
            with patch.object(notifications, 'send_slack') as sender:
                notifications.deliver()
                self.assertEqual(sender.call_args.args[0], webhook)
            self.assertEqual(secret_store.encrypt_existing(), 0)

    def test_migration_is_idempotent_and_rolls_back_on_wrong_key(self):
        self.login()
        with patch.dict(os.environ, {'MONTRALOG_ENCRYPTION_KEY': '', 'MONTRALOG_ENCRYPTION_REQUIRED': 'false'}):
            self.request('/api/control/channels', 'POST', {'name': 'Old', 'webhook': 'https://hooks.slack.com/services/OLD/TEST/secret'})
        with patch.dict(os.environ, {'MONTRALOG_ENCRYPTION_KEY': Fernet.generate_key().decode()}):
            self.assertEqual(secret_store.encrypt_existing(), 1)
            self.assertEqual(secret_store.encrypt_existing(), 0)
        with storage.database() as db:
            db.execute("INSERT INTO data_sources(id,name,url,auth_type,username,secret,is_default,last_checked,last_status,last_detail,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", ('legacy', 'Legacy', 'http://localhost', 'bearer', '', 'plaintext-before-rollback', 0, 0, '', '', 0))
        with patch.dict(os.environ, {'MONTRALOG_ENCRYPTION_KEY': Fernet.generate_key().decode()}):
            with self.assertRaises(storage.StorageError): secret_store.encrypt_existing()
        with storage.database() as db:
            self.assertEqual(db.execute("SELECT secret FROM data_sources WHERE id='legacy'").fetchone()[0], 'plaintext-before-rollback')

    def test_encrypted_backup_restore_wrong_key_and_lost_key_fail_closed(self):
        if storage.postgres_enabled():
            self.skipTest('SQLite backup API only; PostgreSQL native restore needs deployment acceptance')
        key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {'MONTRALOG_ENCRYPTION_KEY': key, 'MONTRALOG_ENCRYPTION_REQUIRED': 'true'}):
            # A fresh install has nothing to migrate; the same migration also
            # handles pre-existing plaintext records without changing telemetry.
            self.assertEqual(secret_store.encrypt_existing(), 0)
            with storage.database() as db:
                db.execute('INSERT INTO notification_channels VALUES (?,?,?,?,?,?)', ('restore-channel', 'Restore fixture', 'slack', 'legacy-webhook-fixture', 1, 0))
            self.assertEqual(secret_store.verify_existing(), {'encrypted':0,'plaintext':1})
            self.assertEqual(secret_store.encrypt_existing(), 1)
            self.assertEqual(secret_store.verify_existing(), {'encrypted':1,'plaintext':0})
            backup = Path(self.tmp.name) / 'encrypted-backup.db'
            with storage.database() as source, closing(sqlite3.connect(backup)) as target:
                source.backup(target)
            with patch.object(storage, 'DB', backup):
                storage.initialize()
                for candidate in ('', Fernet.generate_key().decode()):
                    with patch.dict(os.environ, {'MONTRALOG_ENCRYPTION_KEY': candidate}):
                        with self.assertRaises(storage.StorageError): secret_store.encrypt_existing()
                        with self.assertRaises(storage.StorageError): secret_store.verify_existing()
                with storage.database() as db:
                    stored = db.execute("SELECT secret FROM notification_channels WHERE id='restore-channel'").fetchone()[0]
                self.assertTrue(stored.startswith(secret_store.PREFIX))
                # Recovery uses the separately preserved original key. There is
                # intentionally no bypass capable of recovering a lost key.
                self.assertEqual(secret_store.reveal(stored), 'legacy-webhook-fixture')
                self.assertEqual(secret_store.encrypt_existing(), 0)


import test_identity
class EncryptedIdentityTests(test_identity.IdentityTests):
    def setUp(self):
        self.encryption = patch.dict(os.environ, {'MONTRALOG_ENCRYPTION_KEY': Fernet.generate_key().decode()})
        self.encryption.start()
        self.addCleanup(self.encryption.stop)
        super().setUp()
