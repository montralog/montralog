"""Scan every bundled chart backend and retain all findings; reject unapproved HIGH/CRITICAL."""
import argparse
import json
from pathlib import Path
import subprocess
import yaml

TRIVY = 'aquasec/trivy:0.76.2@sha256:8f6bb947dbc528902e11f2f5be52f7b519f6a39d5d148f41166f2040499768fb'


def summarize(report):
    results = report.get('Results', [])
    if not any(r.get('Packages') for r in results):
        raise ValueError('Scan must include a nonempty package inventory')
    if report.get('Metadata', {}).get('OS', {}).get('EOSL'):
        raise ValueError('Bundled image uses an unsupported operating system')
    vulnerabilities = [v for r in results for v in r.get('Vulnerabilities', []) or []]
    counts = {level: sum(v.get('Severity') == level for v in vulnerabilities)
              for level in ('UNKNOWN', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')}
    return {'result': 'FAIL' if counts['HIGH'] or counts['CRITICAL'] else 'PASS',
            'severity_counts': counts, 'total': len(vulnerabilities)}



def assess_remaining(report, image, accepted):
    result = summarize(report)
    if result['result'] == 'PASS':
        return result
    findings = [v for r in report.get('Results', []) for v in r.get('Vulnerabilities', []) or []
                if v.get('Severity') in ('HIGH', 'CRITICAL')]
    policy = accepted.get(image, {})
    matches = (policy and len(findings) <= policy.get('max_occurrences', 0)
               and all(v.get('Severity') == 'HIGH'
                       and v.get('VulnerabilityID') == policy.get('vulnerability_id')
                       and v.get('PkgName') == policy.get('package')
                       and v.get('InstalledVersion') == policy.get('installed_version')
                       for v in findings))
    if matches:
        result['result'] = 'ACCEPTED_REMAINING_HIGH'
        result['risk_acceptance'] = policy
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('security-reports/stack'))
    parser.add_argument('--cache', default='mtl-trivy-stack-cache')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    values = yaml.safe_load((root/'deploy/helm/montralog/values.yaml').read_text())
    compose = yaml.safe_load((root/'compose.yaml').read_text())
    accepted = json.loads((root/'deploy/security/accepted-upstream-findings.json').read_text())['images']
    summary = {}
    for name in ('prometheus', 'alertmanager', 'collector'):
        reference = values[name]['image']
        if '@sha256:' not in reference or compose['services'][name]['image'] != reference:
            raise ValueError('Compose/chart images must match and be pinned by digest')
        subprocess.run(['docker', 'run', '--rm', '-v', args.cache+':/root/.cache/trivy',
                        '-v', str(output)+':/reports', TRIVY, 'image', '--image-src', 'remote',
                        '--scanners', 'vuln', '--list-all-pkgs', '--format', 'json',
                        '--output', '/reports/'+name+'.json', reference], check=True)
        summary[name] = {'image': reference, **assess_remaining(json.loads((output/(name+'.json')).read_text()), reference, accepted)}
    (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))
    if any(r['result'] == 'FAIL' for r in summary.values()):
        raise SystemExit('Bundled image gate rejected new or unapproved HIGH/CRITICAL findings')


if __name__ == '__main__':
    main()
