"""Forward authenticated OTLP metrics to the configured private collector."""
import json
import os
import urllib.error
import urllib.request
import urllib.parse
from .accounts import AccountError
from .config import MAX_BODY
from .outbound import open_request, endpoint, DestinationError
from .connections import NoRedirect, finite_json_number

def metrics(raw):
    base=os.getenv('MONTRALOG_COLLECTOR_URL','').rstrip('/')
    if not base:raise AccountError('Metric ingestion collector is not configured.',503)
    try: url,port=endpoint(base)
    except DestinationError: raise AccountError('Invalid collector endpoint.',503) from None
    if url.scheme not in ('http','https') or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise AccountError('Configure an HTTP or HTTPS collector URL without embedded credentials.',503)
    req=urllib.request.Request(base+'/v1/metrics',data=raw,headers={
        'Content-Type':'application/json','Authorization':'Bearer '+os.environ['MONTRALOG_INGEST_TOKEN']})
    try:
        origin = (url.hostname, port)
        internal = os.getenv('MONTRALOG_ALLOW_INSECURE_COLLECTOR', '').lower() == 'true'
        with open_request(req, timeout=10, private_origins=(f'{url.hostname}:{port}',), insecure_credential_origin=origin if internal else None) as response:
            body=response.read(MAX_BODY+1)
            if len(body)>MAX_BODY:raise ValueError('Response too large')
            result=json.loads(body,parse_float=finite_json_number,parse_constant=finite_json_number)
            if not isinstance(result,dict):raise ValueError('Expected collector object')
            return result
    except urllib.error.HTTPError as error:
        error.close()
        raise AccountError('Collector rejected the metric payload.' if error.code<500 else 'Collector unavailable.',400 if error.code<500 else 503) from None
    except (OSError,ValueError):raise AccountError('Collector unavailable; retry with backoff.',503) from None
