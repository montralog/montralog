"""Read-only installation check, with an explicitly requested synthetic demo."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url',default=os.getenv('MONTRALOG_URL','http://127.0.0.1:8080'))
parser.add_argument('--env-file',type=Path,default=root/'.env')
parser.add_argument('--demo',action='store_true',help='Explicitly insert synthetic logs, spans and a deployment event')
args=parser.parse_args();base=args.url.rstrip('/')
url=urllib.parse.urlsplit(base)
if url.scheme!='https' and not (url.scheme=='http' and url.hostname in ('127.0.0.1','localhost','::1')):
    parser.error('Use loopback HTTP or a remote HTTPS URL')
credentials={}
if args.env_file.exists():
    for line in args.env_file.read_text().splitlines():
        if line.startswith(('MONTRALOG_READ_TOKEN=','MONTRALOG_INGEST_TOKEN=')):
            key,value=line.split('=',1);credentials[key]=value
for key in ('MONTRALOG_READ_TOKEN','MONTRALOG_INGEST_TOKEN'):
    if os.getenv(key):credentials[key]=os.environ[key]

def get(path,authenticated=False):
    headers={}
    if authenticated:
        token=credentials.get('MONTRALOG_READ_TOKEN','')
        if len(token)<32:raise RuntimeError('Local read credential is unavailable; provide the installation env file')
        headers['Authorization']='Bearer '+token
    with urllib.request.urlopen(urllib.request.Request(base+path,headers=headers),timeout=15) as response:return json.load(response)

try:
    health=get('/healthz');assert get('/health/ready')['status']=='ready'
    print('PASS: gateway ready; version '+str(health.get('version','unknown')))
    try:get('/api/overview')
    except urllib.error.HTTPError as error:
        if error.code!=401:raise RuntimeError('Unexpected unauthenticated response') from None
    else:raise RuntimeError('Telemetry was readable without authentication')
    print('PASS: unauthenticated telemetry reads are rejected')
    overview=get('/api/overview',True);targets=get('/api/targets',True)
    if not targets.get('available'):raise RuntimeError(targets.get('error','Prometheus unavailable'))
    items=targets.get('data',{}).get('activeTargets',[])
    print('PASS: Prometheus reachable; '+str(len(items))+' scrape targets, '+str(sum(t.get('health')=='up' for t in items))+' reporting up')
    print('Observed '+str(overview['totals']['logs'])+' logs in the default window. Zero is expected before connecting data.')
    if args.demo:
        if len(credentials.get('MONTRALOG_INGEST_TOKEN',''))<32:raise RuntimeError('Ingest credential unavailable for the requested demo')
        env=os.environ.copy();env.update(credentials);env['MONTRALOG_URL']=base
        subprocess.run([sys.executable,str(root/'scripts/send_demo.py')],env=env,check=True)
        print('PASS: explicitly requested synthetic demo sent in environment=demo')
    print('Open '+base+' and sign in with your locally created account. These checks do not establish production capacity or complete integration health.')
except Exception as error:
    print('FAIL: '+(str(error) if isinstance(error,(RuntimeError,AssertionError)) else type(error).__name__)+'. Check Docker service status and docs/EVALUATION.md.',file=sys.stderr)
    raise SystemExit(1)
