"""Local Docker CLI + optional host metrics -> authenticated OTLP collector.

No Docker socket is mounted into Montralog. This process inherits the operator's
Docker CLI access and only invokes info, ps and stats. No container log contents,
environment variables, command lines or filesystem contents are collected.
"""
import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import math
import os
from pathlib import Path
import re
import socket
import subprocess
import time
import urllib.request
import urllib.parse

def docker(*args):
    result=subprocess.run(['docker',*args],capture_output=True,text=True,timeout=30,check=True,
                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]

def quantity(value):
    match=re.fullmatch(r'\s*([0-9.]+)\s*([A-Za-z]*)\s*',str(value))
    if not match:
        raise ValueError('Unrecognized Docker size')
    number,unit=match.groups()
    powers={'':1,'B':1,'kB':1000,'KB':1000,'MB':1000**2,'GB':1000**3,'TB':1000**4,
            'KiB':1024,'MiB':1024**2,'GiB':1024**3,'TiB':1024**4}
    result=float(number)*powers[unit]
    if not math.isfinite(result) or result<0:
        raise ValueError('Invalid Docker size')
    return result

def docker_points(rows,now):
    points=[]
    for row in rows:
        labels={'container_name':row['Name'],'container_id':row['ID']}
        memory,limit=map(quantity,row['MemUsage'].split('/'))
        received,sent=map(quantity,row['NetIO'].split('/'))
        read,written=map(quantity,row['BlockIO'].split('/'))
        values={'cpu_cores':float(row['CPUPerc'].rstrip('%'))/100,
                'memory_bytes':memory,'memory_limit_bytes':limit,
                'memory_percent':float(row['MemPerc'].rstrip('%')),
                'network_received_bytes':received,'network_sent_bytes':sent,
                'block_read_bytes':read,'block_written_bytes':written,
                'processes':int(row['PIDs']),'last_seen_timestamp_seconds':now}
        for name,value in values.items():
            if not math.isfinite(value) or value<0:
                raise ValueError('Invalid Docker measurement')
            points.append(('montralog_docker_'+name,value,labels))
    points.append(('montralog_docker_running_containers',len(rows),{}))
    points.append(('montralog_docker_collection_timestamp_seconds',now,{}))
    return points

def payload(points,host,now):
    metrics={}
    for name,value,labels in points:
        metric=metrics.setdefault(name,{'name':name,'gauge':{'dataPoints':[]}})
        metric['gauge']['dataPoints'].append({'timeUnixNano':str(int(now*1e9)),'asDouble':value,
            'attributes':[{'key':k,'value':{'stringValue':str(v)}} for k,v in labels.items()]})
    resource={'attributes':[{'key':k,'value':{'stringValue':v}} for k,v in
              {'service.name':'montralog-local-agent','host.name':host,'deployment.environment.name':'local'}.items()]}
    return {'resourceMetrics':[{'resource':resource,'scopeMetrics':[{'scope':{'name':'montralog.local-docker'},'metrics':list(metrics.values())}]}]}

def collect(include_host=False):
    rows=docker('stats','--no-stream','--format','{{json .}}')
    if len(rows)>100:
        raise ValueError('Local agent supports at most 100 running containers')
    now=time.time()
    points=docker_points(rows,now)
    if include_host:
        import psutil
        values={'cpu_percent':psutil.cpu_percent(interval=1),
                'memory_percent':psutil.virtual_memory().percent,
                'disk_percent':psutil.disk_usage(os.path.abspath(os.sep)).percent,
                'collection_timestamp_seconds':now}
        points.extend(('montralog_host_'+name,value,{}) for name,value in values.items())
    return payload(points,socket.gethostname(),now),len(rows)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--env-file',type=Path)
    parser.add_argument('--once',action='store_true')
    parser.add_argument('--host',action='store_true',help='Also collect this operating system via psutil')
    parser.add_argument('--interval',type=int,default=15)
    parser.add_argument('--log-file',type=Path)
    options=parser.parse_args()
    handler=RotatingFileHandler(options.log_file,maxBytes=2*1024*1024,backupCount=3,encoding='utf-8') if options.log_file else logging.StreamHandler()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',handlers=[handler])
    if options.env_file:
        for line in options.env_file.read_text().splitlines():
            if line.startswith(('MONTRALOG_INGEST_TOKEN=','OTEL_EXPORTER_OTLP_ENDPOINT=')):
                key,value=line.split('=',1);os.environ.setdefault(key,value)
    base=os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT','http://127.0.0.1:4318').rstrip('/')
    url=urllib.parse.urlparse(base)
    if url.scheme!='https' and not (url.scheme=='http' and url.hostname in ('127.0.0.1','localhost','::1')):
        parser.error('Use a loopback HTTP or remote HTTPS collector endpoint')
    token=os.getenv('MONTRALOG_INGEST_TOKEN','')
    if len(token)<32:parser.error('Set MONTRALOG_INGEST_TOKEN or pass --env-file')
    if options.host:
        try:import psutil
        except ImportError:parser.error('Host mode requires psutil==7.0.0')
    # Check the selected Docker daemon before collecting. This agent targets local Docker only.
    context=docker('context','inspect','--format','{{json .Endpoints.docker.Host}}')
    endpoint=context[0] if context else ''
    if not endpoint.startswith(('npipe://','unix://')):
        parser.error('Select a local Docker context (named pipe or Unix socket)')
    backoff=max(5,options.interval)
    while True:
        started=time.monotonic()
        try:
            data,count=collect(options.host)
            raw=json.dumps(data,allow_nan=False).encode()
            if len(raw)>2*1024*1024:raise ValueError('OTLP payload exceeds 2 MiB')
            req=urllib.request.Request(base+'/v1/metrics',data=raw,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=10) as response:
                result=json.load(response)
                if result.get('partialSuccess',{}).get('rejectedDataPoints'):
                    raise ValueError('Collector rejected metric points')
            logging.info('Delivered metrics for %s running containers%s',count,' and local host' if options.host else '')
            backoff=max(5,options.interval)
            if options.once:return
        except Exception as error:
            # Do not include request headers, environment, container metadata or credentials.
            logging.error('Local collection/delivery failed (%s); retrying',type(error).__name__)
            if options.once:raise SystemExit(1)
            backoff=min(300,backoff*2)
        time.sleep(max(1,backoff-(time.monotonic()-started)))

if __name__=='__main__':main()
