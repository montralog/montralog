import unittest
from test_accounts import AccountTests
from montralog.accounts import create_account
from montralog.storage import database


class AccessTests(AccountTests):
    def setUp(self):
        super().setUp()
        create_account('admin', 'Administrator', 'test-admin-password')

    def admin_login(self):
        r = self.request('/api/auth/login', 'POST', {'username': 'admin', 'password': 'test-admin-password'})
        self.cookie = r['headers']['Set-Cookie'].split(';')[0]
        self.csrf = r['body']['csrf']

    def change(self, **body):
        return self.request('/api/control/access', 'POST', body)

    def test_membership_audit_and_validation(self):
        self.admin_login()
        self.assertEqual(self.change(action='create', kind='team', name='Platform')['status'], 200)
        self.assertEqual(self.change(action='create', kind='team', name='Platform')['status'], 400)
        data = self.request('/api/control/access')['body']
        team = data['collections'][0]['id']
        alice = next(u['id'] for u in data['users'] if u['username'] == 'alice')
        self.assertEqual(self.change(action='member-add', id=team, user_id=alice)['status'], 200)
        self.assertEqual(self.change(action='member-add', id=team, user_id=alice)['status'], 200)
        self.assertEqual(len(self.request('/api/control/access')['body']['members']), 1)
        self.assertEqual(self.change(action='delete', id=team)['status'], 400)
        self.assertEqual(self.change(action='member-remove', id=team, user_id=alice)['status'], 200)
        self.assertEqual(self.change(action='delete', id=team)['status'], 200)
        self.assertGreaterEqual(len(self.request('/api/control/access')['body']['audit']), 4)

    def test_authorization_and_last_admin(self):
        self.assertEqual(self.request('/api/control/access')['status'], 403)
        self.sign_in()
        self.assertEqual(self.change(action='create', kind='group', name='Ops')['status'], 403)
        self.admin_login()
        self.assertEqual(self.request('/api/control/access', 'POST', {'action': 'create', 'kind': 'group', 'name': 'Ops'}, csrf='bad')['status'], 403)
        users = self.request('/api/control/access')['body']['users']
        admin = next(u['id'] for u in users if u['username'] == 'admin')
        alice = next(u['id'] for u in users if u['username'] == 'alice')
        self.assertEqual(self.change(action='role', id=admin, role='viewer')['status'], 400)
        self.assertEqual(self.change(action='role', id=alice, role='owner')['status'], 400)
        self.assertEqual(self.change(action='role', id=alice, role='admin')['status'], 200)
        self.assertEqual(self.change(action='role', id=admin, role='viewer')['status'], 200)
        self.assertEqual(self.request('/api/control/access')['status'], 403)

    def test_sensitive_fields_never_returned(self):
        self.admin_login()
        result = str(self.request('/api/control/access')['body'])
        self.assertNotIn('password_hash', result)
        self.assertNotIn('csrf', result)


if __name__ == '__main__':
    unittest.main()
