"""Explicit synthetic telemetry for investigation walkthroughs."""
import json
import os
import secrets
import time
import urllib.request

base = os.getenv('MONTRALOG_URL','http://127.0.0.1:8080').rstrip('/')
token = os.getenv('MONTRALOG_INGEST_TOKEN','')
if len(token)<32:
    raise SystemExit('Set MONTRALOG_INGEST_TOKEN first')
now=time.time()
logs,spans=[],[]
for i in range(60):
    trace,root,child=secrets.token_hex(16),secrets.token_hex(8),secrets.token_hex(8)
    at=now-(60-i)*8
    error=i>=42
    logs.append({'time':at,'service':'checkout','environment':'demo','severity':'ERROR' if error else 'INFO',
                 'message':f'Database connection timeout after {100+i} ms' if error else f'Checkout request {i} completed',
                 'trace_id':trace,'attributes':{'demo':True,'service.version':'v42' if error else 'v41'}})
    spans.extend([{'time':at,'service':'checkout','environment':'demo','trace_id':trace,'span_id':root,
                   'name':'POST /checkout','duration_ms':220 if error else 42,'status':'ERROR' if error else 'OK'},
                  {'time':at+0.005,'service':'payments-db','environment':'demo','trace_id':trace,'span_id':child,
                   'parent_id':root,'name':'SELECT payment','duration_ms':200 if error else 15,'status':'ERROR' if error else 'OK'}])
payloads={'logs':logs,'spans':spans,'events':[{'time':now-18*8,'service':'checkout','environment':'demo','kind':'deployment','message':'Synthetic demo: checkout v42 deployed; inspect related errors (correlation, not proof of cause).'}]}
for kind,items in payloads.items():
    req=urllib.request.Request(base+'/api/'+kind,data=json.dumps(items).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=15) as response:
        print(kind,response.status,json.load(response))
