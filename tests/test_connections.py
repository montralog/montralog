import io
import json
import socket
import urllib.error
from unittest.mock import patch
import test_accounts
import test_studio
from montralog.accounts import create_account,AccountError
from montralog import connections,storage

class ConnectionTests(test_accounts.AccountTests):
    def setUp(self):
        super().setUp();create_account('admin','Administrator','admin123')
    admin_login=test_studio.StudioTests.admin_login

    def test_admin_save_default_masking_and_edit(self):
        self.sign_in()
        self.assertEqual(self.request('/api/control/data-sources')['status'],200)
        self.assertEqual(self.request('/api/control/data-sources','POST',{'name':'bad'})['status'],403)
        self.admin_login()
        source={'name':'Metrics','url':'http://127.0.0.1:9090','auth_type':'basic','username':'reader','secret':'private-password','is_default':True}
        with patch.object(connections,'query',return_value={'available':True,'data':{'result':[{}]}}):
            created=self.request('/api/control/data-sources','POST',source)
            self.assertEqual(created['status'],200)
            ident=created['body']['id']
            listed=self.request('/api/control/data-sources')['body']['items']
            self.assertNotIn('private-password',json.dumps(listed))
            self.assertEqual(connections.resolve()['id'],ident)
            source.update(id=ident,secret='',name='Renamed')
            self.assertEqual(self.request('/api/control/data-sources','POST',source)['status'],200)
            self.assertEqual(connections.resolve()['secret'],'private-password')

    def test_save_requires_success_and_csrf(self):
        self.admin_login();source={'name':'Offline','url':'http://127.0.0.1:9090','auth_type':'none'}
        self.assertEqual(self.request('/api/control/data-sources','POST',source,csrf='wrong')['status'],403)
        with patch.object(connections,'query',return_value={'available':False,'error':'Server unreachable'}):
            self.assertEqual(self.request('/api/control/data-sources','POST',source)['status'],400)
            source['action']='test'
            self.assertFalse(self.request('/api/control/data-sources','POST',source)['body']['ok'])
        self.assertEqual(len(self.request('/api/control/data-sources')['body']['items']),1)

    def test_metadata_addresses_and_embedded_credentials_blocked(self):
        for url in ('file:///etc/passwd','http://user:secret@localhost','http://169.254.169.254','http://0.0.0.0','http://224.0.0.1','http://metadata.google.internal','http://localhost/#x','http://localhost/?query=x'):
            with self.assertRaises(AccountError):connections.validate_url(url)

    def test_server_auth_headers_and_safe_errors(self):
        response=io.BytesIO(json.dumps({'status':'success','data':{'result':[]}}).encode())
        source={'url':'http://127.0.0.1:9090','auth_type':'bearer','secret':'do-not-expose','name':'Metrics'}
        with patch('urllib.request.OpenerDirector.open',return_value=response) as opened:
            self.assertTrue(connections.query(source,'query',{'query':'up'})['available'])
            request=opened.call_args.args[0]
            self.assertEqual(request.get_header('Authorization'),'Bearer do-not-expose')
            self.assertNotIn('do-not-expose',request.full_url)
        with patch('urllib.request.OpenerDirector.open',side_effect=OSError('secret do-not-expose')):
            self.assertNotIn('do-not-expose',json.dumps(connections.query(source,'query')))
        self.assertIsNone(connections.NoRedirect().redirect_request(None,None,302,'','', 'http://elsewhere/'))

    def test_explicit_source_and_deleted_panel_reference(self):
        self.admin_login()
        with patch.object(connections,'query',return_value={'available':True,'data':{'result':[]}}):
            ident=self.request('/api/control/data-sources','POST',{'name':'Panel source','url':'http://127.0.0.1:9090'})['body']['id']
        definition={'minutes':15,'panels':[{'source':'metric','metric':'cpu','visual':'stat','datasource':ident}]}
        self.assertEqual(self.request('/api/saved-dashboards','POST',{'name':'Pinned source','definition':definition})['status'],200)
        self.request('/api/control/data-sources','POST',{'action':'delete','id':ident})
        with self.assertRaises(AccountError):connections.resolve(ident)
