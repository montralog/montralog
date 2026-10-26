import io
import json
import os
import unittest
from unittest.mock import patch
from montralog import model_providers,outbound
import socket
import urllib.request

class ProviderContractTests(unittest.TestCase):
    def test_all_provider_contracts_without_sending_telemetry(self):
        answer=json.dumps({'summary':'Fixture only','hypotheses':[]})
        fixtures={
            'ollama':({'done':True,'message':{'content':answer}},'/api/chat'),
            'openai':({'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':answer}]}]},'/responses'),
            'openai-compatible':({'choices':[{'finish_reason':'stop','message':{'content':answer}}]},'/chat/completions'),
            'anthropic':({'stop_reason':'end_turn','content':[{'type':'text','text':answer}]},'/messages'),
            'gemini':({'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':answer}]}}]},'/models/fixture:generateContent')}
        for provider,(response,suffix) in fixtures.items():
            with self.subTest(provider=provider),patch.dict(os.environ,{'MONTRALOG_AI_PROVIDER':provider,'MONTRALOG_AI_MODEL':'fixture','MONTRALOG_AI_URL':'https://provider.example/v1','MONTRALOG_AI_API_KEY':'fixture-not-real'}),patch.object(model_providers,'open_request',return_value=io.BytesIO(json.dumps(response).encode())) as send:
                result,usage=model_providers.generate('JSON only','synthetic data')
                self.assertEqual(result['summary'],'Fixture only')
                request=send.call_args.args[0]
                self.assertTrue(request.full_url.endswith(suffix))
                self.assertNotIn('fixture-not-real',request.full_url)
                self.assertNotIn('fixture-not-real',request.data.decode())
                self.assertEqual(send.call_count,1)

    def test_truncated_and_oversized_responses_are_not_retried(self):
        for raw in (b'x'*65537,json.dumps({'done':False,'message':{'content':'{}'}}).encode()):
            with patch.dict(os.environ,{'MONTRALOG_AI_PROVIDER':'ollama','MONTRALOG_AI_MODEL':'fixture','MONTRALOG_AI_URL':'https://provider.example'}),patch.object(model_providers,'open_request',return_value=io.BytesIO(raw)) as send:
                with self.assertRaises(ValueError):model_providers.generate('JSON','fixture')
                self.assertEqual(send.call_count,1)

    def test_local_dns_change_to_public_never_connects(self):
        with patch.object(socket,'getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',11434))]),patch.object(socket,'socket') as connect:
            with self.assertRaises(outbound.DestinationError):
                with outbound.open_request(urllib.request.Request('http://ollama:11434/api/chat',data=b'{}'),private_origins=('ollama:11434',),insecure_credential_origin=('ollama',11434),require_private=True):pass
            connect.assert_not_called()

    def test_ollama_receives_schema_instead_of_unconstrained_json_mode(self):
        schema={'type':'object','properties':{'summary':{'type':'string'}}}
        raw=json.dumps({'done':True,'message':{'content':'{"summary":"fixture"}'}}).encode()
        with patch.dict(os.environ,{'MONTRALOG_AI_PROVIDER':'ollama','MONTRALOG_AI_MODEL':'fixture','MONTRALOG_AI_URL':'https://provider.example'}),patch.object(model_providers,'open_request',return_value=io.BytesIO(raw)) as send:
            model_providers.generate('JSON','fixture',response_schema=schema)
            self.assertEqual(json.loads(send.call_args.args[0].data)['format'],schema)

    def test_http_hosted_endpoint_cannot_receive_credentials(self):
        with patch.dict(os.environ,{'MONTRALOG_AI_PROVIDER':'openai','MONTRALOG_AI_MODEL':'fixture','MONTRALOG_AI_URL':'http://provider.example','MONTRALOG_AI_API_KEY':'fixture'}):
            with self.assertRaises(ValueError):model_providers.config()
