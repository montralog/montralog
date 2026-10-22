"""Install and exercise Helm in an explicitly named disposable verification cluster.

Never targets an ambient kubeconfig. Generates only synthetic data. The caller
owns deleting the dedicated kind cluster afterwards.
"""
import argparse
import json
import os
import secrets
import subprocess
from pathlib import Path

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--kubeconfig',required=True,type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    namespace='montralog-verify'
    release='verify'
    helm=os.getenv('HELM','helm')
    kubectl=['kubectl','--kubeconfig',str(args.kubeconfig),'-n',namespace]
    def run(command,input=None,capture=False):
        result=subprocess.run(command,input=input,text=True,encoding='utf-8',capture_output=capture)
        if result.returncode:
            raise RuntimeError('Verification command failed: '+command[0]+(' '+result.stderr if capture else ''))
        return result.stdout if capture else ''
    context=run(['kubectl','--kubeconfig',str(args.kubeconfig),'config','current-context'],capture=True).strip()
    if context!='kind-montralog-verify':
        raise SystemExit('Only the disposable context kind-montralog-verify is accepted')
    def apply(obj):
        run([*kubectl,'apply','-f','-'],json.dumps(obj))
    apply({'apiVersion':'v1','kind':'Namespace','metadata':{'name':namespace}})
    auth_exists=subprocess.run([*kubectl,'get','secret','montralog-auth','-o','name'],capture_output=True).returncode==0
    if not auth_exists:
        apply({'apiVersion':'v1','kind':'Secret','metadata':{'name':'montralog-auth'},'stringData':{'read-token':secrets.token_urlsafe(36),'ingest-token':secrets.token_urlsafe(36)}})
    chart=root/'deploy/helm/montralog'
    run([helm,'upgrade','--install',release,str(chart),'--kubeconfig',str(args.kubeconfig),'--namespace',namespace,'--wait','--timeout','4m'])
    gateway='deployment/verify-montralog'
    def exec_gateway(*command):
        run([*kubectl,'exec',gateway,'-c','gateway','--',*command])
    exec_gateway('env','MONTRALOG_REQUIRE_PROMETHEUS=1','python','scripts/smoke.py')
    exec_gateway('env','OTEL_SMOKE_URL=http://verify-montralog-collector:4318','python','scripts/collector_smoke.py')
    # Pod restart must preserve SQLite telemetry on its PVC.
    run([*kubectl,'rollout','restart',gateway])
    run([*kubectl,'rollout','status',gateway,'--timeout=120s'])
    exec_gateway('python','-c',"from montralog.queries import query_view; assert query_view('overview',{'environment':'smoke'})['totals']['logs']>=2; print('PASS: telemetry persisted across Kubernetes pod restart')")
    print('PASS: Helm install, probes, services, PVC, OTLP pipeline and pod restart.',flush=True)

    # Exercise the two-replica production database topology with an ephemeral DB.
    password=secrets.token_urlsafe(32)
    apply({'apiVersion':'v1','kind':'Secret','metadata':{'name':'verification-postgres'},'stringData':{'password':password}})
    apply({'apiVersion':'apps/v1','kind':'Deployment','metadata':{'name':'verification-postgres'},'spec':{
        'replicas':1,'selector':{'matchLabels':{'app':'verification-postgres'}},'template':{
            'metadata':{'labels':{'app':'verification-postgres'}},'spec':{'automountServiceAccountToken':False,
            'containers':[{'name':'postgres','image':'postgres:17.6-alpine','env':[
                {'name':'POSTGRES_PASSWORD','valueFrom':{'secretKeyRef':{'name':'verification-postgres','key':'password'}}},
                {'name':'POSTGRES_DB','value':'montralog_test'}],
                'ports':[{'containerPort':5432}],
                'readinessProbe':{'exec':{'command':['pg_isready','-U','postgres','-d','montralog_test']},'periodSeconds':3},
                'resources':{'requests':{'cpu':'100m','memory':'128Mi'},'limits':{'cpu':'1','memory':'512Mi'}}}]}}}})
    apply({'apiVersion':'v1','kind':'Service','metadata':{'name':'verification-postgres'},'spec':{
        'selector':{'app':'verification-postgres'},'ports':[{'port':5432,'targetPort':5432}]}})
    run([*kubectl,'rollout','status','deployment/verification-postgres','--timeout=180s'])
    apply({'apiVersion':'v1','kind':'Secret','metadata':{'name':'montralog-database'},'stringData':{
        'database-url':f'postgresql://postgres:{password}@verification-postgres:5432/montralog_test'}})
    run([helm,'upgrade',release,str(chart),'--kubeconfig',str(args.kubeconfig),'--namespace',namespace,
         '--set','database.mode=postgresql','--set','database.existingSecret=montralog-database',
         '--set','replicaCount=2','--set','persistence.enabled=false','--wait','--timeout','4m'])
    exec_gateway('env','MONTRALOG_REQUIRE_PROMETHEUS=1','python','scripts/smoke.py')
    pods=json.loads(run([*kubectl,'get','pods','-l','app.kubernetes.io/component=gateway','-o','json'],capture=True))['items']
    active=[p for p in pods if not p['metadata'].get('deletionTimestamp')]
    assert len(active)==2,'Expected two PostgreSQL gateway replicas'
    for pod in active:
        run([*kubectl,'exec',pod['metadata']['name'],'-c','gateway','--','python','-c',
             "from montralog.queries import query_view; assert query_view('overview',{'environment':'smoke'})['totals']['logs']>=1; print('PASS: PostgreSQL telemetry readable on gateway replica')"])
    run([*kubectl,'rollout','restart',gateway])
    run([*kubectl,'rollout','status',gateway,'--timeout=180s'])
    exec_gateway('python','scripts/smoke.py')
    print('PASS: PostgreSQL chart topology, shared data on two replicas and rolling pod restart.',flush=True)

if __name__=='__main__':
    main()
