import json
from unittest.mock import patch
import test_accounts
from montralog import storage
from montralog.accounts import create_account
from montralog import notifications

class StudioTests(test_accounts.AccountTests):
    def setUp(self):
        super().setUp()
        create_account('admin','Administrator','admin123')

    def admin_login(self):
        result=self.request('/api/auth/login','POST',{'username':'admin','password':'admin123'})
        self.assertEqual(result['status'],200)
        self.assertEqual(result['body']['user']['role'],'admin')
        self.cookie=result['headers']['Set-Cookie'].split(';')[0];self.csrf=result['body']['csrf']

    def test_managed_tokens_roles_scope_expiry_and_revocation(self):
        self.sign_in()
        self.assertEqual(self.request('/api/control/tokens')['status'],403)
        self.admin_login()
        self.assertEqual(self.request('/api/control/tokens','POST',{'name':'x','scope':'read','days':1},csrf='wrong')['status'],403)
        result=self.request('/api/control/tokens','POST',{'name':'reader','scope':'read','days':1})
        raw=result['body']['token']
        from test_gateway import GatewayTests
        self.assertEqual(GatewayTests.call(self,'/api/overview',token=raw)[0]['status'],200)
        self.assertEqual(GatewayTests.call(self,'/api/logs','POST',[],token=raw)[0]['status'],401)
        listing=self.request('/api/control/tokens')['body']['items']
        self.assertNotIn(raw,json.dumps(listing))
        ident=listing[0]['id']
        self.request('/api/control/tokens','POST',{'action':'revoke','id':ident})
        self.assertEqual(GatewayTests.call(self,'/api/overview',token=raw)[0]['status'],401)
        ingest=self.request('/api/control/tokens','POST',{'name':'writer','scope':'ingest','days':1})['body']['token']
        self.assertEqual(GatewayTests.call(self,'/api/logs','POST',[{'service':'api','message':'managed token'}],token=ingest)[0]['status'],201)
        self.assertEqual(GatewayTests.call(self,'/api/overview',token=ingest)[0]['status'],401)
        with storage.database() as db:db.execute('UPDATE api_tokens SET expires_at=0')
        self.assertEqual(GatewayTests.call(self,'/api/logs','POST',[],token=ingest)[0]['status'],401)

    def test_custom_dashboard_edit_and_ownership(self):
        self.sign_in()
        definition={'minutes':15,'panels':[{'source':'logs','visual':'timeline','title':'Errors','severity':'ERROR'},
                                          {'source':'metric','metric':'cpu','visual':'stat'},
                                          {'source':'patterns','visual':'bar'}]}
        created=self.request('/api/saved-dashboards','POST',{'name':'Investigation','definition':definition})
        self.assertEqual(created['status'],200)
        ident=created['body']['id']
        self.assertEqual(self.request('/api/saved-dashboards','POST',{'id':ident,'name':'Updated','definition':definition})['status'],200)
        self.assertEqual(self.request('/api/saved-dashboards')['body']['items'][0]['name'],'Updated')
        definition['panels'][0]['visual']='unsupported'
        self.assertEqual(self.request('/api/saved-dashboards','POST',{'name':'Bad','definition':definition})['status'],400)

    def test_empty_dashboard_save_add_panels_and_owner_boundary(self):
        self.sign_in()
        created=self.request('/api/saved-dashboards','POST',{'name':'Empty canvas','definition':{'minutes':60,'panels':[]}})
        self.assertEqual(created['status'],200)
        ident=created['body']['id']
        self.assertEqual(self.request('/api/saved-dashboards')['body']['items'][0]['definition']['panels'],[])
        panel={'source':'logs','visual':'timeline','title':'Errors'}
        self.assertEqual(self.request('/api/saved-dashboards','POST',{'id':ident,'name':'Built canvas','definition':{'minutes':60,'panels':[panel]}},csrf='wrong')['status'],403)
        self.assertEqual(self.request('/api/saved-dashboards','POST',{'id':ident,'name':'Built canvas','definition':{'minutes':60,'panels':[panel]}})['status'],200)
        self.assertEqual(self.request('/api/saved-dashboards','POST',{'name':'Too many','definition':{'minutes':60,'panels':[panel]*25}})['status'],400)
        self.admin_login()
        self.assertEqual(self.request('/api/saved-dashboards')['body']['items'],[])
        self.assertEqual(self.request('/api/saved-dashboards','POST',{'id':ident,'name':'Not mine','definition':{'minutes':60,'panels':[]}})['status'],404)

    def test_channels_hide_secrets_validate_destination_and_retry(self):
        self.admin_login()
        self.assertEqual(self.request('/api/control/channels','POST',{'name':'bad','webhook':'http://127.0.0.1/secret'})['status'],400)
        url='https://hooks.slack.com/services/TEST/CHANNEL/secret'
        created=self.request('/api/control/channels','POST',{'name':'Test route','webhook':url})
        self.assertEqual(created['status'],200);ident=created['body']['id']
        self.assertNotIn(url,json.dumps(self.request('/api/control/channels')['body']))
        self.request('/api/control/channels','POST',{'action':'test','id':ident})
        with patch.object(notifications,'send_slack',side_effect=OSError('do not leak '+url)):notifications.deliver()
        history=self.request('/api/control/deliveries')['body']['items']
        self.assertEqual(history[0]['status'],'pending');self.assertNotIn(url,json.dumps(history))
        with storage.database() as db:db.execute('UPDATE notification_outbox SET next_attempt=0')
        with patch.object(notifications,'send_slack') as sender:
            notifications.deliver();self.assertEqual(sender.call_count,1)
        self.assertEqual(self.request('/api/control/deliveries')['body']['items'][0]['status'],'sent')

    def test_rule_transitions_are_deduplicated_and_missing_data_unknown(self):
        self.admin_login()
        rule={'name':'Memory high','definition':{'source':'metric','metric':'memory','threshold':80,'op':'gt','for_seconds':0,'channels':[]}}
        self.assertEqual(self.request('/api/control/rules','POST',rule)['status'],200)
        with patch.object(notifications,'evaluate',return_value=(90,'sample')):
            notifications.tick();notifications.tick()
        self.assertEqual(len(self.request('/api/control/inbox')['body']['items']),1)
        with patch.object(notifications,'evaluate',return_value=(None,'unavailable')):notifications.tick()
        self.assertEqual(self.request('/api/control/rules')['body']['items'][0]['state'],'unknown')
        self.assertEqual(len(self.request('/api/control/inbox')['body']['items']),1)

    def test_log_count_rule_uses_literal_filter(self):
        self.admin_login()
        from montralog.ingestion import ingest
        ingest('logs',[{'service':'api','severity':'ERROR','message':'timeout 100%'}])
        self.request('/api/control/rules','POST',{'name':'Error logs','definition':{'source':'logs','threshold':0,'op':'gt','for_seconds':0,'q':'100%','severity':'ERROR','channels':[]}})
        notifications.tick()
        self.assertEqual(self.request('/api/control/rules')['body']['items'][0]['state'],'firing')

    def test_managed_ingest_token_forwards_otlp_metrics(self):
        self.admin_login()
        raw=self.request('/api/control/tokens','POST',{'name':'metric writer','scope':'ingest','days':1})['body']['token']
        from test_gateway import GatewayTests
        with patch('montralog.forwarding.metrics',return_value={}) as forward:
            result=GatewayTests.call(self,'/v1/metrics','POST',{'resourceMetrics':[]},token=raw)
            self.assertEqual(result[0]['status'],200)
            self.assertEqual(forward.call_count,1)
