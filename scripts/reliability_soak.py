"""Disposable Docker ingestion/idempotency, restart and verified-restore probe.

Only synthetic data is used. This is a reproducible acceptance workload, not a
capacity guarantee, external penetration test or real Slack receipt test.
"""
import argparse
import base64
import concurrent.futures
import datetime
import json
from pathlib import Path
import secrets
import subprocess
import threading
import time
import urllib.error
import urllib.request


def docker(*args):
    result=subprocess.run(['docker',*args],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
    if result.returncode:
        # In particular, do not render the run command containing fixture keys.
        raise RuntimeError('Docker operation failed: '+str(args[0]))
    return result.stdout.strip()


def percentile(values,fraction):
    ordered=sorted(values)
    return round(ordered[min(len(ordered)-1,int((len(ordered)-1)*fraction))],3) if ordered else None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image',required=True)
    parser.add_argument('--output',default='work/acceptance/reliability-soak.json')
    parser.add_argument('--duration',type=int,default=30)
    parser.add_argument('--clients',type=int,default=4)
    parser.add_argument('--batch-size',type=int,default=50)
    parser.add_argument('--max-events',type=int,default=100000)
    parser.add_argument('--rate',type=int,default=1000,help='Target unique events/second; zero means unthrottled')
    args=parser.parse_args()
    if not 5<=args.duration<=600 or not 1<=args.clients<=32 or not 1<=args.batch_size<=1000 or not args.batch_size<=args.max_events<=1000000 or not 0<=args.rate<=100000:
        parser.error('Use duration 5-600s, clients 1-32, batches 1-1000, max-events batch-size to 1000000, rate 0-100000')
    nonce=secrets.token_hex(12)
    name='mtl-soak-'+nonce;volume='mtl-soak-data-'+nonce;tenant='soak-'+nonce
    read='mtls1.'+tenant+'.read.'+secrets.token_urlsafe(36)
    ingest='mtls1.'+tenant+'.ingest.'+secrets.token_urlsafe(36)
    key=base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    report={'result':'FAIL','image':args.image,'started_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'container_limits':{'cpus':1,'memory_mib':512,'pids':128},
        'workload':{'requested_duration_seconds':args.duration,'clients':args.clients,'batch_size':args.batch_size,'max_events':args.max_events,'target_unique_events_per_second':args.rate},
        'limits':['Disposable synthetic SQLite workload; not PostgreSQL/native failover or production sizing.',
                  'Only explicit idempotency keys are replayed; deduplication depends on receipt retention and credential scope.',
                  'Slack is stubbed and retry deadline is advanced; no external notifications are sent.',
                  'Gateway restart and verified application snapshot restore do not test disk/host failure or other backend volumes.']}
    stop=threading.Event();guard=threading.Lock()
    counters={'requests':0,'http_retries':0,'network_retries':0,'terminal_errors':0,'duplicate_requests':0}
    cleanup={'container':False,'volume':False}
    report['stage']='create_disposable_stack'
    try:
        docker('volume','create','--label','montralog.disposable=soak','--label','montralog.soak_run='+nonce,volume)
        docker('run','-d','--pull','never','--name',name,'--label','montralog.disposable=soak','--label','montralog.soak_run='+nonce,
            '--cpus','1','--memory','512m','--pids-limit','128','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true',
            '--tmpfs','/tmp:rw,nosuid,noexec,size=64m,mode=1777','-p','127.0.0.1::8080','-v',volume+':/data',
            '-e','MONTRALOG_TENANT_ID='+tenant,'-e','MONTRALOG_READ_TOKEN='+read,'-e','MONTRALOG_INGEST_TOKEN='+ingest,
            '-e','MONTRALOG_ENCRYPTION_KEY='+key,'-e','MONTRALOG_ENCRYPTION_REQUIRED=true','-e','MONTRALOG_SILO_STRICT=true',
            '-e','MONTRALOG_AI_ENABLED=false',args.image)
        base='http://'+docker('port',name,'8080/tcp').splitlines()[0]
        report['image_id']=docker('image','inspect',args.image,'--format','{{.Id}}')
        report['source_revision']=docker('image','inspect',args.image,'--format','{{index .Config.Labels "org.opencontainers.image.revision"}}')

        def request(path,payload=None,receipt=None,retries=8):
            headers={'Content-Type':'application/json','Authorization':'Bearer '+(ingest if payload is not None else read)}
            if receipt:headers['Idempotency-Key']=receipt
            for attempt in range(retries+1):
                with guard:counters['requests']+=1
                try:
                    req=urllib.request.Request(base+path,data=payload,headers=headers)
                    with urllib.request.urlopen(req,timeout=20) as response:
                        raw=response.read(2*1024*1024+1)
                    if len(raw)>2*1024*1024:raise ValueError('Oversized test response')
                    return json.loads(raw)
                except urllib.error.HTTPError as error:
                    code=error.code;error.close()
                    if code not in (429,503) or attempt==retries:raise
                    with guard:counters['http_retries']+=1
                except OSError:
                    if attempt==retries:raise
                    with guard:counters['network_retries']+=1
                time.sleep(min(1,.05*2**attempt))

        def ready():
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                try:
                    request('/health/ready',retries=0);return
                except (OSError,ValueError):time.sleep(.2)
            raise RuntimeError('Disposable gateway did not become ready')

        def count_logs():
            return request('/api/overview?service=reliability-soak&environment=synthetic')['totals']['logs']

        report['stage']='initial_readiness'
        ready()
        for field in counters:counters[field]=0
        report['stage']='concurrent_ingestion_and_queries'
        started=time.monotonic();deadline=started+args.duration
        allocation={'next':0};acknowledged={};replays=[];batch_ms=[];query_ms=[]

        def allocate():
            with guard:
                index=allocation['next']
                if (index+1)*args.batch_size>args.max_events:return None
                scheduled=started+(index*args.batch_size/args.rate if args.rate else 0)
                if time.monotonic()>=deadline or scheduled>=deadline:return None
                allocation['next']+=1
                return index,scheduled

        def sender():
            while not stop.is_set():
                slot=allocate()
                if slot is None:return
                index,scheduled=slot
                if stop.wait(max(0,scheduled-time.monotonic())):return
                records=[{'service':'reliability-soak','environment':'synthetic','severity':'ERROR',
                    'message':f'Synthetic soak batch {index} event {event}'} for event in range(args.batch_size)]
                payload=json.dumps(records,separators=(',',':')).encode()
                receipt=f'soak-{nonce}-{index:08}'
                instant=time.perf_counter()
                try:
                    result=request('/api/logs',payload,receipt)
                    if result.get('accepted')!=args.batch_size:raise ValueError('Unexpected acknowledgement count')
                    with guard:
                        acknowledged[index]=args.batch_size
                        batch_ms.append((time.perf_counter()-instant)*1000)
                        if len(replays)<5:replays.append((receipt,payload))
                    if index%5==0:
                        result=request('/api/logs',payload,receipt)
                        if result.get('accepted')!=args.batch_size:raise ValueError('Replay acknowledgement changed')
                        with guard:counters['duplicate_requests']+=1
                except Exception:
                    with guard:counters['terminal_errors']+=1
                    stop.set();raise

        def querier():
            while time.monotonic()<deadline and not stop.is_set():
                instant=time.perf_counter()
                try:request('/api/logs?service=reliability-soak&environment=synthetic&minutes=60')
                except Exception:
                    with guard:counters['terminal_errors']+=1
                    stop.set();raise
                query_ms.append((time.perf_counter()-instant)*1000)
                stop.wait(.25)

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.clients+1) as pool:
            query_future=pool.submit(querier)
            futures=[pool.submit(sender) for _ in range(args.clients)]
            for future in futures:future.result()
            query_future.result()
        elapsed=time.monotonic()-started
        unique=sum(acknowledged.values());stored=count_logs()
        report['ingestion']={'acknowledged_unique_events':unique,'stored_events':stored,'missing_events':max(0,unique-stored),
            'extra_events':max(0,stored-unique),'elapsed_seconds':round(elapsed,3),'unique_events_per_second':round(unique/elapsed,2),
            'allocated_batches':allocation['next'],'acknowledged_batches':len(acknowledged),'event_cap_reached':allocation['next']*args.batch_size>=args.max_events,
            'batch_latency_ms':{'p50':percentile(batch_ms,.5),'p95':percentile(batch_ms,.95)},
            'query_latency_ms':{'count':len(query_ms),'p50':percentile(query_ms,.5),'p95':percentile(query_ms,.95)},'transport':dict(counters)}
        if not unique or stored!=unique or counters['terminal_errors']:raise ValueError('Ingestion/replay count mismatch')

        # Real log evaluation creates the incident and durable pending delivery.
        # The sender is deliberately stubbed so this never contacts Slack.
        initial_alert="""import json,time
from unittest.mock import patch
from montralog import notifications as n,storage,secret_store
with storage.database() as db:
 db.execute('INSERT INTO notification_channels VALUES (?,?,?,?,?,?)',('soak-channel','Soak fixture','slack',secret_store.seal('https://hooks.slack.com/services/FIXTURE/ONLY/not-a-secret'),1,time.time()))
 db.execute('INSERT INTO alert_rules VALUES (?,?,?,?,?)',('soak-rule','Synthetic error count',json.dumps({'source':'logs','service':'reliability-soak','environment':'synthetic','op':'gt','threshold':0,'for_seconds':0,'channels':['soak-channel']}),1,time.time()))
with patch.object(n,'send_slack',side_effect=OSError('injected test failure')): n.tick()
with storage.database() as db:
 row=dict(db.execute('SELECT * FROM notification_outbox').fetchone())
 assert row['status']=='pending' and row['attempts']==1
 assert db.execute("SELECT last_known_state FROM alert_states WHERE rule_id='soak-rule'").fetchone()[0]=='firing'
print(json.dumps({'state':'pending','attempts':1,'incident':'firing'}))
"""
        report['stage']='persist_firing_alert_and_delivery_failure'
        report['alert_initial']=json.loads(docker('exec',name,'python','-c',initial_alert))
        report['stage']='create_and_verify_backup'
        docker('exec',name,'python','-m','montralog','backup','--destination','/data/soak-snapshot.db')
        docker('exec',name,'python','-m','montralog','verify-backup','--source','/data/soak-snapshot.db')
        report['backup']={'created':True,'manifest_checksum_integrity_and_silo_verified':True}

        report['stage']='restart_and_replay'
        restart_started=time.monotonic()
        docker('restart','--time','10',name)
        base='http://'+docker('port',name,'8080/tcp').splitlines()[0]
        ready();before_replay=count_logs()
        for receipt,payload in replays:
            if request('/api/logs',payload,receipt).get('accepted')!=args.batch_size:raise ValueError('Restart replay acknowledgement changed')
        after_replay=count_logs()
        report['restart']={'recovery_seconds':round(time.monotonic()-restart_started,3),'before':stored,'after_restart':before_replay,
            'after_replay':after_replay,'replayed_batches':len(replays),'duplicates_added':after_replay-before_replay}
        if stored!=before_replay or stored!=after_replay:raise ValueError('Restart lost data or replay duplicated data')

        recover_alert="""import json
from unittest.mock import patch
from montralog import notifications as n,storage
with storage.database() as db:db.execute('UPDATE notification_outbox SET next_attempt=0')
with patch.object(n,'send_slack') as sender:
 n.deliver(); assert sender.call_count==1
with patch.object(n,'send_slack') as sender:
 with patch.object(n,'evaluate',return_value=(None,'backend outage')):n.tick()
 assert sender.call_count==0
 with patch.object(n,'evaluate',return_value=(0,'synthetic recovery')):n.tick()
 assert sender.call_count==1
with storage.database() as db:
 rows=[dict(r) for r in db.execute('SELECT status,attempts FROM notification_outbox ORDER BY created_at')]
 assert len(rows)==2 and all(r['status']=='sent' for r in rows)
 assert rows[0]['attempts']==2
 assert db.execute("SELECT last_known_state FROM alert_states WHERE rule_id='soak-rule'").fetchone()[0]=='normal'
print(json.dumps({'worker_process_recovery':True,'firing_then_resolution':True,'deliveries':rows,'external_sender':'stubbed','retry_deadline':'advanced in fixture'}))
"""
        report['stage']='alert_worker_outage_and_resolution_recovery'
        report['alert_recovery']=json.loads(docker('exec',name,'python','-c',recover_alert))
        report['stage']='restore_snapshot_to_new_database'
        docker('exec',name,'python','-m','montralog','restore-backup','--source','/data/soak-snapshot.db','--destination','/data/soak-restored.db')
        restored="""import json
from montralog import storage,secret_store
storage.initialize()
with storage.database() as db:
 count=db.execute('SELECT COUNT(*) FROM logs').fetchone()[0]
 row=dict(db.execute('SELECT * FROM notification_outbox').fetchone())
 assert row['status']=='pending' and row['attempts']==1
 assert db.execute("SELECT last_known_state FROM alert_states WHERE rule_id='soak-rule'").fetchone()[0]=='firing'
 assert db.execute('SELECT COUNT(*) FROM ingest_receipts').fetchone()[0]>0
 assert secret_store.verify_existing()['encrypted']==1
print(json.dumps({'restored_logs':count,'encrypted_credentials_verified':True,'pending_delivery_restored':True,'idempotency_receipts_restored':True}))
"""
        report['restore']=json.loads(docker('exec',name,'env','MONTRALOG_DB=/data/soak-restored.db','python','-c',restored))
        if report['restore']['restored_logs']!=stored:raise ValueError('Restored snapshot record count differs')
        wrong_silo=subprocess.run(['docker','exec','-e','MONTRALOG_TENANT_ID=wrong-synthetic-silo',name,'python','-m','montralog','verify-backup','--source','/data/soak-snapshot.db'],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
        if wrong_silo.returncode==0:raise ValueError('Backup verification accepted a different silo')
        report['backup']['wrong_silo_rejected']=True
        report['stage']='complete'
        report['result']='PASS'
    except Exception as error:
        report['error_type']=type(error).__name__
        report['error']='Disposable acceptance probe failed; inspect the named stage and rerun in staging.'
    finally:
        stop.set()
        for kind,resource in (('container',name),('volume',volume)):
            probe=subprocess.run(['docker',kind,'inspect','--format','{{index .Config.Labels "montralog.soak_run"}}' if kind=='container' else '{{index .Labels "montralog.soak_run"}}',resource],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
            if probe.returncode!=0:cleanup[kind]=True
            elif probe.stdout.strip()==nonce:
                result=subprocess.run(['docker',kind,'rm',*(['-f'] if kind=='container' else []),resource],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
                cleanup[kind]=result.returncode==0
        report['cleanup']=cleanup
        if not all(cleanup.values()):report['result']='FAIL';report['cleanup_error']='Disposable resource cleanup was not confirmed.'
        output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    return 0 if report['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
