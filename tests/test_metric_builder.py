import unittest
from unittest.mock import patch
import test_accounts
from montralog.metrics import build_query, PANELS

class QueryBuilderTests(test_accounts.AccountTests):
    def test_allowlisted_queries_and_rejected_syntax(self):
        self.assertEqual(build_query('cpu'),PANELS['cpu'][1])
        self.assertEqual(build_query('targets','avg','instance'),'avg by (instance) (up)')
        for args in [('targets','evil',''),('targets','sum','x) (up)'),('targets','none','instance'),('missing','none','')]:
            with self.assertRaises(ValueError):build_query(*args)

    def test_builder_round_trip_and_backend_execution(self):
        self.sign_in()
        definition={'minutes':60,'panels':[{'source':'metric','metric':'targets','visual':'stat','aggregation':'count','group_by':'instance'}]}
        self.assertEqual(self.request('/api/saved-dashboards','POST',{'name':'Count','definition':definition})['status'],200)
        saved=self.request('/api/saved-dashboards')['body']['items'][0]['definition']['panels'][0]
        self.assertEqual(saved['aggregation'],'count')
        self.assertEqual(saved['group_by'],'instance')
        with patch('montralog.http.prometheus',return_value={'available':True}) as query:
            from test_gateway import GatewayTests
            status,body=GatewayTests.call(self,'/api/metrics',query='panel=targets&aggregation=count&group_by=instance')
        self.assertEqual(status['status'],200)
        self.assertEqual(query.call_args.args[1]['query'],'count by (instance) (up)')
        self.assertEqual(body['panel']['unit'],'series')
        definition['panels'][0]['group_by']='instance) (up)'
        self.assertEqual(self.request('/api/saved-dashboards','POST',{'name':'Invalid','definition':definition})['status'],400)
