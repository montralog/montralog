"""Create a private key env file without printing or replacing the key."""
import argparse
import base64
import os
from pathlib import Path
import secrets

parser = argparse.ArgumentParser()
parser.add_argument('--destination', type=Path, default=Path('.local/encryption.env'))
args = parser.parse_args()
args.destination.parent.mkdir(parents=True, exist_ok=True)
fd = os.open(args.destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
with os.fdopen(fd, 'w') as output:
    output.write('MONTRALOG_ENCRYPTION_KEY=' + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('ascii') + '\n')
    output.write('MONTRALOG_ENCRYPTION_REQUIRED=true\n')
print('Created private encryption configuration at ' + str(args.destination))
print('Back it up separately from the database. Restrict Windows ACLs. Never commit it.')
