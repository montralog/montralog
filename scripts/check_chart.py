"""Render both topologies and reject unsafe combinations without a live cluster."""
import json
import os
import subprocess
from pathlib import Path
import yaml

root=Path(__file__).resolve().parents[1]
chart=root/'deploy/helm/montralog'
helm=os.getenv('HELM','helm')
def command(*args,success=True):
    result=subprocess.run([helm,*map(str,args)],capture_output=True,text=True,encoding='utf-8')
    if (result.returncode==0)!=success:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout
command('lint',chart,'--strict')
for profile in ('sqlite','postgresql'):
    args=['template','verify',chart,'--namespace','montralog-verify']
    if profile=='postgresql':
        args+=['-f',chart/'values-production.yaml']
    manifests=list(yaml.safe_load_all(command(*args)))
    manifests=[x for x in manifests if x]
    deployment=next(x for x in manifests if x['kind']=='Deployment')
    assert deployment['spec']['replicas']==(1 if profile=='sqlite' else 2)
    assert deployment['spec']['strategy']['type']==('Recreate' if profile=='sqlite' else 'RollingUpdate')
    assert not any(x['kind']=='Secret' for x in manifests),'Credentials must be operator-managed Secrets'
    if profile=='postgresql':
        encryption=next(e for e in deployment['spec']['template']['spec']['containers'][0]['env'] if e['name']=='MONTRALOG_ENCRYPTION_KEY')
        assert encryption['valueFrom']['secretKeyRef']['name']=='montralog-encryption'

    for resource in manifests:
        if resource['kind'] in ('Deployment','StatefulSet'):
            pod=resource['spec']['template']['spec']
            assert pod['automountServiceAccountToken'] is False
            for container in pod['containers']:
                assert container['securityContext']['readOnlyRootFilesystem']
                assert container['securityContext']['allowPrivilegeEscalation'] is False
                assert 'ALL' in container['securityContext']['capabilities']['drop']
                assert container['resources']['requests']
    if profile=='postgresql':
        assert any(x['kind']=='PodDisruptionBudget' for x in manifests)
        assert any(x['kind']=='CronJob' for x in manifests)
    output=root/'work'/'chart-validation'/profile
    output.mkdir(parents=True,exist_ok=True)
    for resource in manifests:
        if resource['kind']=='ConfigMap':
            for name,value in resource.get('data',{}).items():
                (output/name).write_text(value,encoding='utf-8')
    print(f'PASS: {profile} profile; {len(manifests)} resources with security and storage assertions')
for settings in (
    ['--set','replicaCount=2'],
    ['--set','database.mode=postgresql'],
    ['--set','persistence.enabled=false'],
    ['--set','ingress.enabled=true'],
    ['--set','prometheus.enabled=false'],
    ['--set','retentionDays=0'],
    ['--set','database.mode=invalid'],
    ['--set','encryption.existingSecret='],
):
    command('template','invalid',chart,*settings,success=False)
print('PASS: eight unsafe/invalid chart configurations were rejected')
