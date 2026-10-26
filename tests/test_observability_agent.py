import json
import os
import unittest
from unittest.mock import patch
import test_investigations
from montralog import investigations,observability_agent,model_providers,connections,storage

class AgentTests(test_investigations.InvestigationTests):
    def queue_agent(self,**extra):
        response=self.request('/api/control/investigations','POST',{'use_model':True,'agentic':True,'service':'checkout','question':'Why are requests timing out?','metric':'cpu',**extra})
        self.assertEqual(response['status'],200,response['body'])
        return response['body']

    def final(self,run):
        record=run['report']['evidence']['evidence'][0]
        return {'summary':'A tentative correlation, not proven causality.','hypotheses':[{'claim':'Investigate the observed timeout','evidence_ids':[record['id']],'evidence_quotes':[{'id':record['id'],'quote':record['message'][:30]}],'uncertainty':'No direct database health evidence','next_check':'Compare database health with the captured time window.'}],'missing_evidence':['Database health and a verified recovery signal']}

    def local(self):
        return patch.dict(os.environ,{'MONTRALOG_AI_ENABLED':'true','MONTRALOG_AI_PROVIDER':'ollama','MONTRALOG_AI_MODEL':'qwen3:4b','MONTRALOG_AI_LOCAL_HTTP':'true','MONTRALOG_AI_URL':'http://ollama:11434'})

    def test_agent_reads_selected_source_follows_tool_and_validates_quotes(self):
        with self.local():
            run=self.queue_agent(source_id='builtin')
            metric={'available':True,'data':{'result':[{'metric':{'instance':'fixture','password':'never-send'},'value':[123,'96.5'],'values':[[120,'90'],[123,'96.5']]}]}}
            replies=[({'tool_request':{'tool':'metric_trend','metric':'memory'}},{'input':10}), (self.final(run),{'input':10})]
            with patch.object(connections,'query',return_value=metric) as query,patch.object(model_providers,'generate',side_effect=replies) as model:
                self.assertTrue(investigations.process_one());self.assertEqual(model.call_count,2)
                self.assertEqual(query.call_args_list[0].args[1],'query');self.assertEqual(query.call_args_list[1].args[1],'query_range')
                self.assertEqual(query.call_args_list[0].args[2]['time'],run['report']['evidence']['scope']['end'])
                self.assertEqual(query.call_args_list[1].args[2]['end'],run['report']['evidence']['scope']['end'])
                self.assertNotIn('never-send',model.call_args.args[1])
            opened=self.request('/api/control/investigations','POST',{'action':'open','id':run['id']})['body']
            self.assertEqual(opened['status'],'complete');self.assertEqual(len(opened['report']['tool_trace']),2)
            self.assertFalse(opened['report']['analysis']['causality_proven'])
            self.assertNotIn('source_fingerprint',json.dumps(opened['report']))

    def test_unapproved_tool_cannot_execute_or_query(self):
        with self.local():
            run=self.queue_agent()
            with patch.object(connections,'query',return_value={'available':False}) as query,patch.object(model_providers,'generate',return_value=({'tool_request':{'tool':'shell','metric':'cpu'}},{})):
                investigations.process_one();self.assertEqual(query.call_count,1)
            opened=self.request('/api/control/investigations','POST',{'action':'open','id':run['id']})['body']
            self.assertEqual(opened['status'],'failed');self.assertEqual(opened['report']['analysis']['hypotheses'],[])

    def test_revocation_during_agent_stops_followup_reads(self):
        def revoke(*args,**kwargs):
            with storage.database() as db:db.execute("UPDATE user_roles SET role='viewer' WHERE user_id=(SELECT id FROM users WHERE username='admin')")
            return {'tool_request':{'tool':'metric_trend','metric':'memory'}},{}
        with self.local():
            run=self.queue_agent()
            with patch.object(connections,'query',return_value={'available':False}) as query,patch.object(model_providers,'generate',side_effect=revoke) as model:
                investigations.process_one();self.assertEqual(model.call_count,1);self.assertEqual(query.call_count,1)
            with storage.database() as db:self.assertEqual(db.execute('SELECT status FROM investigation_runs WHERE id=?',(run['id'],)).fetchone()[0],'failed')

    def test_invented_quotes_fail_closed(self):
        with self.local():
            run=self.queue_agent();result=self.final(run);result['hypotheses'][0]['evidence_quotes'][0]['quote']='A fabricated excerpt never observed'
            with patch.object(connections,'query',return_value={'available':False}),patch.object(model_providers,'generate',return_value=(result,{})):
                investigations.process_one()
            opened=self.request('/api/control/investigations','POST',{'action':'open','id':run['id']})['body'];self.assertEqual(opened['status'],'failed')

    def test_format_correction_stays_inside_reserved_call_limit(self):
        with self.local():
            run=self.queue_agent();invalid=self.final(run);invalid['hypotheses'][0].pop('evidence_quotes')
            with patch.object(connections,'query',return_value={'available':False}),patch.object(model_providers,'generate',side_effect=[(invalid,{}),(self.final(run),{})]) as model:
                investigations.process_one();self.assertEqual(model.call_count,2)
            opened=self.request('/api/control/investigations','POST',{'action':'open','id':run['id']})['body']
            self.assertEqual(opened['status'],'complete')
            self.assertTrue(any(t['tool']=='analysis-format-correction' for t in opened['report']['tool_trace']))

    def test_three_call_limit_and_no_fourth_provider_request(self):
        with self.local():
            self.queue_agent()
            replies=[({'tool_request':{'tool':'metric_trend','metric':metric}},{}) for metric in ('cpu','memory','pods')]
            with patch.object(connections,'query',return_value={'available':False}) as query,patch.object(model_providers,'generate',side_effect=replies) as model:
                investigations.process_one();self.assertEqual(model.call_count,3);self.assertEqual(query.call_count,3)

    def test_alert_condition_is_redacted_before_model_context(self):
        rule=self.request('/api/control/rules','POST',{'name':'Sensitive labels','definition':{'source':'logs','service':'password=hidden alice@example.com','threshold':1,'for_seconds':0}})
        self.assertEqual(rule['status'],200)
        result=self.request('/api/control/investigations','POST',{'agentic':True,'alert_id':rule['body']['id']})
        self.assertEqual(result['status'],200,result['body'])
        context=json.dumps(result['body']['report']['context'])
        self.assertNotIn('hidden',context);self.assertNotIn('alice@example.com',context)

    def test_changed_source_fails_before_model_or_metric_read(self):
        with self.local():
            self.queue_agent()
            with patch.object(connections,'resolve',return_value={'id':'builtin','url':'http://different.invalid'}),patch.object(connections,'query') as query,patch.object(model_providers,'generate') as model:
                investigations.process_one();query.assert_not_called();model.assert_not_called()

    def test_alert_runbook_and_authoritative_scope_are_captured(self):
        rule=self.request('/api/control/rules','POST',{'name':'Checkout incident','definition':{'source':'logs','service':'checkout','environment':'production','threshold':1,'for_seconds':0,'runbook':{'summary':'Check dependencies','checks':['Inspect database health'],'success_criteria':'Errors cease'}}})
        self.assertEqual(rule['status'],200,rule['body'])
        result=self.request('/api/control/investigations','POST',{'agentic':True,'alert_id':rule['body']['id'],'service':'unrelated'})['body']
        self.assertEqual(result['report']['evidence']['scope']['service'],'checkout')
        self.assertEqual(result['report']['context']['alert']['runbook']['checks'],['Inspect database health'])

class AbstentionTests(unittest.TestCase):
    def test_insufficient_evidence_can_abstain_without_inventing_a_cause(self):
        result=observability_agent.validate_final({'summary':'Insufficient evidence for a causal explanation','hypotheses':[],'missing_evidence':['No working metric source or relevant logs']},{'evidence':[]})
        self.assertEqual(result['verdict'],'insufficient_evidence');self.assertFalse(result['causality_proven'])

class ProfileTests(unittest.TestCase):
    def test_approved_profiles_use_private_keys_without_global_env_changes(self):
        profiles={'company':{'provider':'openai-compatible','model':'approved-model','url':'https://company.example/v1','key_env':'TEAM_AI_KEY'}}
        with patch.dict(os.environ,{'MONTRALOG_AI_PROFILES':json.dumps(profiles),'MONTRALOG_AI_PROFILE_KEYS':json.dumps({'TEAM_AI_KEY':'private-fixture'}),'MONTRALOG_AI_PROVIDER':'ollama'}):
            cfg=model_providers.config('company');self.assertEqual(cfg['key'],'private-fixture')
            self.assertNotIn('private-fixture',json.dumps(model_providers.public_profiles()))
            self.assertEqual(os.environ['MONTRALOG_AI_PROVIDER'],'ollama')
            with self.assertRaises(ValueError):model_providers.config('unapproved')
