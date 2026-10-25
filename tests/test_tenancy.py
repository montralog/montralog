import io
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch
import test_gateway
from montralog import accounts, http, storage, tenancy


class TenancyTests(unittest.TestCase):
    setUp = test_gateway.GatewayTests.setUp
    tearDown = test_gateway.GatewayTests.tearDown
    call = test_gateway.GatewayTests.call
    write = test_gateway.GatewayTests.write
    def test_database_binding_cannot_be_reassigned_or_bypassed_by_header(self):
        self.write('logs', [{'service': 'tenant-a', 'message': 'private fixture'}])
        with patch.dict(os.environ, {'MONTRALOG_TENANT_ID': 'customer-b'}):
            with self.assertRaises(storage.StorageError): storage.initialize()
            self.assertEqual(self.call('/api/overview')[0]['status'], 503)
        self.assertEqual(self.call('/api/overview')[1]['totals']['logs'], 1)

    def test_cross_customer_tokens_sessions_and_records_are_rejected(self):
        accounts.create_account('admin', 'A', 'fixture-password')
        token_cookie = accounts.login({'username': 'admin', 'password': 'fixture-password'}, {'REMOTE_ADDR': '127.0.0.1'})[1][1]
        self.write('logs', [{'service': 'tenant-a', 'message': 'private-a'}])
        original = storage.DB
        with patch.dict(os.environ, {'MONTRALOG_TENANT_ID': 'customer-b', 'MONTRALOG_READ_TOKEN': 'b'*40, 'MONTRALOG_INGEST_TOKEN': 'c'*40}):
            storage.DB = Path(self.tmp.name) / 'b.db'
            try:
                storage.initialize()
                self.assertEqual(self.call('/api/overview', token='r'*40)[0]['status'], 401)
                self.assertEqual(self.call('/api/logs', 'POST', [{'service':'intrusion','message':'x'}], token='w'*40)[0]['status'], 401)
                self.assertIsNone(accounts.session({'HTTP_COOKIE':token_cookie}))
                self.assertEqual(self.call('/api/overview', token='b'*40)[1]['totals']['logs'], 0)
                self.assertNotEqual(tenancy.cookie_name('montralog_session'), 'montralog_session')
                accounts.create_account('admin', 'B', 'different-fixture-password')
                with storage.database() as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM dashboards').fetchone()[0],0)
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM notification_outbox').fetchone()[0],0)
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM data_sources').fetchone()[0],0)
            finally: storage.DB = original
        self.assertEqual(self.call('/api/overview')[1]['totals']['logs'], 1)

    def test_explicit_tenant_mismatch_and_shared_mode_fail_closed(self):
        env={'PATH_INFO':'/api/overview','REQUEST_METHOD':'GET','HTTP_X_MONTRALOG_TENANT':'other','wsgi.input':io.BytesIO()}
        captured=[]
        result=b''.join(http.application(env,lambda status,headers:captured.append(status)))
        self.assertTrue(captured[0].startswith('403'))
        self.assertNotIn('totals',json.loads(result))
        with patch.dict(os.environ, {'MONTRALOG_TENANCY_MODE':'shared'}):
            with self.assertRaises(ValueError): storage.initialize()
