"""Reproducible Docker-only acceptance probe using disposable synthetic data."""
import argparse
import concurrent.futures
import datetime
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import urllib.error
import urllib.request


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True, stderr=subprocess.STDOUT).strip()


def percentile(values, fraction):
    values = sorted(values)
    return round(values[min(len(values)-1, int((len(values)-1)*fraction))], 3) if values else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', default='montralog:acceptance')
    parser.add_argument('--output', default='work/acceptance/load.json')
    parser.add_argument('--batches', type=int, default=100)
    parser.add_argument('--batch-size', type=int, default=100)
    parser.add_argument('--clients', type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.batches <= 10000 or not 1 <= args.batch_size <= 1000 or not 1 <= args.clients <= 64:
        parser.error('Bounded workload required: batches 1-10000, batch-size 1-1000, clients 1-64')
    suffix = secrets.token_hex(8)
    name, volume = 'mtl-acceptance-'+suffix, 'mtl-acceptance-data-'+suffix
    read, ingest = ('mtls1.acceptance-'+suffix+'.'+scope+'.'+secrets.token_urlsafe(40) for scope in ('read','ingest'))
    import base64
    key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    report = {'result': 'FAIL', 'image': args.image, 'platform': 'Docker Linux containers',
              'started_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'container_limits':{'cpus':1,'memory_mib':512,'pids':128},
              'workload': {'batches':args.batches,'batch_size':args.batch_size,'clients':args.clients},
              'limits': ['Synthetic local workload, not an organization capacity guarantee.',
                         'Gateway restart and SQLite write-lock injection; not PostgreSQL failover.',
                         'Slack delivery is stubbed; retry deadlines are advanced, no external messages sent.']}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    try:
        docker('volume', 'create', '--label', 'montralog.disposable=acceptance', volume)
        docker('run', '-d', '--name', name, '--label', 'montralog.disposable=acceptance',
               '--cpus', '1', '--memory', '512m', '--pids-limit', '128', '--read-only', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges:true', '--tmpfs', '/tmp:rw,nosuid,noexec,size=64m,mode=1777',
               '-p', '127.0.0.1::8080', '-v', volume+':/data',
               '-e', 'MONTRALOG_TENANT_ID=acceptance-'+suffix,
               '-e', 'MONTRALOG_READ_TOKEN='+read, '-e', 'MONTRALOG_INGEST_TOKEN='+ingest,
               '-e', 'MONTRALOG_ENCRYPTION_KEY='+key, args.image)
        base = 'http://'+docker('port', name, '8080/tcp').splitlines()[0]
        retry_count = 0
        def request(path, records=None, retries=0):
            nonlocal retry_count
            for attempt in range(retries+1):
                req = urllib.request.Request(base+path, data=json.dumps(records).encode() if records is not None else None,
                    headers={'Content-Type':'application/json','Authorization':'Bearer '+(ingest if records is not None else read)})
                try:
                    with urllib.request.urlopen(req, timeout=25) as response: return json.load(response)
                except urllib.error.HTTPError as error:
                    code = error.code; error.close()
                    if code not in (429,503) or attempt == retries: raise
                    retry_count += 1
                    time.sleep(min(1, .1 * 2**attempt))
        def ready():
            deadline = time.monotonic()+60
            while time.monotonic() < deadline:
                try:
                    request('/health/ready'); return
                except (OSError, ValueError): time.sleep(.2)
            raise RuntimeError('Temporary gateway did not become ready')
        ready()
        image_id = docker('image', 'inspect', args.image, '--format', '{{.Id}}')
        report['image_id'] = image_id
        report['source_revision'] = docker('image','inspect',args.image,'--format','{{index .Config.Labels "org.opencontainers.image.revision"}}')
        queries = []
        def batch(index):
            records = [{'service':'acceptance','environment':'synthetic','severity':'ERROR',
                        'message':f'Fixture batch {index} event {event}'} for event in range(args.batch_size)]
            started = time.perf_counter()
            result = request('/api/logs', records)
            assert result['accepted'] == args.batch_size
            elapsed = (time.perf_counter()-started)*1000
            if index % 5 == 0:
                start = time.perf_counter(); request('/api/logs?service=acceptance&limit=50')
                queries.append((time.perf_counter()-start)*1000)
            return elapsed
        started = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.clients) as pool:
            latencies = list(pool.map(batch, range(args.batches)))
        duration = time.perf_counter()-started
        expected = args.batches*args.batch_size
        observed = request('/api/overview')['totals']['logs']
        report['ingestion'] = {'acknowledged':expected,'stored':observed,'missing':expected-observed,
            'elapsed_seconds':round(duration,3),'events_per_second':round(expected/duration,2),
            'batch_latency_ms':{'p50':percentile(latencies,.5),'p95':percentile(latencies,.95),'max':round(max(latencies),3)},
            'concurrent_query_latency_ms':{'count':len(queries),'p50':percentile(queries,.5),'p95':percentile(queries,.95)},
            'request_errors':0}
        assert observed == expected
        # Force a real write timeout. Reads remain available under WAL; the
        # client retries only an explicit failed (503) transactional write.
        lock_code = "import sqlite3,time; c=sqlite3.connect('/data/montralog.db'); c.execute('BEGIN IMMEDIATE'); open('/tmp/lock-ready','w').close(); time.sleep(8); c.rollback()"
        docker('exec', '-d', name, 'python', '-c', lock_code)
        for _ in range(50):
            if docker('exec', name, 'python', '-c', "from pathlib import Path; print(Path('/tmp/lock-ready').exists())") == 'True': break
            time.sleep(.1)
        else: raise RuntimeError('Write-lock injection did not start')
        recovered = request('/api/logs', [{'service':'acceptance','message':'after explicit storage failure'}], retries=8)
        assert recovered['accepted'] == 1 and retry_count >= 1
        report['write_failure'] = {'explicit_503_retries':retry_count,'recovered':True}
        before = request('/api/overview')['totals']['logs']
        started = time.perf_counter(); docker('restart', '--time', '10', name)
        base = 'http://'+docker('port', name, '8080/tcp').splitlines()[0]
        ready()
        after = request('/api/overview')['totals']['logs']
        assert before == after == expected+1
        report['restart'] = {'recovery_seconds':round(time.perf_counter()-started,3),'stored_before':before,'stored_after':after,'missing':before-after}
        # Persist a log alert and encrypted channel; two independent worker
        # processes fail then recover without contacting a real Slack channel.
        setup = """import json,time
from unittest.mock import patch
from montralog import notifications as n,storage,secret_store
with storage.database() as db:
 db.execute('INSERT INTO notification_channels VALUES (?,?,?,?,?,?)',('fixture','Fixture','slack',secret_store.seal('https://hooks.slack.com/services/FIXTURE/TEST/secret'),1,time.time()))
 db.execute('INSERT INTO alert_rules VALUES (?,?,?,?,?)',('fixture-rule','Synthetic errors',json.dumps({'source':'logs','op':'gt','threshold':0,'for_seconds':0,'channels':['fixture']}),1,time.time()))
with patch.object(n,'send_slack',side_effect=OSError('injected failure')): n.tick()
with storage.database() as db:
 row=dict(db.execute('SELECT * FROM notification_outbox').fetchone())
 assert row['status']=='pending' and row['attempts']==1
 assert 25<=row['next_attempt']-time.time()<=31
 db.execute('UPDATE notification_outbox SET next_attempt=0')
print(json.dumps({'state':'pending','attempts':1,'initial_backoff_seconds':30}))
"""
        failed = json.loads(docker('exec', name, 'python', '-c', setup))
        recovery = """import json
from unittest.mock import patch
from montralog import notifications as n,storage
with patch.object(n,'send_slack',side_effect=OSError('second injected failure')): n.deliver()
with storage.database() as db:
 row=dict(db.execute('SELECT * FROM notification_outbox').fetchone())
 assert row['status']=='pending' and row['attempts']==2
 assert 55<=row['next_attempt']-n.time.time()<=61
 db.execute('UPDATE notification_outbox SET next_attempt=0')
with patch.object(n,'send_slack') as sender:
 n.deliver(); assert sender.call_count==1
with storage.database() as db:
 row=dict(db.execute('SELECT * FROM notification_outbox').fetchone())
 assert row['status']=='sent' and row['attempts']==3
 assert db.execute("SELECT state FROM alert_states WHERE rule_id='fixture-rule'").fetchone()[0]=='firing'
print(json.dumps({'state':'sent','attempts':3,'second_backoff_seconds':60,'worker_process_recovery':True}))
"""
        report['alerting'] = {'initial_failure':failed,'recovery':json.loads(docker('exec', name, 'python', '-c', recovery)), 'external_delivery':'stubbed'}
        report['result'] = 'PASS'
    except Exception as error:
        report['error_type'] = type(error).__name__
        try: report['temporary_container_log'] = docker('logs', '--tail', '40', name)
        except subprocess.CalledProcessError: pass
        raise
    finally:
        output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        subprocess.run(['docker','rm','-f',name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        subprocess.run(['docker','volume','rm',volume], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
