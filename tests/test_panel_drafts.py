import json
import os
import unittest
from unittest.mock import patch
import test_accounts
from montralog.accounts import create_account,AccountError
from montralog import panel_drafts,investigations,model_providers,storage

VALID={'name':'Operations','panels':[{'title':'CPU','source':'metric','metric':'cpu','visual':'gauge'},{'title':'Errors','source':'logs','visual':'timeline'}]}
ENV={'MONTRALOG_AI_ENABLED':'true','MONTRALOG_AI_PROVIDER':'ollama','MONTRALOG_AI_LOCAL_HTTP':'true','MONTRALOG_AI_URL':'http://ollama:11434','MONTRALOG_AI_MODEL':'qwen3:4b'}

class PanelDraftTests(test_accounts.AccountTests):
    def setUp(self):
        super().setUp();create_account('admin','Administrator','panel-draft-password')
        auth=self.request('/api/auth/login','POST',{'username':'admin','password':'panel-draft-password'})
        self.cookie=auth['headers']['Set-Cookie'].split(';')[0];self.csrf=auth['body']['csrf']

    def test_queue_validate_review_without_saving_or_telemetry(self):
        with patch.dict(os.environ,ENV):
            before=self.request('/api/saved-dashboards')['body']['items']
            created=self.request('/api/control/panel-drafts','POST',{'action':'generate','prompt':'Create a CPU and error log dashboard'})
            self.assertEqual(created['status'],200);ident=created['body']['id']
            self.assertEqual(self.request('/api/control/investigations')['body']['items'],[])
            with patch.object(model_providers,'generate',return_value=(VALID,{})) as generate:
                self.assertTrue(investigations.process_one())
                payload=json.loads(generate.call_args.args[1]);self.assertEqual(set(payload),{'request','metric_catalog'})
                self.assertNotIn('evidence',payload)
            result=self.request('/api/control/panel-drafts','POST',{'action':'open','id':ident})['body']
            self.assertEqual(result['status'],'complete');self.assertEqual(len(result['draft']['definition']['panels']),2)
            self.assertEqual(self.request('/api/saved-dashboards')['body']['items'],before)
            self.sign_in();self.assertEqual(self.request('/api/control/panel-drafts')['status'],403)

    def test_csrf_egress_and_role_revocation(self):
        self.assertEqual(self.request('/api/control/panel-drafts','POST',{'action':'generate'},csrf='wrong')['status'],403)
        remote={**ENV,'MONTRALOG_AI_PROVIDER':'openai-compatible','MONTRALOG_AI_URL':'https://model.example.com/v1','MONTRALOG_AI_API_KEY':'private-fixture-key','MONTRALOG_AI_EGRESS':'false'}
        with patch.dict(os.environ,remote):
            self.assertEqual(self.request('/api/control/panel-drafts','POST',{'action':'generate','prompt':'Create a dashboard','confirm_egress':True})['status'],400)
        with patch.dict(os.environ,{**remote,'MONTRALOG_AI_EGRESS':'true'}):
            self.assertEqual(self.request('/api/control/panel-drafts','POST',{'action':'generate','prompt':'Create a dashboard'})['status'],400)
        with patch.dict(os.environ,ENV):
            ident=self.request('/api/control/panel-drafts','POST',{'action':'generate','prompt':'Create CPU panels'})['body']['id']
            with storage.database() as db:db.execute("UPDATE user_roles SET role='viewer' WHERE user_id=(SELECT id FROM users WHERE username='admin')")
            with patch.object(model_providers,'generate') as generate:
                investigations.process_one();generate.assert_not_called()
            with storage.database() as db:self.assertEqual(db.execute('SELECT status FROM investigation_runs WHERE id=?',(ident,)).fetchone()[0],'failed')

    def test_cross_user_job_open_is_not_found(self):
        with patch.dict(os.environ,ENV):ident=self.request('/api/control/panel-drafts','POST',{'action':'generate','prompt':'Create CPU panels'})['body']['id']
        create_account('otheradmin','Other admin','other-panel-password')
        with storage.database() as db:db.execute("INSERT INTO user_roles(user_id,role) SELECT id,'admin' FROM users WHERE username='otheradmin'")
        auth=self.request('/api/auth/login','POST',{'username':'otheradmin','password':'other-panel-password'})
        self.cookie=auth['headers']['Set-Cookie'].split(';')[0];self.csrf=auth['body']['csrf']
        self.assertEqual(self.request('/api/control/panel-drafts','POST',{'action':'open','id':ident})['status'],404)

class PanelDraftValidationTests(unittest.TestCase):
    def test_unknown_queries_urls_and_oversized_drafts_rejected(self):
        for result in [{'name':'Bad','panels':[{**VALID['panels'][0],'query':'up'}]}, {'name':'Bad','panels':[{**VALID['panels'][0],'datasource':'other'}]}, {'name':'Bad','panels':[{**VALID['panels'][0],'metric':'invented'}]}, {'name':'Bad','panels':VALID['panels']*4}]:
            with self.assertRaises((ValueError,AccountError)):panel_drafts.validated(result)
