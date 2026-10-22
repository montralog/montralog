"""Small local HTTP exercise, not a sustained production capacity benchmark."""
import concurrent.futures
import json
import os
import statistics
import time
import urllib.request
from pathlib import Path

root=Path(__file__).resolve().parents[1]
for line in (root/'.env').read_text().splitlines():
    if '=' in line and not line.startswith('#'):
        key,value=line.split('=',1)
        os.environ.setdefault(key,value)
url=os.getenv('MONTRALOG_URL','http://127.0.0.1:8080')
headers={'Authorization':'Bearer '+os.environ['MONTRALOG_INGEST_TOKEN'],'Content-Type':'application/json'}
def send(index):
    items=[{'service':'benchmark','environment':'benchmark','message':f'Batch {index} record {i}','severity':'INFO'} for i in range(50)]
    start=time.perf_counter()
    req=urllib.request.Request(url+'/api/logs',data=json.dumps(items).encode(),headers=headers)
    with urllib.request.urlopen(req,timeout=20) as response:
        assert response.status==201
        assert json.load(response)['accepted']==50
    return time.perf_counter()-start
start=time.perf_counter()
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    latencies=list(pool.map(send,range(20)))
elapsed=time.perf_counter()-start
report={'scenario':'1000 synthetic logs, 20 batches of 50, four concurrent clients, loopback HTTP',
        'records':1000,'elapsed_seconds':round(elapsed,3),'records_per_second_observed':round(1000/elapsed,1),
        'batch_latency_median_ms':round(statistics.median(latencies)*1000,2),
        'batch_latency_p95_ms':round(sorted(latencies)[18]*1000,2),
        'limitations':'Short warm local run only; not sustained load, remote networking, production sizing or a supported capacity limit.'}
print(json.dumps(report,indent=2))
