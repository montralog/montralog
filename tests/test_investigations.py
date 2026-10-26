import io
import json
import os
import unittest
from unittest.mock import patch
import test_accounts
from montralog import investigations,model_providers,storage
from montralog.accounts import create_account
from montralog.ingestion import ingest


class InvestigationTests(test_accounts.AccountTests):
    def setUp(self):
        super().setUp();create_account('admin','Administrator','investigation-fixture-password')
        self.request('/api/auth/login','POST',{})
        auth=self.request('/api/auth/login','POST',{'username':'admin','password':'investigation-fixture-password'})
        self.cookie=auth['headers']['Set-Cookie'].split(';')[0];self.csrf=auth['body']['csrf']
        ingest('logs',[{'service':'checkout','severity':'ERROR','message':'Database timeout password=hidden alice@example.com'}]*10)

    def test_admin_csrf_and_evidence_only_have_no_model_egress(self):
        with patch.object(model_providers,'generate') as generate:
            self.assertEqual(self.request('/api/control/investigations','POST',{},csrf='wrong')['status'],403)
            result=self.request('/api/control/investigations','POST',{'service':'checkout'})
            self.assertEqual(result['status'],200);self.assertEqual(result['body']['status'],'complete')
            report=result['body']['report'];self.assertEqual(len(report['evidence']['evidence']),1)
            self.assertEqual(report['evidence']['noise']['repeated_records'],9)
            self.assertNotIn('hidden',json.dumps(report));self.assertNotIn('alice@example.com',json.dumps(report))
            self.assertFalse(report['analysis']['causality_proven']);generate.assert_not_called()
        self.sign_in();self.assertEqual(self.request('/api/control/investigations')['status'],403)

    def test_background_model_has_citations_cache_and_no_implicit_remediation(self):
        config={'MONTRALOG_AI_ENABLED':'true','MONTRALOG_AI_PROVIDER':'ollama','MONTRALOG_AI_LOCAL_HTTP':'true','MONTRALOG_AI_URL':'http://ollama:11434','MONTRALOG_AI_MODEL':'qwen3:4b'}
        with patch.dict(os.environ,config):
            result=self.request('/api/control/investigations','POST',{'use_model':True})['body']
            self.assertEqual(result['status'],'queued')
            ref=result['report']['evidence']['evidence'][0]['id']
            generated={'summary':'Hypothesis only','hypotheses':[{'claim':'Possible backend issue','evidence_ids':[ref],'uncertainty':'No backend health samples','next_check':'Review existing metrics'}]}
            with patch.object(model_providers,'generate',return_value=(generated,{'input':20,'output':30})) as generate:
                self.assertTrue(investigations.process_one());self.assertFalse(investigations.process_one());self.assertEqual(generate.call_count,1)
            opened=self.request('/api/control/investigations','POST',{'action':'open','id':result['id']})['body']
            self.assertEqual(opened['status'],'complete');self.assertFalse(opened['report']['analysis']['causality_proven'])
            cached=self.request('/api/control/investigations','POST',{'use_model':True})['body'];self.assertTrue(cached['cache_hit'])
            self.assertEqual(cached['id'],result['id'])
            with storage.database() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM remediation_plans').fetchone()[0],0)

    def test_hosted_ollama_also_needs_egress_consent(self):
        with patch.dict(os.environ,{'MONTRALOG_AI_ENABLED':'true','MONTRALOG_AI_PROVIDER':'ollama','MONTRALOG_AI_URL':'https://hosted.example','MONTRALOG_AI_LOCAL_HTTP':'true','MONTRALOG_AI_EGRESS':'false'}),patch.object(model_providers,'generate') as generate:
            self.assertEqual(self.request('/api/control/investigations','POST',{'use_model':True,'confirm_egress':True})['status'],400);generate.assert_not_called()

    def test_hallucinated_citations_fail_closed_and_leave_attempt_audit(self):
        with patch.dict(os.environ,{'MONTRALOG_AI_ENABLED':'true','MONTRALOG_AI_PROVIDER':'ollama','MONTRALOG_AI_LOCAL_HTTP':'true','MONTRALOG_AI_URL':'http://ollama:11434'}):
            result=self.request('/api/control/investigations','POST',{'use_model':True})['body']
            with patch.object(model_providers,'generate',return_value=({'summary':'fake','hypotheses':[{'claim':'Proven cause','evidence_ids':['L:outside'],'uncertainty':'none','next_check':'anything'}]},{})):
                investigations.process_one()
            opened=self.request('/api/control/investigations','POST',{'action':'open','id':result['id']})['body']
            self.assertEqual(opened['status'],'failed');self.assertEqual(opened['report']['analysis']['hypotheses'],[])
            with storage.database() as db:self.assertTrue(db.execute("SELECT id FROM access_audit WHERE action='investigation-attempt'").fetchone())

    def test_budget_rejects_before_any_provider_call(self):
        with patch.dict(os.environ,{'MONTRALOG_AI_DAILY_REQUESTS':'1'}):
            investigations.reserve_budget(2000)
            with self.assertRaises(Exception):investigations.reserve_budget(2000)

    def test_runbook_approval_lifecycle_and_replay_protection(self):
        run=self.request('/api/control/investigations','POST',{})['body']
        plan=self.request('/api/control/runbooks','POST',{'run_id':run['id'],'source_id':'builtin'})['body']
        self.assertEqual(self.request('/api/control/runbooks','POST',{'action':'execute','id':plan['id']})['status'],409)
        self.assertEqual(self.request('/api/control/runbooks','POST',{'action':'approve','id':plan['id'],'confirmation':'wrong'})['status'],400)
        self.assertEqual(self.request('/api/control/runbooks','POST',{'action':'approve','id':plan['id'],'confirmation':plan['definition']['confirmation']})['status'],200)
        with patch('montralog.connections.query',return_value={'available':True}) as query:
            self.assertEqual(self.request('/api/control/runbooks','POST',{'action':'execute','id':plan['id']})['status'],200)
            self.assertEqual(self.request('/api/control/runbooks','POST',{'action':'execute','id':plan['id']})['status'],409)
            query.assert_called_once()
        self.assertEqual(self.request('/api/control/runbooks','POST',{'action':'approve','id':plan['id'],'confirmation':plan['definition']['confirmation']})['status'],409)
