"""Offline silo audit and non-destructive credential upgrade. Never print secrets."""
import argparse
import base64
import os
from pathlib import Path
import re
import secrets


def read_env(path):
    values={}
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):continue
        if '=' not in line:raise ValueError('Expected simple KEY=value configuration')
        key,value=line.split('=',1)
        if not re.fullmatch('[A-Z][A-Z0-9_]*',key) or key in values:raise ValueError('Invalid or duplicate setting')
        values[key]=value
    return values


def audit(paths):
    seen={};ports=set()
    for path in paths:
        values=read_env(path)
        for key in ('MONTRALOG_TENANT_ID','COMPOSE_PROJECT_NAME','MONTRALOG_READ_TOKEN','MONTRALOG_INGEST_TOKEN','MONTRALOG_ENCRYPTION_KEY'):
            value=values.get(key,'')
            if not value:raise ValueError('A required silo setting is missing: '+key)
            identity=(key,value)
            if identity in seen:raise ValueError('Customer configurations reuse '+key)
            seen[identity]=True
        if values.get('MONTRALOG_DATABASE_URL'):raise ValueError('Docker silo audit requires separate local databases')
        tenant=values['MONTRALOG_TENANT_ID']
        for scope in ('read','ingest'):
            token=values['MONTRALOG_'+scope.upper()+'_TOKEN']
            if not re.fullmatch(re.escape('mtls1.'+tenant+'.'+scope+'.')+r'[A-Za-z0-9_-]{43,128}',token):raise ValueError('A machine token is not customer bound')
        if values.get('MONTRALOG_SILO_STRICT')!='true':raise ValueError('Strict silo mode is required')
        if len(base64.urlsafe_b64decode(values['MONTRALOG_ENCRYPTION_KEY']))!=32:raise ValueError('Invalid encryption key')
        for key in ('MONTRALOG_HTTP_PORT','MONTRALOG_OTLP_HTTP_PORT','MONTRALOG_OTLP_GRPC_PORT'):
            port=int(values[key])
            if not 1024<=port<=65535 or port in ports:raise ValueError('Customer port allocation overlaps or is invalid')
            ports.add(port)
    return len(paths)


def upgrade(source,destination):
    values=read_env(source)
    tenant=values.get('MONTRALOG_TENANT_ID','default')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}',tenant):raise ValueError('Invalid existing customer ID')
    if not values.get('MONTRALOG_ENCRYPTION_KEY'):raise ValueError('Restore the existing encryption key before upgrading')
    values['MONTRALOG_TENANT_ID']=tenant
    for scope in ('read','ingest'):
        values['MONTRALOG_'+scope.upper()+'_TOKEN']='mtls1.'+tenant+'.'+scope+'.'+secrets.token_urlsafe(36)
    values['MONTRALOG_SILO_STRICT']='true'
    values['MONTRALOG_ENCRYPTION_REQUIRED']='true'
    fd=os.open(destination,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w') as out:out.writelines(k+'='+v+'\n' for k,v in values.items())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    check=sub.add_parser('audit');check.add_argument('--directory',type=Path,default=Path('.local/tenants'))
    migrate=sub.add_parser('upgrade');migrate.add_argument('--source',required=True,type=Path);migrate.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    try:
        if args.command=='audit':
            paths=list(args.directory.glob('*.env'))
            if not paths:raise ValueError('No customer configurations found')
            print('PASS: '+str(audit(paths))+' distinct customer configurations; no secret values displayed')
        else:
            upgrade(args.source,args.output)
            print('Created a new private configuration. Existing key and customer ID preserved; machine tokens rotated. Update producers and reissue old managed API tokens before enabling strict mode.')
    except (ValueError,OSError,KeyError):raise SystemExit('Silo check failed. Check required settings, unique IDs/keys/tokens/projects/ports and private file access; existing files were preserved.') from None

if __name__=='__main__':main()
