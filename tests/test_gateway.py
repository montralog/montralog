import io
import json
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import montralog.http as app
from montralog import storage
from montralog.storage import initialize, prune

class GatewayTests(unittest.TestCase):
    def setUp(self):
        scratch=Path(os.getenv('MONTRALOG_TEST_TMP',str(Path(__file__).resolve().parents[1]/'work')))
        scratch.mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=scratch)
        storage.DB=Path(self.tmp.name)/'data.db'
        self.env=patch.dict(os.environ,{'MONTRALOG_READ_TOKEN':'r'*40,'MONTRALOG_INGEST_TOKEN':'w'*40,'RETENTION_DAYS':'7','PROMETHEUS_URL':'','MONTRALOG_DATABASE_URL':'','MONTRALOG_ALLOWED_DESTINATIONS':'127.0.0.1:9090,localhost:4318'})
        self.env.start()
        initialize()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def call(self,path,method='GET',payload=None,token='r'*40,query='',content_type='application/json',length=None):
        data=json.dumps(payload).encode() if payload is not None else b''
        env={'PATH_INFO':path,'REQUEST_METHOD':method,'QUERY_STRING':query,'HTTP_AUTHORIZATION':'Bearer '+token,
             'CONTENT_TYPE':content_type,'CONTENT_LENGTH':str(len(data) if length is None else length),'wsgi.input':io.BytesIO(data)}
        captured={}
        def start(status,headers):
            captured.update(status=int(status.split()[0]),headers=dict(headers))
        response=b''.join(app.application(env,start))
        return captured,json.loads(response) if captured['headers']['Content-Type'].startswith('application/json') else response

    def write(self,kind,items):
        return self.call('/api/'+kind,'POST',items,'w'*40)

    def test_authentication_and_role_separation(self):
        self.assertEqual(self.call('/api/overview',token='')[0]['status'],401)
        self.assertEqual(self.call('/api/overview',token='w'*40)[0]['status'],401)
        self.assertEqual(self.call('/api/logs','POST',[{'service':'api','message':'hello'}])[0]['status'],401)
        self.assertEqual(self.call('/readyz')[0]['status'],200)
        self.assertEqual(self.call('/healthz',token='')[0]['status'],200)
        self.assertEqual(self.call('/health/ready',token='')[0]['status'],200)

    def test_logs_redaction_search_and_pattern_grouping(self):
        status,result=self.write('logs',[
            {'service':'api','message':'Timeout after 100 ms password=hunter2','severity':'ERROR','attributes':{'api_key':'sensitive','nested':{'token':'nested-secret'}}},
            {'service':'api','message':'Timeout after 200 ms password=hunter2','severity':'ERROR'}])
        self.assertEqual(status['status'],201)
        self.assertEqual(result['accepted'],2)
        logs=self.call('/api/logs',query='q=Timeout')[1]['items']
        self.assertNotIn('hunter2',json.dumps(logs))
        self.assertNotIn('nested-secret',json.dumps(logs))
        self.assertEqual(self.call('/api/patterns')[1]['items'][0]['occurrences'],2)
        self.assertEqual(self.call('/api/overview')[1]['totals']['errors'],2)

    def test_authorization_bearer_redacts_whole_credential(self):
        self.write('logs',[{'service':'api','message':'authorization=Bearer confidential.jwt-value'}])
        self.assertNotIn('confidential',json.dumps(self.call('/api/logs')[1]))

    def test_invalid_batch_rolls_back_and_handles_nan(self):
        response=self.write('logs',[{'service':'api','message':'ok'},{'message':'missing service'}])
        self.assertEqual(response[0]['status'],400)
        self.assertEqual(self.call('/api/overview')[1]['totals']['logs'],0)
        self.assertEqual(self.write('samples',[{'service':'host','name':'cpu','value':float('nan')}])[0]['status'],400)

    def test_filters_and_literal_search(self):
        self.write('logs',[{'service':"api' OR 1=1 --",'environment':'prod','message':'100% available'},
                           {'service':'api','environment':'test','message':'hello'},
                           {'service':'api','environment':'prod','message':'old','time':time.time()-7200}])
        self.assertEqual(len(self.call('/api/logs',query='environment=prod')[1]['items']),1)
        self.assertEqual(len(self.call('/api/logs',query='q=%25')[1]['items']),1)
        self.assertEqual(len(self.call('/api/logs',query='service=missing')[1]['items']),0)

    def test_search_case_is_consistent(self):
        self.write('logs',[{'service':'api','message':'DATABASE Timeout'}])
        self.assertEqual(len(self.call('/api/logs',query='q=database')[1]['items']),1)

    def test_pagination(self):
        self.write('logs',[{'service':'api','message':str(i)} for i in range(105)])
        first=self.call('/api/logs')[1]
        last=self.call('/api/logs',query='offset=100')[1]
        self.assertEqual(len(first['items']),100)
        self.assertTrue(first['has_more'])
        self.assertEqual(len(last['items']),5)
        self.assertFalse(last['has_more'])

    def test_otlp_json_logs_and_traces(self):
        trace='ab'*16
        ns=int((time.time()-1)*1e9)
        attrs=[{'key':'service.name','value':{'stringValue':'checkout'}}]
        logs={'resourceLogs':[{'resource':{'attributes':attrs},'scopeLogs':[{'logRecords':[{'timeUnixNano':str(ns),'severityNumber':17,'body':{'stringValue':'failed'},'traceId':trace}]}]}]}
        self.assertEqual(self.call('/v1/logs','POST',logs,'w'*40)[0]['status'],200)
        traces={'resourceSpans':[{'resource':{'attributes':attrs},'scopeSpans':[{'spans':[{'traceId':trace,'spanId':'cd'*8,'name':'GET /','startTimeUnixNano':str(ns),'endTimeUnixNano':str(ns+42000000),'status':{'code':2}}]}]}]}
        self.assertEqual(self.call('/v1/traces','POST',traces,'w'*40)[0]['status'],200)
        self.assertEqual(self.call('/v1/traces','POST',traces,'w'*40)[0]['status'],200)
        spans=self.call('/api/traces',query='trace_id='+trace)[1]['items']
        self.assertEqual(len(spans),1)
        self.assertEqual(spans[0]['duration_ms'],42)
        self.assertEqual(self.call('/api/logs',query='trace_id='+trace)[1]['items'][0]['severity'],'ERROR')
        self.assertEqual(self.call('/v1/logs','POST',{'wrong':[]},'w'*40)[0]['status'],400)

    def test_size_content_type_and_identifier_limits(self):
        self.assertEqual(self.call('/api/logs','POST',[],'w'*40,length=app.MAX_BODY+1)[0]['status'],413)
        self.assertEqual(self.call('/api/logs','POST',[],'w'*40,content_type='application/x-protobuf')[0]['status'],415)
        self.assertEqual(self.write('logs',[{'service':'api','message':'ok','trace_id':'<script>'}])[0]['status'],400)
        self.assertEqual(self.call('/api/logs',query='minutes=0')[0]['status'],400)
        self.assertEqual(self.write('logs',[{'service':'api','message':'x'}]*1001)[0]['status'],400)

    def test_storage_failures_report_unavailable(self):
        with patch('montralog.queries.database',side_effect=storage.StorageError('disk full')):
            self.assertEqual(self.call('/api/overview')[0]['status'],503)

    def test_static_security_headers_and_traversal(self):
        status,body=self.call('/',token='')
        self.assertIn(b'montralog',body)
        self.assertIn("frame-ancestors 'none'",status['headers']['Content-Security-Policy'])
        self.assertEqual(self.call('/../.env')[0]['status'],404)

    def test_metric_queries_are_allowlisted(self):
        self.assertFalse(self.call('/api/metrics')[1]['available'])
        self.assertEqual(self.call('/api/metrics',query='panel=arbitrary')[0]['status'],400)
        with patch.object(app,'prometheus',return_value={'available':True,'data':{'result':[]}}) as mock:
            self.call('/api/metrics',query='panel=cpu')
            self.assertEqual(mock.call_args.args[0],'query_range')
            self.assertIn('node_cpu_seconds_total',mock.call_args.args[1]['query'])

    def test_retention_and_backup_restore(self):
        self.write('logs',[{'service':'api','message':'old','time':time.time()-9*86400},{'service':'api','message':'new'}])
        prune()
        target=Path(self.tmp.name)/'backup.db'
        with app.database() as source,closing(sqlite3.connect(target)) as backup:
            source.backup(backup)
        storage.DB=target
        self.assertEqual(self.call('/api/overview')[1]['totals']['logs'],1)

    def test_concurrent_ingestion(self):
        def send(i):
            return self.write('logs',[{'service':'worker','message':f'item {i}'}])[0]['status']
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertTrue(all(s==201 for s in pool.map(send,range(40))))
        self.assertEqual(self.call('/api/overview')[1]['totals']['logs'],40)

    def test_sample_only_resources_and_events(self):
        self.write('samples',[{'service':'host','name':'host_cpu_usage','value':12.5,'unit':'%'}])
        self.write('events',[{'service':'host','kind':'deployment','message':'v1'}])
        self.assertEqual(self.call('/api/overview')[1]['services'][0]['service'],'host')
        self.assertEqual(len(self.call('/api/events')[1]['items']),1)

if __name__=='__main__':
    unittest.main()
