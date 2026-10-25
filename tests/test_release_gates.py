import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_security_report import validate_report


class SecurityGateTests(unittest.TestCase):
    def setUp(self):
        self.report = {'Metadata': {'OS': {'Family': 'alpine', 'Name': 'supported', 'EOSL': False}}, 'Results': [
            {'Class': 'os-pkgs', 'Type': 'alpine', 'Packages': [{'Name': 'musl'}]},
            {'Class': 'lang-pkgs', 'Type': 'python-pkg', 'Packages': [{'Name': name} for name in ('gunicorn', 'cryptography', 'joserfc', 'psycopg')]}]}

    def test_zero_findings_requires_real_package_inventories(self):
        self.assertEqual(validate_report(self.report)['result'], 'PASS')
        self.report['Results'][0]['Packages'] = []
        with self.assertRaises(ValueError): validate_report(self.report)

    def test_unfixed_high_and_critical_cannot_be_hidden(self):
        for severity in ('HIGH', 'CRITICAL'):
            report = copy.deepcopy(self.report)
            report['Results'][0]['Vulnerabilities'] = [{'Severity': severity, 'FixedVersion': ''}]
            with self.subTest(severity=severity), self.assertRaises(ValueError): validate_report(report)

    def test_unsupported_or_incomplete_scans_fail_closed(self):
        for change in ('os', 'eol', 'python'):
            report = copy.deepcopy(self.report)
            if change == 'os': report['Metadata']['OS']['Family'] = 'unknown'
            if change == 'eol': report['Metadata']['OS']['EOSL'] = True
            if change == 'python': report['Results'].pop()
            with self.subTest(change=change), self.assertRaises(ValueError): validate_report(report)
