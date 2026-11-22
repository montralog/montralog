import io
from pathlib import Path
import sys
import tarfile
import unittest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from chart_publication import validate_chart_image, mark_retired


def archive(image):
    data = yaml.safe_dump({'image': image}).encode()
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w:gz') as package:
        member = tarfile.TarInfo('montralog/values.yaml')
        member.size = len(data)
        package.addfile(member, io.BytesIO(data))
    return output.getvalue()


class ChartPublicationTests(unittest.TestCase):
    def test_unqualified_rc_image_is_rejected_before_lookup(self):
        def unexpected(_):
            self.fail('Invalid registry should not be queried')
        with self.assertRaisesRegex(ValueError, 'public ghcr.io'):
            validate_chart_image(archive({'repository': 'montralog', 'tag': '0.5.1-rc1'}), unexpected)

    def test_missing_public_image_blocks_publication(self):
        def unavailable(_):
            raise OSError('Registry manifest unavailable')
        with self.assertRaisesRegex(OSError, 'unavailable'):
            validate_chart_image(archive({'repository': 'ghcr.io/montralog/montralog', 'tag': 'missing'}), unavailable)

    def test_digest_mismatch_blocks_publication(self):
        with self.assertRaisesRegex(ValueError, 'digest differs'):
            validate_chart_image(archive({'repository': 'ghcr.io/montralog/montralog', 'tag': '0.8.1', 'digest': 'sha256:wrong'}), lambda _: 'sha256:actual')

    def test_valid_public_image_and_digest(self):
        result = validate_chart_image(archive({'repository': 'ghcr.io/montralog/montralog', 'tag': '0.8.1', 'digest': 'sha256:actual'}), lambda _: 'sha256:actual')
        self.assertEqual(result, ('ghcr.io/montralog/montralog:0.8.1', 'sha256:actual'))

    def test_retirement_preserves_archive_identity_and_supported_entry(self):
        old = {'version': '0.5.1-rc.1', 'digest': 'original', 'urls': ['original.tgz']}
        current = {'version': '0.8.1', 'description': 'Current'}
        result = mark_retired({'entries': {'montralog': [old, current]}})
        self.assertTrue(result['entries']['montralog'][0]['deprecated'])
        self.assertEqual(old['digest'], 'original')
        self.assertEqual(old['urls'], ['original.tgz'])
        self.assertEqual(current, {'version': '0.8.1', 'description': 'Current'})
