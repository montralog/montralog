"""Exercise the documented Docker-only bootstrap on disposable host files."""
import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', required=True)
    parser.add_argument('--output', default='work/acceptance/bootstrap.json')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='mtl-bootstrap-') as scratch:
        target = Path(scratch)
        (target/'scripts').mkdir()
        for name in ('setup.py','create_tenant.py'):
            shutil.copyfile(root/'scripts'/name, target/'scripts'/name)
        def run(script, *options, success=True):
            result = subprocess.run(['docker','run','--rm','--network','none','--user','0:0',
                '--entrypoint','python','-v',str(target)+':/install',args.image,'/install/scripts/'+script,*options],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            assert (result.returncode == 0) == success, (script,result.stderr)
        run('setup.py')
        original = (target/'.env').read_bytes()
        run('setup.py',success=False)
        assert (target/'.env').read_bytes() == original
        def customer(name, ports, success=True):
            run('create_tenant.py','--tenant',name,'--http-port',str(ports[0]),'--otlp-http-port',str(ports[1]),'--otlp-grpc-port',str(ports[2]),success=success)
        customer('alpha',(18080,14318,14317))
        customer('beta',(18081,14328,14327))
        alpha = target/'.local/tenants/alpha.env'
        before = alpha.read_bytes()
        customer('alpha',(18082,14338,14337),success=False)
        assert alpha.read_bytes() == before
        customer('overlap',(18080,14348,14347),success=False)
        customer('../escape',(18083,14358,14357),success=False)
        files = (target/'.env', alpha, target/'.local/tenants/beta.env')
        values = [dict(line.split('=',1) for line in p.read_text().splitlines()) for p in files]
        for key in ('MONTRALOG_TENANT_ID','MONTRALOG_READ_TOKEN','MONTRALOG_INGEST_TOKEN','MONTRALOG_ENCRYPTION_KEY'):
            assert len({v[key] for v in values}) == 3
        if os.name == 'posix':
            for p in files:
                assert p.stat().st_uid == target.stat().st_uid
                assert stat.S_IMODE(p.stat().st_mode) == 0o600
            assert stat.S_IMODE(alpha.parent.stat().st_mode) == 0o700
    report = {'result':'PASS','checks':['Docker-only setup','operator file ownership and private POSIX modes',
        'no credential overwrite','independent tenant IDs/tokens/keys','port collision rejection','path traversal rejection'],
        'limits':'Windows private-file access also depends on host ACLs; no customer data used.'}
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__': main()
