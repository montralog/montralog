"""Disposable synthetic SQLite log-query benchmark; never use an operator database."""
import argparse
import json
import os
from pathlib import Path
import platform
import sqlite3
import statistics
import sys
import time


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--records',type=int,default=100000)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--existing-synthetic',action='store_true')
    args=parser.parse_args()
    if (args.existing_synthetic and not args.database.is_file()) or (args.database.exists() and not args.existing_synthetic) or not 1000<=args.records<=10000000:
        raise SystemExit('Use a new disposable database and 1,000–10,000,000 records')
    args.database.parent.mkdir(parents=True,exist_ok=True)
    os.environ.update(MONTRALOG_DATABASE_URL='',MONTRALOG_TENANT_ID='query-benchmark',MONTRALOG_SILO_STRICT='false',MONTRALOG_ENCRYPTION_KEY='')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
    from montralog import storage
    from montralog.queries import query_view
    storage.DB=args.database.resolve()
    seed_seconds=None
    if args.existing_synthetic:
        with sqlite3.connect(args.database) as db:
            identity=db.execute('SELECT tenant_id FROM deployment_identity WHERE id=1').fetchone()
            fixture=db.execute('SELECT message FROM logs LIMIT 1').fetchone()
            maximum=db.execute('SELECT MAX(id) FROM logs').fetchone()[0]
            if identity!=('query-benchmark',) or fixture!=('Synthetic benchmark record',) or maximum!=args.records:
                raise SystemExit('Existing file is not the expected synthetic benchmark dataset')
    else:
        storage.initialize()
        anchor=time.time()
        start=time.perf_counter()
        with sqlite3.connect(args.database) as db:
            for first in range(0,args.records,100000):
                count=min(100000,args.records-first)
                db.execute("""WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i+1 FROM n WHERE i<?)
                INSERT INTO logs(id,time,received,service,environment,severity,message,pattern,trace_id,attributes)
                SELECT ?+i,?-((?-i)*0.001),?,'service-'||((?+i)%100),'benchmark',
                CASE WHEN i%20=0 THEN 'ERROR' ELSE 'INFO' END,
                'Synthetic benchmark record','Synthetic benchmark record','','{}' FROM n""",
                (count,first,anchor,args.records-first,anchor,first))
                db.commit()
                print('Seeded',first+count,flush=True)
        seed_seconds=time.perf_counter()-start
    baseline_started=time.perf_counter()
    try:
        with storage.database() as db:
            cutoff=time.time()-10080*60
            list(db.execute('SELECT * FROM logs WHERE time>=? ORDER BY time DESC,id DESC LIMIT 100 OFFSET 0',(cutoff,)))
            db.execute('SELECT COUNT(*) FROM logs WHERE time>=?',(cutoff,)).fetchone()
        baseline={'status':'complete','ms':(time.perf_counter()-baseline_started)*1000}
    except storage.StorageError:
        baseline={'status':'database_deadline_exceeded','ms':(time.perf_counter()-baseline_started)*1000}
    measurements=[]
    for _ in range(10):
        start=time.perf_counter()
        result=query_view('logs',{'minutes':'10080'})
        measurements.append((time.perf_counter()-start)*1000)
        assert len(result['items'])==100 and result['has_more']
    report={'scope':'Synthetic local SQLite query path only. Direct SQL seeding is not ingestion throughput. No sustained capacity or multi-user guarantee.',
            'records':args.records,'seed_seconds':seed_seconds,'database_bytes':args.database.stat().st_size,
            'platform':platform.system(),'python':platform.python_version(),'query_runs':len(measurements),
            'legacy_count_query':baseline,'first_page_ms':measurements,'median_ms':statistics.median(measurements),'max_ms':max(measurements)}
    cursor=result['next_cursor']
    following=[]
    seen=set(row['id'] for row in result['items'])
    for _ in range(min(100,(args.records-1)//100)):
        start=time.perf_counter()
        page=query_view('logs',{'minutes':'10080','cursor':cursor})
        following.append((time.perf_counter()-start)*1000)
        ids=set(row['id'] for row in page['items'])
        assert not seen & ids
        seen.update(ids)
        cursor=page['next_cursor']
    report['following_pages']={'count':len(following),'records_verified_unique':len(seen),'median_ms':statistics.median(following),'max_ms':max(following)}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
