"""Provision an isolated Compose customer's private env file, never overwrite."""
import argparse
import base64
import os
from pathlib import Path
import re
import secrets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tenant', required=True)
    parser.add_argument('--http-port', required=True, type=int)
    parser.add_argument('--otlp-http-port', required=True, type=int)
    parser.add_argument('--otlp-grpc-port', required=True, type=int)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', args.tenant): parser.error('Invalid customer ID')
    ports = (args.http_port, args.otlp_http_port, args.otlp_grpc_port)
    if len(set(ports)) != 3 or not all(1024 <= p <= 65535 for p in ports): parser.error('Choose three different ports from 1024-65535')
    root = Path(__file__).resolve().parents[1]
    directory = root / '.local' / 'tenants'
    for candidate in (directory.parent, directory):
        try: candidate.mkdir(mode=0o700)
        except FileExistsError: continue
        if hasattr(os, 'geteuid') and os.geteuid() == 0:
            owner = root.stat()
            os.chown(candidate, owner.st_uid, owner.st_gid)
    for existing in directory.glob('*.env'):
        used = {int(line.split('=',1)[1]) for line in existing.read_text().splitlines() if line.startswith(('MONTRALOG_HTTP_PORT=', 'MONTRALOG_OTLP_HTTP_PORT=', 'MONTRALOG_OTLP_GRPC_PORT='))}
        if used.intersection(ports): parser.error('A port is already assigned in another customer env file')
    path = directory / (args.tenant + '.env')
    try: fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError: parser.error('Customer file already exists; credentials were preserved')
    if hasattr(os, 'geteuid') and os.geteuid() == 0:
        owner = root.stat()
        os.fchown(fd, owner.st_uid, owner.st_gid)
    values = {'COMPOSE_PROJECT_NAME':'montralog-'+args.tenant, 'MONTRALOG_TENANT_ID':args.tenant,
        'MONTRALOG_HTTP_PORT':args.http_port,'MONTRALOG_OTLP_HTTP_PORT':args.otlp_http_port,'MONTRALOG_OTLP_GRPC_PORT':args.otlp_grpc_port,
        'MONTRALOG_READ_TOKEN':'mtls1.'+args.tenant+'.read.'+secrets.token_urlsafe(36),'MONTRALOG_INGEST_TOKEN':'mtls1.'+args.tenant+'.ingest.'+secrets.token_urlsafe(36),
        'MONTRALOG_ENCRYPTION_KEY':base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
        'MONTRALOG_ENCRYPTION_REQUIRED':'true','MONTRALOG_SILO_STRICT':'true','RETENTION_DAYS':7}
    with os.fdopen(fd,'w') as output:
        output.writelines(f'{k}={v}\n' for k,v in values.items())
    print(f'Created private customer configuration: .local/tenants/{args.tenant}.env')
    print(f'Run: docker compose --env-file .local/tenants/{args.tenant}.env up -d --wait')
    print('Keep customer environment files and encryption keys private and separately backed up.')


if __name__ == '__main__': main()
