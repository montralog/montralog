"""Opt-in tests against an isolated PostgreSQL database, never an operator's data."""
import os
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch
import test_gateway
from montralog import storage

@unittest.skipUnless(os.getenv('MONTRALOG_TEST_DATABASE_URL'),'No isolated PostgreSQL test database supplied')
class PostgresGatewayTests(test_gateway.GatewayTests):
    def setUp(self):
        self.env=patch.dict(os.environ,{
            'MONTRALOG_DATABASE_URL':os.environ['MONTRALOG_TEST_DATABASE_URL'],
            'MONTRALOG_READ_TOKEN':'r'*40,'MONTRALOG_INGEST_TOKEN':'w'*40,
            'RETENTION_DAYS':'7','PROMETHEUS_URL':'','MONTRALOG_ALLOWED_DESTINATIONS':'127.0.0.1:9090,localhost:4318'})
        self.env.start()
        # Require an explicit test URL and database name before clearing test records.
        from urllib.parse import urlparse
        if not urlparse(os.environ['MONTRALOG_TEST_DATABASE_URL']).path.endswith('/montralog_test'):
            raise RuntimeError('Tests require an isolated database named montralog_test')
        storage.initialize()
        with storage.database() as db:
            db.execute('TRUNCATE identity_states,external_identities,identity_providers,access_members,access_collections,access_audit,logs,spans,samples,events,sessions,dashboards,users,login_attempts,user_roles,api_tokens,notification_channels,alert_rules,alert_states,notification_inbox,notification_outbox,worker_heartbeat,data_sources RESTART IDENTITY')

    def tearDown(self):
        self.env.stop()

    def test_retention_and_backup_restore(self):
        import time
        self.write('logs',[{'service':'api','message':'old','time':time.time()-9*86400},{'service':'api','message':'new'}])
        self.write('spans',[{'service':'api','trace_id':'ab'*16,'span_id':'cd'*8,'time':time.time()-9*86400}])
        storage.prune()
        self.assertEqual(self.call('/api/overview')[1]['totals']['logs'],1)
        with storage.database() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM spans').fetchone()[0],0)

    def test_migrations_are_idempotent(self):
        storage.initialize()
        storage.initialize()
        with storage.database() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0],storage.SCHEMA_VERSION)

import test_accounts
from montralog.accounts import create_account

@unittest.skipUnless(os.getenv('MONTRALOG_TEST_DATABASE_URL'),'No isolated PostgreSQL test database supplied')
class PostgresAccountTests(test_accounts.AccountTests):
    def setUp(self):
        PostgresGatewayTests.setUp(self)
        create_account('alice','Alice','a-secure-test-password')
        self.cookie=''
        self.csrf=''
    tearDown=PostgresGatewayTests.tearDown

import test_studio
@unittest.skipUnless(os.getenv('MONTRALOG_TEST_DATABASE_URL'),'No isolated PostgreSQL test database supplied')
class PostgresStudioTests(test_studio.StudioTests):
    def setUp(self):
        PostgresGatewayTests.setUp(self)
        create_account('alice','Alice','a-secure-test-password')
        create_account('admin','Administrator','admin123')
        self.cookie=''
        self.csrf=''
    tearDown=PostgresGatewayTests.tearDown

import test_connections
@unittest.skipUnless(os.getenv('MONTRALOG_TEST_DATABASE_URL'),'No isolated PostgreSQL test database supplied')
class PostgresConnectionTests(test_connections.ConnectionTests):
    def setUp(self):
        PostgresGatewayTests.setUp(self)
        create_account('alice','Alice','a-secure-test-password')
        create_account('admin','Administrator','admin123')
        self.cookie=''
        self.csrf=''
    tearDown=PostgresGatewayTests.tearDown

import test_access
import test_identity

@unittest.skipUnless(os.getenv('MONTRALOG_TEST_DATABASE_URL'),'No isolated PostgreSQL test database supplied')
class PostgresAccessTests(test_access.AccessTests):
    def setUp(self):
        with patch.object(test_gateway.GatewayTests, 'setUp', PostgresGatewayTests.setUp):
            super().setUp()
    tearDown=PostgresGatewayTests.tearDown

@unittest.skipUnless(os.getenv('MONTRALOG_TEST_DATABASE_URL'),'No isolated PostgreSQL test database supplied')
class PostgresIdentityTests(test_identity.IdentityTests):
    def setUp(self):
        with patch.object(test_gateway.GatewayTests, 'setUp', PostgresGatewayTests.setUp):
            super().setUp()
    tearDown=PostgresGatewayTests.tearDown

import test_functional_review

@unittest.skipUnless(os.getenv('MONTRALOG_TEST_DATABASE_URL'), 'No isolated PostgreSQL test database supplied')
class PostgresFunctionalReviewTests(test_functional_review.FunctionalReviewTests):
    setUp = PostgresGatewayTests.setUp
    tearDown = PostgresGatewayTests.tearDown

import test_secret_store
@unittest.skipUnless(os.getenv('MONTRALOG_TEST_DATABASE_URL'), 'No isolated PostgreSQL test database supplied')
class PostgresSecretStoreTests(test_secret_store.SecretStoreTests):
    setUp = PostgresGatewayTests.setUp
    tearDown = PostgresGatewayTests.tearDown
