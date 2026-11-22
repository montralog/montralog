import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from check_stack_security import summarize, assess_remaining

class StackSecurityTests(unittest.TestCase):
    def report(self, severity='LOW'):
        return {'Results': [{'Packages': [{'Name': 'fixture'}], 'Vulnerabilities': [{'Severity': severity}]}]}
    def test_unfixed_critical_and_high_are_rejected(self):
        for severity in ('HIGH', 'CRITICAL'):
            self.assertEqual(summarize(self.report(severity))['result'], 'FAIL')
    def test_low_is_retained_and_not_hidden(self):
        result = summarize(self.report())
        self.assertEqual(result['result'], 'PASS')
        self.assertEqual(result['severity_counts']['LOW'], 1)
        self.assertEqual(result['total'], 1)
    def test_empty_inventory_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'inventory'):
            summarize({'Results': []})
    def test_end_of_life_os_is_rejected(self):
        report=self.report();report['Metadata']={'OS': {'EOSL': True}}
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            summarize(report)

    def test_acceptance_is_limited_to_exact_digest_cve_package_and_count(self):
        image='vendor/component@sha256:exact'
        policy={image: {'vulnerability_id': 'CVE-fixture', 'package': 'golang.org/x/net', 'installed_version': 'v0.61.0', 'max_occurrences': 2}}
        finding={'Severity': 'HIGH', 'VulnerabilityID': 'CVE-fixture', 'PkgName': 'golang.org/x/net', 'InstalledVersion': 'v0.61.0'}
        report={'Results': [{'Packages': [{'Name': 'fixture'}], 'Vulnerabilities': [finding]}]}
        accepted=assess_remaining(report,image,policy)
        self.assertEqual(accepted['result'],'ACCEPTED_REMAINING_HIGH')
        self.assertEqual(accepted['severity_counts']['HIGH'],1)
        self.assertEqual(assess_remaining(report,'vendor/component@sha256:different',policy)['result'],'FAIL')
        for field,value in [('Severity','CRITICAL'),('VulnerabilityID','CVE-new'),('PkgName','other'),('InstalledVersion','v0.60.0')]:
            changed={**finding,field:value}
            bad={'Results': [{'Packages': [{'Name': 'fixture'}], 'Vulnerabilities': [changed]}]}
            self.assertEqual(assess_remaining(bad,image,policy)['result'],'FAIL')
        report['Results'][0]['Vulnerabilities']=[finding]*3
        self.assertEqual(assess_remaining(report,image,policy)['result'],'FAIL')
