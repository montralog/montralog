"""Verify anonymous GHCR pull access and the exact published manifest digest."""
import argparse
import json
import re
import time
import urllib.error
import urllib.request


def anonymous_digest(reference):
    prefix = 'ghcr.io/montralog/montralog:'
    if not reference.startswith(prefix) or not re.fullmatch(r'[0-9A-Za-z.-]+', reference[len(prefix):]):
        raise ValueError('Expected a Montralog GHCR version tag')
    with urllib.request.urlopen('https://ghcr.io/token?service=ghcr.io&scope=repository:montralog/montralog:pull', timeout=20) as response:
        token = json.load(response)['token']
    req = urllib.request.Request('https://ghcr.io/v2/montralog/montralog/manifests/' + reference[len(prefix):], method='HEAD', headers={
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.oci.image.index.v1+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json'})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.headers['Docker-Content-Digest']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', required=True)
    parser.add_argument('--digest', required=True)
    parser.add_argument('--wait-seconds', type=int, default=0)
    args = parser.parse_args()
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', args.digest): raise ValueError('Invalid digest')
    deadline = time.monotonic() + args.wait_seconds
    while True:
        try:
            actual = anonymous_digest(args.reference)
            if actual != args.digest: raise ValueError('Public manifest digest differs from the tested image')
            print('PASS: anonymous container pull is public and its manifest digest matches')
            return
        except urllib.error.HTTPError as error:
            error.close()
            if time.monotonic() >= deadline: raise SystemExit('Public container access not available; check package visibility') from None
        except OSError:
            if time.monotonic() >= deadline: raise SystemExit('Registry connection failed') from None
        print('Waiting for public package visibility...', flush=True)
        time.sleep(10)


if __name__ == '__main__': main()
