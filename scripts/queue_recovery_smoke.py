"""Local Docker-only restart recovery exercise with synthetic data.

Temporarily stops gateway/retention, queues one log, restarts the collector, and
brings the gateway back. Run only on a controlled evaluation deployment.
"""
import json
import os
import secrets
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

root=Path(__file__).resolve().parents[1]
for line in (root/'.env').read_text().splitlines():
    if '=' in line and not line.startswith('#'):
        key,value=line.split('=',1)
        os.environ.setdefault(key,value)
def compose(*args):
    subprocess.run(['docker','compose',*args],cwd=root,check=True)
def request(url,token,data=None):
    headers={'Authorization':'Bearer '+token}
    if data is not None:
        headers['Content-Type']='application/json'
    req=urllib.request.Request(url,data=json.dumps(data).encode() if data is not None else None,headers=headers)
    with urllib.request.urlopen(req,timeout=10) as response:
        return json.load(response)
trace=secrets.token_hex(16)
body={'resourceLogs':[{'resource':{'attributes':[
    {'key':'service.name','value':{'stringValue':'queue-recovery'}},
    {'key':'deployment.environment.name','value':{'stringValue':'verification'}}]},
    'scopeLogs':[{'logRecords':[{'timeUnixNano':str(int(time.time()*1e9)),'traceId':trace,
                                'severityNumber':9,'body':{'stringValue':'Persistent queue recovery verification'}}]}]}]}
try:
    compose('stop','gateway','retention')
    request('http://127.0.0.1:4318/v1/logs',os.environ['MONTRALOG_INGEST_TOKEN'],body)
    time.sleep(7)  # Allow the configured five-second batch flush into disk queue.
    compose('restart','collector')
finally:
    # Restore the controlled deployment even if the verification encounters errors.
    compose('up','-d','--wait','--wait-timeout','120','gateway','retention')
deadline=time.time()+90
while time.time()<deadline:
    data=request('http://127.0.0.1:8080/api/logs?environment=verification&trace_id='+trace,os.environ['MONTRALOG_READ_TOKEN'])
    if data['items']:
        print('PASS: log accepted during gateway outage survived collector restart and reached storage')
        break
    time.sleep(2)
else:
    raise SystemExit('FAIL: queued log did not recover within 90 seconds')
