import base64
import importlib.util
import tempfile
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('silo_config',Path(__file__).parents[1]/'scripts/silo_config.py')
silo=importlib.util.module_from_spec(spec);spec.loader.exec_module(silo)
class SiloConfigTests(unittest.TestCase):
    def test_upgrade_preserves_key_and_source_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'old.env';output=Path(directory)/'new.env'
            original='MONTRALOG_TENANT_ID=customer-a\nMONTRALOG_ENCRYPTION_KEY='+base64.urlsafe_b64encode(b'k'*32).decode()+'\nMONTRALOG_READ_TOKEN=legacy\n'
            source.write_text(original);silo.upgrade(source,output)
            values=silo.read_env(output)
            self.assertEqual(source.read_text(),original)
            self.assertEqual(values['MONTRALOG_ENCRYPTION_KEY'],silo.read_env(source)['MONTRALOG_ENCRYPTION_KEY'])
            self.assertTrue(values['MONTRALOG_READ_TOKEN'].startswith('mtls1.customer-a.read.'))
            with self.assertRaises(FileExistsError):silo.upgrade(source,output)
    def test_audit_rejects_reused_master_key(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=[]
            for index,tenant in enumerate(('customer-a','customer-b')):
                path=Path(directory)/(tenant+'.env');paths.append(path)
                values={'MONTRALOG_TENANT_ID':tenant,'COMPOSE_PROJECT_NAME':tenant,'MONTRALOG_ENCRYPTION_KEY':base64.urlsafe_b64encode(b'k'*32).decode(),'MONTRALOG_SILO_STRICT':'true'}
                for scope in ('read','ingest'):values['MONTRALOG_'+scope.upper()+'_TOKEN']='mtls1.'+tenant+'.'+scope+'.'+'x'*48
                for offset,name in enumerate(('HTTP','OTLP_HTTP','OTLP_GRPC')):values['MONTRALOG_'+name+'_PORT']=str(18000+index*10+offset)
                path.write_text(''.join(k+'='+v+'\n' for k,v in values.items()))
            with self.assertRaisesRegex(ValueError,'ENCRYPTION_KEY'):silo.audit(paths)
            paths[1].write_text(paths[1].read_text().replace(base64.urlsafe_b64encode(b'k'*32).decode(),base64.urlsafe_b64encode(b'z'*32).decode()))
            self.assertEqual(silo.audit(paths),2)
