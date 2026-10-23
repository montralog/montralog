"""Import a platform-specific local image into the disposable kind node.

Works around Docker OCI indexes containing unavailable other-platform
or attestation content. Requires Docker with image save --platform support.
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--image',default='montralog:0.5.1-rc1')
args=parser.parse_args()
node='montralog-verify-control-plane'
root=Path(__file__).resolve().parents[1]/'work'
root.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=root) as tmp:
    archive=Path(tmp)/'gateway.tar'
    subprocess.run(['docker','image','save','--platform=linux/amd64','-o',str(archive),args.image],check=True)
    with archive.open('rb') as data:
        subprocess.run(['docker','exec','-i',node,'ctr','--namespace=k8s.io','images','import','--platform','linux/amd64','-'],stdin=data,check=True)
print(f'{args.image} imported into disposable verification node')
