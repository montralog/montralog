import io
import json
import unittest
from unittest.mock import patch
import test_connections
from montralog import connections, storage
from montralog.accounts import AccountError
from montralog.studio import clean_definition

class AdvancedPanelTests(unittest.TestCase):
    def test_gauge_and_reference_validation(self):
        panel={'source':'metric','metric':'cpu','visual':'gauge','width':'third','height':'tall','icon':'server','description':'CPU utilization','reference':'https://example.com/runbook','min':0,'max':100,'warning':70,'critical':90}
        clean=clean_definition({'panels':[panel]})['panels'][0]
        self.assertEqual(clean['width'],'third')
        self.assertEqual(clean['critical'],90)
        for change in ({'reference':'javascript:alert(1)'},{'reference':'https://u:p@example.com'},{'critical':'nan'},{'min':90},{'icon':'<svg>'},{'reference':'https://example.com/\nheader'}):
            with self.subTest(change=change),self.assertRaises(AccountError):clean_definition({'panels':[{**panel,**change}]})

    def test_loki_literal_filters_and_sampled_patterns(self):
        source={'kind':'loki','url':'https://logs.example.com'}
        result={'status':'success','data':{'resultType':'streams','result':[{'stream':{'service_name':'checkout','level':'error'},'values':[['1000000000','Failed request 123'],['2000000000','Failed request 456']]}]}}
        with patch.object(connections,'remote_json',return_value=result) as request:
            data=connections.remote_records(source,'patterns',{'q':'" | drop all'})
        self.assertTrue(data['sampled']);self.assertEqual(sum(p['occurrences'] for p in data['items']),2)
        self.assertIn('|= '+json.dumps('" | drop all'),request.call_args.args[2]['query'])
        self.assertEqual(request.call_args.args[2]['limit'],100)
        with self.assertRaises(AccountError):connections.remote_records(source,'traces',{})

    def test_tempo_search_normalization_and_malformed_data(self):
        source={'kind':'tempo','url':'https://traces.example.com'}
        with patch.object(connections,'remote_json',return_value={'traces':[{'traceID':'abc','durationMs':25,'startTimeUnixNano':'1000000000','rootServiceName':'api'}]}):
            data=connections.remote_records(source,'traces',{})
        self.assertEqual(data['items'][0]['duration_s'],.025)
        self.assertTrue(data['items'][0]['remote'])
        with patch.object(connections,'remote_json',return_value={'traces':'bad'}),self.assertRaises(AccountError):connections.remote_records(source,'traces',{})

    def test_remote_transport_does_not_leak_secrets_and_blocks_http_credentials(self):
        source={'kind':'loki','url':'https://logs.example.com','auth_type':'bearer','secret':'secret-test'}
        with patch.object(connections,'validate_url',return_value=source['url']),patch.object(connections,'open_request',return_value=io.BytesIO(b'{"status":"success","data":[]}')) as opened:
            self.assertTrue(connections.test_remote(source)['available'])
            self.assertEqual(opened.call_args.args[0].get_header('Authorization'),'Bearer secret-test')
        with patch.object(connections,'validate_url',return_value='http://logs.example.com'),self.assertRaises(AccountError):connections.remote_json(source,'/loki/api/v1/labels')

class AdapterPersistenceTests(test_connections.ConnectionTests):
    def test_save_loki_cannot_be_default_and_rejects_wrong_panel_signal(self):
        self.admin_login()
        with patch.object(connections,'test_remote',return_value={'available':True,'data':{'result':[]}}):
            result=self.request('/api/control/data-sources','POST',{'name':'Logs','kind':'loki','url':'https://127.0.0.1:9090','is_default':True})
        self.assertEqual(result['status'],200)
        row=connections.resolve(result['body']['id']);self.assertEqual(row['kind'],'loki');self.assertFalse(row['is_default'])
        with self.assertRaises(AccountError):clean_definition({'panels':[{'source':'metric','metric':'cpu','visual':'line','datasource':row['id']}]})
        self.assertEqual(clean_definition({'panels':[{'source':'logs','visual':'table','datasource':row['id']} ]})['panels'][0]['datasource'],row['id'])

    def test_schema_7_upgrade_preserves_existing_source(self):
        with storage.database() as db:
            db.execute("INSERT INTO data_sources(id,name,url,auth_type,username,secret,is_default,last_checked,last_status,last_detail,created_at) VALUES ('legacy','Legacy','https://example.com','none','','',0,0,'connected','',0)")
            db.execute('ALTER TABLE data_sources DROP COLUMN kind')
            db.execute('DELETE FROM schema_migrations WHERE version=8')
        storage.initialize()
        self.assertEqual(connections.resolve('legacy')['kind'],'prometheus')
