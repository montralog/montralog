import unittest
import test_accounts
from montralog.accounts import create_account
from montralog.storage import database

class WorkspaceSettingsTests(unittest.TestCase):
    def setUp(self):
        test_accounts.AccountTests.setUp(self)
        with database() as db:
            db.execute("INSERT INTO user_roles(user_id,role) SELECT id,'admin' FROM users WHERE username='alice' ON CONFLICT(user_id) DO UPDATE SET role='admin'")
    tearDown=test_accounts.AccountTests.tearDown
    request=test_accounts.AccountTests.request
    sign_in=test_accounts.AccountTests.sign_in

    def test_admin_changes_persist_without_changing_deployment_identity(self):
        self.sign_in()
        with database() as db:
            original=dict(db.execute('SELECT * FROM deployment_identity WHERE id=1').fetchone())
        result=self.request('/api/control/workspace','POST',{'name':'Acme Engineering','description':'Production observability'})
        self.assertEqual(result['status'],200)
        self.assertEqual(self.request('/api/control/workspace')['body']['name'],'Acme Engineering')
        with database() as db:
            self.assertEqual(dict(db.execute('SELECT * FROM deployment_identity WHERE id=1').fetchone()),original)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM access_audit WHERE action='workspace.updated'").fetchone()[0],1)

    def test_authenticated_viewer_can_read_but_cannot_rename(self):
        self.assertEqual(self.request('/api/control/workspace')['status'],401)
        create_account('bob','Bob','viewer-fixture-password')
        login=self.request('/api/auth/login','POST',{'username':'bob','password':'viewer-fixture-password'})
        self.cookie=login['headers']['Set-Cookie'].split(';')[0];self.csrf=login['body']['csrf']
        self.assertEqual(self.request('/api/control/workspace')['status'],200)
        self.assertEqual(self.request('/api/control/workspace','POST',{'name':'Changed'})['status'],403)

    def test_csrf_and_display_field_validation(self):
        self.sign_in()
        self.assertEqual(self.request('/api/control/workspace','POST',{'name':'Acme'},csrf='wrong')['status'],403)
        for payload in [{'name':''},{'name':'x'*81},{'name':'Acme\nInjected'},{'name':'Acme','description':'x'*161},{'name':'Acme','tenant_id':'other'}]:
            self.assertEqual(self.request('/api/control/workspace','POST',payload)['status'],400)
        self.assertEqual(self.request('/api/control/workspace')['body']['name'],'Your organization')
