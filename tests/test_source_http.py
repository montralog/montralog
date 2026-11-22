"""HTTP contract checks using a disposable loopback API, not vendor certification."""
import io
import json
import os
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
import test_accounts
import test_studio
from montralog.accounts import create_account
from montralog.http import application
from montralog import connections

class SourceHTTPTests(unittest.TestCase):
    tearDown=test_accounts.AccountTests.tearDown
    admin_login=test_studio.StudioTests.admin_login

    def request(self,path,method='GET',data=None):
        parsed=urllib.parse.urlsplit(path);raw=json.dumps(data).encode() if data is not None else b''
        env={'PATH_INFO':parsed.path,'QUERY_STRING':parsed.query,'REQUEST_METHOD':method,'CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw),'HTTP_COOKIE':self.cookie,'HTTP_X_CSRF_TOKEN':self.csrf,'REMOTE_ADDR':'127.0.0.1'}
        result={}
        def start(status,headers):result.update(status=int(status.split()[0]),headers=dict(headers))
        result['body']=json.loads(b''.join(application(env,start)));return result

    def setUp(self):
        test_accounts.AccountTests.setUp(self)
        create_account('admin','Administrator','admin123')
        self.calls=[]
        self.payload_override=None
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                parsed=urllib.parse.urlsplit(self.path)
                owner.calls.append((parsed.path,urllib.parse.parse_qs(parsed.query)))
                if parsed.path.endswith('/api/v1/query'):
                    payload={'status':'success','data':{'resultType':'vector','result':[{'metric':{'job':'fixture'},'value':[1,'1']}]}}
                elif parsed.path.endswith('/api/v1/query_range') and '/loki/' not in parsed.path:
                    payload={'status':'success','data':{'resultType':'matrix','result':[{'metric':{'job':'fixture'},'values':[[1,'1']]}]}}
                elif parsed.path.endswith('/loki/api/v1/labels'):
                    payload={'status':'success','data':['service_name','level']}
                elif parsed.path.endswith('/loki/api/v1/query_range'):
                    payload={'status':'success','data':{'resultType':'streams','result':[{'stream':{'service_name':'checkout','level':'error'},'values':[['1000000000','Failed request 123'],['2000000000','Failed request 456']]}]}}
                elif parsed.path.endswith('/api/search'):
                    payload={'traces':[{'traceID':'abc123','rootServiceName':'checkout','rootTraceName':'GET /cart','durationMs':25,'startTimeUnixNano':'1000000000'}]}
                else:
                    self.send_error(404);return
                if owner.payload_override is not None:payload=owner.payload_override
                raw=json.dumps(payload).encode()
                self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.server.server_close);self.addCleanup(self.thread.join,3);self.addCleanup(self.server.shutdown)
        self.base='http://127.0.0.1:'+str(self.server.server_port)
        self.policy=patch.dict(os.environ,{'MONTRALOG_ALLOWED_DESTINATIONS':'127.0.0.1:'+str(self.server.server_port)})
        self.policy.start();self.addCleanup(self.policy.stop)
        self.admin_login()

    def save(self,kind,prefix=''):
        result=self.request('/api/control/data-sources','POST',{'name':kind,'kind':kind,'url':self.base+prefix})
        self.assertEqual(result['status'],200,result)
        return result['body']['id']

    def test_every_metric_kind_saves_and_queries_including_path_prefix(self):
        for kind,prefix in [('prometheus',''),('victoriametrics','/select/7/prometheus'),('mimir','/prometheus'),('thanos','/query')]:
            with self.subTest(kind=kind):
                source=connections.resolve(self.save(kind,prefix))
                self.assertTrue(connections.query(source,'query_range',{'query':'up','start':1,'end':2,'step':1})['available'])
                self.assertEqual(self.calls[-1][0],prefix+'/api/v1/query_range')
                self.assertEqual(self.calls[-1][1]['query'],['up'])
                dashboard=self.request('/api/saved-dashboards','POST',{'name':kind,'definition':{'minutes':60,'panels':[{'source':'metric','metric':'cpu','visual':'line','datasource':source['id']}]}})
                self.assertEqual(dashboard['status'],200,dashboard)

    def test_loki_save_logs_patterns_and_panel_reference(self):
        ident=self.save('loki','/gateway')
        logs=self.request('/api/logs?datasource='+ident)
        self.assertEqual(logs['status'],200,logs)
        self.assertEqual(len(logs['body']['items']),2)
        self.assertTrue(logs['body']['sampled'])
        grouped=self.request('/api/patterns?datasource='+ident)
        self.assertEqual(grouped['body']['items'][0]['occurrences'],2)
        result=self.request('/api/saved-dashboards','POST',{'name':'Remote logs','definition':{'panels':[{'source':'logs','visual':'table','datasource':ident}]}})
        self.assertEqual(result['status'],200,result)

    def test_tempo_save_query_and_panel_reference(self):
        ident=self.save('tempo','/gateway')
        result=self.request('/api/traces?datasource='+ident)
        self.assertEqual(result['status'],200,result)
        self.assertEqual(result['body']['items'][0]['duration_s'],.025)
        saved=self.request('/api/saved-dashboards','POST',{'name':'Remote traces','definition':{'panels':[{'source':'traces','visual':'timeline','datasource':ident}]}})
        self.assertEqual(saved['status'],200,saved)

    def test_malformed_loki_responses_are_safe_errors(self):
        ident=self.save('loki')
        for data in [[],{'resultType':'streams','result':[None]},{'resultType':'streams','result':[{'stream':{},'values':[[None,'bad']]}]}]:
            self.payload_override={'status':'success','data':data}
            result=self.request('/api/logs?datasource='+ident)
            self.assertEqual(result['status'],502,result)
            self.assertNotIn('Traceback',json.dumps(result['body']))
