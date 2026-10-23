"""Retain published chart archives and add an immutable GitHub release package."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import yaml

BASE = 'https://montralog.github.io/montralog/'
parser = argparse.ArgumentParser()
parser.add_argument('--release', required=True)
args = parser.parse_args()
if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:-rc[0-9]+)?', args.release):
    raise SystemExit('Expected an explicit versioned release tag')
public = Path('public')
public.mkdir(exist_ok=True)
try:
    with urllib.request.urlopen(BASE + 'index.yaml', timeout=30) as response:
        index = yaml.safe_load(response.read(1024 * 1024))
except urllib.error.HTTPError as error:
    if error.code != 404:
        raise
    index = {'entries': {}}
for entry in index.get('entries', {}).get('montralog', []):
    name = 'montralog-' + entry['version'] + '.tgz'
    if not re.fullmatch(r'montralog-[0-9A-Za-z.-]+\.tgz', name):
        raise ValueError('Unexpected chart filename')
    with urllib.request.urlopen(BASE + name, timeout=30) as response:
        archive = response.read(16 * 1024 * 1024)
    if hashlib.sha256(archive).hexdigest() != entry['digest']:
        raise ValueError('Published chart digest mismatch')
    (public / name).write_bytes(archive)
# Download into a separate directory so previous versions can never be overwritten.
import tempfile
with tempfile.TemporaryDirectory() as temporary:
    subprocess.run(['gh', 'release', 'download', args.release, '--pattern', 'montralog-*.tgz', '--dir', temporary], check=True)
    for archive in Path(temporary).glob('*.tgz'):
        target = public / archive.name
        if target.exists() and target.read_bytes() != archive.read_bytes():
            raise ValueError('Refusing to replace an existing chart version')
        target.write_bytes(archive.read_bytes())
subprocess.run(['helm', 'repo', 'index', str(public), '--url', BASE.rstrip('/')], check=True)
(public / 'artifacthub-repo.yml').write_bytes(Path('deploy/helm/artifacthub-repo.yml').read_bytes())
(public / '.nojekyll').touch()
print('Prepared Helm repository while retaining previous chart versions')
