import hashlib
import io
import json
import secrets
import unittest
import test_gateway
from montralog.accounts import create_account
from montralog import storage
import montralog.http as app

class AccountTests(unittest.TestCase):
    tearDown = test_gateway.GatewayTests.tearDown
    def setUp(self):
        test_gateway.GatewayTests.setUp(self)
        create_account('alice','Alice','a-secure-test-password')
        self.cookie=''
        self.csrf=''

    def request(self,path,method='GET',data=None,csrf=None,cookie=None):
        raw=json.dumps(data).encode() if data is not None else b''
        env={'PATH_INFO':path,'REQUEST_METHOD':method,'CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(raw)),
             'wsgi.input':io.BytesIO(raw),'HTTP_COOKIE':self.cookie if cookie is None else cookie,
             'HTTP_X_CSRF_TOKEN':self.csrf if csrf is None else csrf,'REMOTE_ADDR':'127.0.0.1'}
        result={}
        def start(status,headers):result.update(status=int(status.split()[0]),headers=dict(headers))
        result['body']=json.loads(b''.join(app.application(env,start)))
        return result

    def sign_in(self):
        result=self.request('/api/auth/login','POST',{'username':'alice','password':'a-secure-test-password'})
        self.assertEqual(result['status'],200)
        self.cookie=result['headers']['Set-Cookie'].split(';')[0]
        self.csrf=result['body']['csrf']
        return result

    def test_session_read_access_no_ingestion_and_logout(self):
        result=self.sign_in()
        self.assertIn('HttpOnly',result['headers']['Set-Cookie'])
        self.assertIn('SameSite=Strict',result['headers']['Set-Cookie'])
        self.assertEqual(self.request('/api/overview')['status'],200)
        self.assertEqual(self.request('/api/logs','POST',[])['status'],401)
        self.assertEqual(self.request('/api/account/logout','POST',{},csrf='wrong')['status'],403)
        self.assertEqual(self.request('/api/account/logout','POST',{})['status'],200)
        self.assertEqual(self.request('/api/overview')['status'],401)

    def test_profile_and_password_revokes_all_sessions(self):
        self.sign_in();old=self.cookie
        self.assertEqual(self.request('/api/account/profile','POST',{'name':'Alicia','email':'alice@example.test'})['status'],200)
        self.assertEqual(self.request('/api/account')['body']['user']['name'],'Alicia')
        self.assertEqual(self.request('/api/account/password','POST',{'current_password':'wrong','password':'replacement-password'})['status'],400)
        self.assertEqual(self.request('/api/account/password','POST',{'current_password':'a-secure-test-password','password':'replacement-password'})['status'],200)
        self.assertEqual(self.request('/api/account',cookie=old)['status'],401)
        self.assertEqual(self.request('/api/auth/login','POST',{'username':'alice','password':'replacement-password'})['status'],200)

    def test_dashboard_persistence_validation_and_ownership(self):
        self.sign_in()
        self.assertEqual(self.request('/api/saved-dashboards','POST',{'name':'CPU','definition':{'panels':['cpu'],'minutes':60}},csrf='')['status'],403)
        created=self.request('/api/saved-dashboards','POST',{'name':'CPU','definition':{'panels':['cpu'],'minutes':60}})
        self.assertEqual(created['status'],200)
        ident=created['body']['id']
        self.assertEqual(len(self.request('/api/saved-dashboards')['body']['items']),1)
        self.assertEqual(self.request('/api/saved-dashboards','POST',{'name':'Bad','definition':{'panels':['arbitrary_query']}})['status'],400)
        create_account('bob','Bob','another-test-password')
        result=self.request('/api/auth/login','POST',{'username':'bob','password':'another-test-password'})
        self.cookie=result['headers']['Set-Cookie'].split(';')[0];self.csrf=result['body']['csrf']
        self.assertEqual(self.request('/api/saved-dashboards')['body']['items'],[])
        self.request('/api/saved-dashboards/delete','POST',{'id':ident})
        self.sign_in()
        self.assertEqual(len(self.request('/api/saved-dashboards')['body']['items']),1)

    def test_rate_limit_and_expiry(self):
        for _ in range(10):
            self.assertEqual(self.request('/api/auth/login','POST',{'username':'alice','password':'wrong'})['status'],401)
        self.assertEqual(self.request('/api/auth/login','POST',{'username':'alice','password':'wrong'})['status'],429)
        with storage.database() as db:db.execute('DELETE FROM login_attempts')
        self.sign_in()
        with storage.database() as db:db.execute('UPDATE sessions SET expires_at=0')
        self.assertEqual(self.request('/api/account')['status'],401)

    def test_other_session_revocation_and_secure_cookie(self):
        from unittest.mock import patch
        with patch.dict('os.environ',{'MONTRALOG_COOKIE_SECURE':'true'}):
            result=self.sign_in()
        self.assertIn('; Secure',result['headers']['Set-Cookie'])
        other=self.cookie
        self.sign_in()
        self.assertEqual(len(self.request('/api/account/sessions')['body']['items']),2)
        self.request('/api/account/revoke','POST',{})
        self.assertEqual(self.request('/api/account',cookie=other)['status'],401)
        self.assertEqual(self.request('/api/account')['status'],200)
