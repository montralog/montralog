"""Fail closed for unrecognized/incomplete scans or any HIGH/CRITICAL finding."""
import argparse
import json
from pathlib import Path


def validate_report(report):
    os = report.get('Metadata', {}).get('OS', {})
    if os.get('Family') != 'alpine' or os.get('EOSL'):
        raise ValueError('Expected a supported Alpine runtime scan')
    results = report.get('Results', [])
    os_packages = [p for r in results if r.get('Class') == 'os-pkgs' and r.get('Type') == 'alpine' for p in r.get('Packages', [])]
    python_packages = {p.get('Name') for r in results if r.get('Type') == 'python-pkg' for p in r.get('Packages', [])}
    if not os_packages or not {'gunicorn', 'cryptography', 'joserfc', 'psycopg'} <= python_packages:
        raise ValueError('Scan must include OS and application Python package inventories')
    findings = [v for r in results for v in (r.get('Vulnerabilities') or []) if v.get('Severity') in ('HIGH', 'CRITICAL')]
    if findings:
        raise ValueError(f'Security gate rejected {len(findings)} HIGH/CRITICAL findings, including unfixed findings')
    return {'result': 'PASS', 'os': os.get('Name'), 'os_packages': len(os_packages),
            'python_packages': len(python_packages), 'high': 0, 'critical': 0,
            'severity_counts': {level: sum(v.get('Severity') == level for r in results for v in (r.get('Vulnerabilities') or [])) for level in ('UNKNOWN','LOW','MEDIUM','HIGH','CRITICAL')},
            'scope': 'Scanner snapshot for this image; not an independent security audit'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    parser.add_argument('--summary', type=Path)
    args = parser.parse_args()
    summary = validate_report(json.loads(args.report.read_text()))
    text = json.dumps(summary, indent=2)
    if args.summary: args.summary.write_text(text + '\n')
    print(text)


if __name__ == '__main__': main()
