"""HTTP verification against a running gateway. Uses isolated smoke environment."""
import json
import os
import secrets
import time
import urllib.error
import urllib.request
from pathlib import Path

envfile=Path(__file__).resolve().parents[1]/'.env'
if envfile.exists():
    for line in envfile.read_text().splitlines():
        if '=' in line and not line.startswith('#'):
            key,value=line.split('=',1)
            os.environ.setdefault(key,value)
base=os.getenv('MONTRALOG_URL','http://127.0.0.1:8080')
def call(path,data=None,ingest=False):
    headers={'Authorization':'Bearer '+os.environ['MONTRALOG_INGEST_TOKEN' if ingest else 'MONTRALOG_READ_TOKEN']}
    if data is not None:
        headers['Content-Type']='application/json'
    request=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
    with urllib.request.urlopen(request,timeout=15) as response:
        return response.status,json.load(response)
assert call('/readyz')[0]==200
try:
    urllib.request.urlopen(base+'/api/overview',timeout=10)
except urllib.error.HTTPError as error:
    assert error.code==401
else:
    raise AssertionError('Unauthenticated read succeeded')
trace=secrets.token_hex(16)
assert call('/api/logs',[{'service':'smoke','environment':'smoke','message':'smoke timeout 100 ms','severity':'ERROR','trace_id':trace}],True)[0]==201
assert call('/api/spans',[{'service':'smoke','environment':'smoke','trace_id':trace,'span_id':secrets.token_hex(8),'name':'smoke','time':time.time(),'duration_ms':10,'status':'ERROR'}],True)[0]==201
assert call('/api/logs?environment=smoke&trace_id='+trace)[1]['items']
assert call('/api/traces?environment=smoke&trace_id='+trace)[1]['items']
assert call('/api/patterns?environment=smoke')[1]['items']
assert call('/api/overview?environment=smoke')[1]['totals']['errors']>=1
print('PASS: live HTTP auth, readiness, ingestion, logs, patterns and trace correlation.')
if os.getenv('MONTRALOG_REQUIRE_PROMETHEUS')=='1':
    result=call('/api/targets')[1]
    assert result.get('available'),result
    targets=result.get('data',{}).get('activeTargets',[])
    assert targets,'No Prometheus targets discovered'
    print('PASS: Prometheus API reachable with configured targets.')
