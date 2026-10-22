"""Forward authenticated OTLP metrics to the configured private collector."""
import json
import os
import urllib.error
import urllib.request
from .accounts import AccountError
from .config import MAX_BODY

def metrics(raw):
    base=os.getenv('MONTRALOG_COLLECTOR_URL','').rstrip('/')
    if not base:raise AccountError('Metric ingestion collector is not configured.',503)
    req=urllib.request.Request(base+'/v1/metrics',data=raw,headers={
        'Content-Type':'application/json','Authorization':'Bearer '+os.environ['MONTRALOG_INGEST_TOKEN']})
    try:
        with urllib.request.urlopen(req,timeout=10) as response:
            body=response.read(MAX_BODY+1)
            if len(body)>MAX_BODY:raise ValueError('Response too large')
            return json.loads(body)
    except urllib.error.HTTPError as error:
        raise AccountError('Collector rejected the metric payload.' if error.code<500 else 'Collector unavailable.',400 if error.code<500 else 503) from None
    except (OSError,ValueError):raise AccountError('Collector unavailable; retry with backoff.',503) from None
