"""Unprivileged host sample collector. Does not inspect processes or containers."""
import json
import argparse
import logging
import os
import socket
import time
import urllib.request
import psutil

parser=argparse.ArgumentParser()
parser.add_argument('--once',action='store_true',help='Collect one interval and exit')
options=parser.parse_args()

base=os.getenv('MONTRALOG_URL','http://127.0.0.1:8080').rstrip('/')
token=os.getenv('MONTRALOG_INGEST_TOKEN','')
service=os.getenv('MONTRALOG_HOST',socket.gethostname())
environment=os.getenv('MONTRALOG_ENVIRONMENT','default')
interval=max(5,int(os.getenv('MONTRALOG_INTERVAL','15')))
if len(token)<32:
    raise SystemExit('Set MONTRALOG_INGEST_TOKEN first')
if not base.startswith('https://') and not base.startswith(('http://127.0.0.1:','http://localhost:')):
    raise SystemExit('Remote host collection requires an HTTPS endpoint')
backoff=interval
while True:
    try:
        net=psutil.net_io_counters()
        values=[('host_cpu_usage',psutil.cpu_percent(interval=1),'%'),
                ('host_memory_usage',psutil.virtual_memory().percent,'%'),
                ('host_disk_usage',psutil.disk_usage(os.path.abspath(os.sep)).percent,'%'),
                ('host_network_sent_bytes',net.bytes_sent,'bytes'),
                ('host_network_received_bytes',net.bytes_recv,'bytes')]
        items=[{'time':time.time(),'service':service,'environment':environment,'name':name,'value':value,'unit':unit} for name,value,unit in values]
        request=urllib.request.Request(base+'/api/samples',data=json.dumps(items).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=10) as response:
            response.read()
        print('Host samples delivered',flush=True)
        backoff=interval
        if options.once:
            break
    except Exception:
        logging.exception('Delivery failed; samples from this interval are not buffered')
        if options.once:
            raise SystemExit(1)
        backoff=min(300,backoff*2)
    time.sleep(backoff)
