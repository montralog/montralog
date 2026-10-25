"""Executable regressions and workflow checks from the functional review."""
import io
import json
import unittest
from unittest.mock import patch
import test_gateway
import test_accounts
from montralog import connections, notifications, storage
from montralog.accounts import create_account


class FunctionalReviewTests(unittest.TestCase):
    setUp = test_gateway.GatewayTests.setUp
    tearDown = test_gateway.GatewayTests.tearDown
    call = test_gateway.GatewayTests.call
    write = test_gateway.GatewayTests.write
    request = test_accounts.AccountTests.request

    def login(self, username='admin'):
        create_account(username, username.title(), 'functional-review-password')
        self.cookie = self.csrf = ''
        result = self.request('/api/auth/login', 'POST', {
            'username': username, 'password': 'functional-review-password'})
        self.assertEqual(result['status'], 200)
        self.cookie = result['headers']['Set-Cookie'].split(';')[0]
        self.csrf = result['body']['csrf']

    def test_nonfinite_backend_json_returns_unavailable_instead_of_crashing(self):
        source = {'url': 'http://127.0.0.1:9090', 'auth_type': 'none'}
        for value in ('NaN', 'Infinity', '-Infinity', '1e400'):
            raw = ('{"status":"success","data":{"result":[],"bad":' + value + '}}').encode()
            with self.subTest(value=value), patch('montralog.connections.resolve', return_value=source), patch(
                    'montralog.connections.open_request', return_value=io.BytesIO(raw)):
                status, body = self.call('/api/metrics', query='panel=cpu')
                self.assertEqual(status['status'], 200)
                self.assertFalse(body['available'])
                self.assertIn('error', body)

    def test_prometheus_string_nan_is_preserved_as_a_valid_sample(self):
        source = {'url': 'http://127.0.0.1:9090', 'auth_type': 'none'}
        payload = {'status': 'success', 'data': {'result': [{'metric': {}, 'value': [123, 'NaN']}]}}
        with patch('montralog.connections.open_request', return_value=io.BytesIO(json.dumps(payload).encode())):
            result = connections.query(source, 'query')
        self.assertTrue(result['available'])
        self.assertEqual(result['data']['result'][0]['value'][1], 'NaN')

    def test_invalid_alert_numbers_do_not_create_rules(self):
        self.login()
        for field, value in [('threshold', True), ('for_seconds', True), ('for_seconds', 1.5),
                             ('for_seconds', -0.5), ('threshold', float('inf'))]:
            with self.subTest(field=field, value=value):
                definition = {'source': 'logs', 'threshold': 1, 'for_seconds': 0, field: value}
                result = self.request('/api/control/rules', 'POST', {'name': 'Invalid', 'definition': definition})
                self.assertEqual(result['status'], 400)
        self.assertEqual(self.request('/api/control/rules')['body']['items'], [])

    def test_log_alert_pending_firing_and_resolution_with_real_counts(self):
        self.login()
        self.write('logs', [{'service': 'checkout', 'environment': 'prod', 'severity': 'ERROR', 'message': 'timeout 100%'},
                            {'service': 'checkout', 'environment': 'test', 'severity': 'ERROR', 'message': 'timeout 100%'},
                            {'service': 'other', 'environment': 'prod', 'severity': 'ERROR', 'message': 'timeout 100%'}])
        result = self.request('/api/control/rules', 'POST', {'name': 'Checkout errors', 'definition': {
            'source': 'logs', 'service': 'checkout', 'environment': 'prod', 'q': '100%',
            'severity': 'ERROR', 'op': 'gt', 'threshold': 0, 'for_seconds': 30, 'channels': []}})
        self.assertEqual(result['status'], 200)
        import time
        now = time.time()
        for seconds, expected, count in [(0, 'pending', 0), (29, 'pending', 0),
                                         (30, 'firing', 1), (31, 'firing', 1)]:
            with patch('montralog.notifications.time.time', return_value=now + seconds):
                notifications.tick()
            rule = self.request('/api/control/rules')['body']['items'][0]
            self.assertEqual(rule['state'], expected)
            self.assertEqual(rule['value'], 1)
            self.assertEqual(len(self.request('/api/control/inbox')['body']['items']), count)
        with storage.database() as db:
            db.execute('DELETE FROM logs')
        notifications.tick()
        notifications.tick()
        self.assertEqual(self.request('/api/control/rules')['body']['items'][0]['state'], 'normal')
        states = [item['state'] for item in self.request('/api/control/inbox')['body']['items']]
        self.assertCountEqual(states, ['firing', 'normal'])

    def test_dashboard_update_cannot_overwrite_another_users_definition(self):
        self.login()
        definition = {'minutes': 15, 'panels': [{'source': 'logs', 'visual': 'timeline'}]}
        created = self.request('/api/saved-dashboards', 'POST', {'name': 'Private', 'definition': definition})
        self.assertEqual(created['status'], 200)
        ident = created['body']['id']
        owner_cookie, owner_csrf = self.cookie, self.csrf
        self.login('bob')
        result = self.request('/api/saved-dashboards', 'POST', {'id': ident, 'name': 'Overwritten', 'definition': definition})
        self.assertEqual(result['status'], 404)
        self.assertEqual(self.request('/api/saved-dashboards')['body']['items'], [])
        self.cookie, self.csrf = owner_cookie, owner_csrf
        dashboard = self.request('/api/saved-dashboards')['body']['items'][0]
        self.assertEqual(dashboard['name'], 'Private')
        self.assertEqual(dashboard['definition']['panels'][0]['visual'], 'timeline')
