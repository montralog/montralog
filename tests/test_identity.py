import copy
import json
import time
import unittest
from unittest.mock import patch
import test_accounts
import test_gateway
from montralog import identity
from montralog.accounts import AccountError, create_account
from montralog.storage import database
from joserfc import jwt
from joserfc.jwk import RSAKey


class IdentityTests(unittest.TestCase):
    request = test_accounts.AccountTests.request
    tearDown = test_gateway.GatewayTests.tearDown

    def setUp(self):
        test_gateway.GatewayTests.setUp(self)
        create_account('admin', 'Administrator', 'test-admin-password')
        self.cookie = self.csrf = ''
        r = self.request('/api/auth/login', 'POST', {'username': 'admin', 'password': 'test-admin-password'})
        self.cookie = r['headers']['Set-Cookie'].split(';')[0]; self.csrf = r['body']['csrf']
        self.key = RSAKey.generate_key(2048, parameters={'kid': 'test-key'})
        self.config = {'provider': 'google', 'issuer': 'https://accounts.google.com', 'client_id': 'client-test', 'client_secret': 'secret-test', 'redirect_uri': 'http://localhost:8080/auth/oidc/callback/google', 'domain': 'company.example'}
        self.claims = dict(iss=self.config['issuer'], aud='client-test', sub='subject-one', exp=int(time.time())+600, iat=int(time.time()), nonce='expected-nonce', hd='company.example', email_verified=True)

    def encoded(self, claims):
        return jwt.encode({'alg': 'RS256', 'kid': 'test-key'}, claims, self.key)

    def verify(self, claims, config=None):
        return identity.verify(self.encoded(claims), {'keys': [self.key.as_dict()]}, config or self.config, 'expected-nonce')

    def test_signature_and_claim_rejection(self):
        self.assertEqual(self.verify(self.claims)['sub'], 'subject-one')
        for field, value in [('nonce', 'wrong'), ('iss', 'https://attacker.example'), ('aud', 'other-client'), ('exp', 1), ('iat', int(time.time())+600), ('hd', 'other.example'), ('email_verified', False), ('azp', 'other-client'), ('sub', '')]:
            with self.subTest(field=field):
                c = self.claims | {field: value}
                with self.assertRaises(AccountError): self.verify(c)
        for field in ('nonce', 'exp', 'iat', 'sub'):
            c = self.claims.copy(); del c[field]
            with self.assertRaises(AccountError): self.verify(c)
        wrong_key = RSAKey.generate_key(2048, parameters={'kid': 'test-key'})
        token = jwt.encode({'alg': 'RS256', 'kid': 'test-key'}, self.claims, wrong_key)
        with self.assertRaises(AccountError): identity.verify(token, {'keys': [self.key.as_dict()]}, self.config, 'expected-nonce')

    def test_all_provider_profiles(self):
        for provider, issuer in [('microsoft', 'https://login.microsoftonline.com/12345678-1234-1234-1234-123456789abc/v2.0'), ('google', 'https://accounts.google.com'), ('okta', 'https://company.okta.com/oauth2/default')]:
            config = self.config | {'provider': provider, 'issuer': issuer}
            self.assertEqual(self.verify(self.claims | {'iss': issuer}, config)['sub'], 'subject-one')
            identity.endpoint(issuer, provider)
        for bad in ('http://accounts.google.com', 'https://accounts.google.com.attacker.example', 'https://127.0.0.1', 'https://accounts.google.com@attacker.example'):
            with self.assertRaises(AccountError): identity.endpoint(bad, 'google')

    def test_settings_secrets_and_permissions(self):
        metadata = {'issuer': self.config['issuer'], 'authorization_endpoint': 'https://accounts.google.com/o/oauth2/v2/auth', 'token_endpoint': 'https://oauth2.googleapis.com/token', 'jwks_uri': 'https://www.googleapis.com/oauth2/v3/certs'}
        with patch.object(identity, 'request_json', return_value=metadata):
            self.assertEqual(self.request('/api/control/identity', 'POST', self.config)['status'], 200)
        result = self.request('/api/control/identity')['body']
        self.assertNotIn('secret-test', json.dumps(result))
        self.assertTrue(result['items'][0]['has_secret'])
        self.assertEqual(self.request('/api/control/identity', 'POST', self.config, csrf='wrong')['status'], 403)
        self.assertEqual(self.request('/api/control/identity', cookie='')['status'], 403)
        self.assertEqual(len(self.request('/api/auth/providers', cookie='')['body']['items']), 1)
        self.assertEqual(self.request('/api/control/identity', 'POST', {'provider': 'google', 'action': 'disable'})['status'], 200)
        self.assertEqual(self.request('/api/auth/providers')['body']['items'], [])

    def test_callback_requires_binding_and_rejects_replay(self):
        with database() as db:
            db.execute('INSERT INTO identity_providers(provider,config) VALUES (?,?)', ('google', json.dumps(self.config)))
            db.execute('INSERT INTO identity_states(state_hash,provider,binding_hash,nonce,verifier,source,expires_at) VALUES (?,?,?,?,?,?,?)', (identity.digest('state'), 'google', identity.digest('binding'), 'expected-nonce', 'verifier', 'source', time.time()+600))
        with self.assertRaises(AccountError): identity.flow('/auth/oidc/callback/google', {'state': 'state', 'code': 'code'}, {})
        # A failed/declined exchange consumes the valid state, preventing reuse.
        env = {'HTTP_COOKIE': 'montralog_oidc=binding'}
        with self.assertRaises(AccountError): identity.flow('/auth/oidc/callback/google', {'state': 'state', 'error': 'access_denied'}, env)
        with self.assertRaises(AccountError): identity.flow('/auth/oidc/callback/google', {'state': 'state', 'code': 'code'}, env)

    def test_complete_exchange_creates_viewer_without_email_linking(self):
        meta = {'issuer': self.config['issuer'], 'authorization_endpoint': 'https://accounts.google.com/o/oauth2/v2/auth', 'token_endpoint': 'https://oauth2.googleapis.com/token', 'jwks_uri': 'https://www.googleapis.com/oauth2/v3/certs'}
        claims = self.claims | {'name': 'Company person', 'email': 'admin@example.test', 'groups': ['admin']}
        with database() as db:
            db.execute('INSERT INTO identity_providers(provider,config) VALUES (?,?)', ('google', json.dumps(self.config)))
            db.execute('INSERT INTO identity_states(state_hash,provider,binding_hash,nonce,verifier,source,expires_at) VALUES (?,?,?,?,?,?,?)', (identity.digest('state'), 'google', identity.digest('binding'), 'expected-nonce', 'verifier', 'source', time.time()+600))
        def provider_request(url, provider, form=None):
            if form:
                self.assertEqual(form['code_verifier'], 'verifier')
                return {'id_token': self.encoded(claims)}
            if url.endswith('/certs'): return {'keys': [self.key.as_dict()]}
            return meta
        with patch.object(identity, 'request_json', side_effect=provider_request):
            location, headers = identity.flow('/auth/oidc/callback/google', {'state': 'state', 'code': 'code'}, {'HTTP_COOKIE': 'montralog_oidc=binding'})
        self.assertEqual(location, '/')
        cookie = next(v for k, v in headers if v.startswith('montralog_session=')).split(';')[0]
        account = self.request('/api/account', cookie=cookie)['body']['user']
        self.assertEqual(account['role'], 'viewer')
        self.assertNotEqual(account['username'], 'admin')
        self.assertEqual(self.request('/api/control/access', cookie=cookie)['status'], 403)

    def test_start_binds_browser_and_limits_requests_before_network(self):
        from urllib.parse import urlsplit, parse_qs
        meta = {'issuer': self.config['issuer'], 'authorization_endpoint': 'https://accounts.google.com/o/oauth2/v2/auth', 'token_endpoint': 'https://oauth2.googleapis.com/token', 'jwks_uri': 'https://www.googleapis.com/oauth2/v3/certs'}
        with database() as db:
            db.execute('INSERT INTO identity_providers(provider,config) VALUES (?,?)', ('google', json.dumps(self.config)))
        with patch.object(identity, 'metadata', return_value=meta) as network:
            for _ in range(20):
                location, headers = identity.flow('/auth/oidc/start/google', {}, {'REMOTE_ADDR': '127.0.0.1'})
            with self.assertRaises(AccountError): identity.flow('/auth/oidc/start/google', {}, {'REMOTE_ADDR': '127.0.0.1'})
            self.assertEqual(network.call_count, 20)
        query = parse_qs(urlsplit(location).query)
        self.assertEqual(query['code_challenge_method'], ['S256'])
        self.assertTrue(query['nonce'][0])
        self.assertIn('SameSite=Lax', headers[0][1])
        self.assertIn('HttpOnly', headers[0][1])


if __name__ == '__main__': unittest.main()
