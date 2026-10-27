"""Bundled legal texts must travel with the application without changing Apache."""
import io
from pathlib import Path
import unittest
from montralog.http import application

class BundledNoticesTests(unittest.TestCase):
    def test_legal_texts_are_public_plain_text_and_match_project_sources(self):
        root=Path(__file__).resolve().parents[1]
        for route,source in [('license','LICENSE'),('notice','NOTICE'),('branding','BRANDING.md'),('third-party','docs/THIRD_PARTY.md')]:
            with self.subTest(route=route):
                result={}
                def start(status,headers):result.update(status=status,headers=dict(headers))
                body=b''.join(application({'PATH_INFO':'/'+route+'.txt','REQUEST_METHOD':'GET','wsgi.input':io.BytesIO()},start))
                self.assertEqual(result['status'],'200 OK')
                self.assertEqual(result['headers']['Content-Type'],'text/plain; charset=utf-8')
                self.assertEqual(body,(root/source).read_bytes())
                self.assertIn('nosniff',result['headers'].values())
        self.assertIn('Apache License',(root/'LICENSE').read_text())
