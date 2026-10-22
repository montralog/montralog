"""End-to-end OTLP HTTP JSON through the collector, then gateway + Prometheus."""
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
collector=os.getenv('OTEL_SMOKE_URL','http://127.0.0.1:4318')
gateway=os.getenv('MONTRALOG_URL','http://127.0.0.1:8080')
write=os.environ['MONTRALOG_INGEST_TOKEN']
read=os.environ['MONTRALOG_READ_TOKEN']
trace=secrets.token_hex(16)
ns=int(time.time()*1e9)
attrs=[{'key':'service.name','value':{'stringValue':'collector-smoke'}},
       {'key':'deployment.environment.name','value':{'stringValue':'smoke'}}]
def request(url,data=None,token=read):
    headers={'Authorization':'Bearer '+token}
    if data is not None:
        headers['Content-Type']='application/json'
    req=urllib.request.Request(url,data=json.dumps(data).encode() if data is not None else None,headers=headers)
    with urllib.request.urlopen(req,timeout=10) as response:
        return json.load(response)
logs={'resourceLogs':[{'resource':{'attributes':attrs},'scopeLogs':[{'logRecords':[{'timeUnixNano':str(ns),'severityNumber':17,'body':{'stringValue':'Collector round-trip verification'},'traceId':trace}]}]}]}
spans={'resourceSpans':[{'resource':{'attributes':attrs},'scopeSpans':[{'spans':[{'traceId':trace,'spanId':secrets.token_hex(8),'name':'collector verification','startTimeUnixNano':str(ns),'endTimeUnixNano':str(ns+50000000),'status':{'code':2}}]}]}]}
metrics={'resourceMetrics':[{'resource':{'attributes':attrs},'scopeMetrics':[{'metrics':[{'name':'http.server.request.duration','unit':'s','histogram':{'aggregationTemporality':2,'dataPoints':[{'startTimeUnixNano':str(ns-1000000000),'timeUnixNano':str(ns),'count':'1','sum':0.05,'bucketCounts':['1','0','0'],'explicitBounds':[0.1,1.0]}]}}]}]}]}
try:
    request(collector+'/v1/logs',logs,token='invalid-token')
except urllib.error.HTTPError as error:
    assert error.code==401,error.code
else:
    raise AssertionError('Collector accepted invalid credentials')
for path,body in [('logs',logs),('traces',spans),('metrics',metrics)]:
    request(collector+'/v1/'+path,body,token=write)
print('OTLP collector accepted all three signals and rejected invalid auth.',flush=True)
deadline=time.time()+65
while time.time()<deadline:
    found_logs=request(gateway+'/api/logs?environment=smoke&trace_id='+trace)['items']
    found_spans=request(gateway+'/api/traces?environment=smoke&trace_id='+trace)['items']
    panel=request(gateway+'/api/metrics?panel=app_requests&minutes=15')
    matching=[x for x in panel.get('data',{}).get('result',[]) if x.get('metric',{}).get('service_name')=='collector-smoke']
    if found_logs and found_spans and matching:
        print('PASS: collector to log/trace storage; collector to Prometheus to application dashboard query.',flush=True)
        break
    time.sleep(2)
else:
    raise SystemExit('FAIL: one or more collector signals did not become queryable within 65 seconds')
