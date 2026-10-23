import io
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch
from montralog import forwarding
from montralog.accounts import AccountError


class ForwardingSecurityTests(unittest.TestCase):
    def test_redirect_cannot_forward_ingest_credentials_to_another_server(self):
        received = []
        class Destination(BaseHTTPRequestHandler):
            def do_GET(self):
                received.append(self.headers.get('Authorization'))
                self.send_response(200); self.end_headers(); self.wfile.write(b'{}')
            def log_message(self, *args): pass
        with HTTPServer(('127.0.0.1', 0), Destination) as destination:
            class Redirect(BaseHTTPRequestHandler):
                def do_POST(self):
                    self.rfile.read(int(self.headers.get('Content-Length', 0)))
                    self.send_response(302)
                    self.send_header('Location', f'http://127.0.0.1:{destination.server_port}/capture')
                    self.end_headers()
                def log_message(self, *args): pass
            with HTTPServer(('127.0.0.1', 0), Redirect) as source:
                threads = [threading.Thread(target=server.serve_forever, daemon=True) for server in (source, destination)]
                for thread in threads: thread.start()
                try:
                    with patch.dict(os.environ, {'MONTRALOG_COLLECTOR_URL': f'http://127.0.0.1:{source.server_port}', 'MONTRALOG_INGEST_TOKEN': 'private-test-token'}):
                        with self.assertRaises(AccountError): forwarding.metrics(b'{}')
                    self.assertEqual(received, [])
                finally:
                    source.shutdown(); destination.shutdown()
                    for thread in threads: thread.join(timeout=5)

    def test_nonfinite_collector_responses_fail_safely(self):
        for body in (b'{"invalid":NaN}', b'{"invalid":1e400}', b'[]'):
            with self.subTest(body=body), patch.dict(os.environ, {'MONTRALOG_COLLECTOR_URL': 'http://localhost:4318', 'MONTRALOG_INGEST_TOKEN': 'test'}), patch('urllib.request.OpenerDirector.open', return_value=io.BytesIO(body)):
                with self.assertRaises(AccountError) as error: forwarding.metrics(b'{}')
                self.assertEqual(error.exception.status, 503)

    def test_unsupported_collector_url_never_opens_a_request(self):
        for url in ('file:///tmp/collector', 'http://user:password@localhost', 'http://localhost/?secret=x'):
            with self.subTest(url=url), patch.dict(os.environ, {'MONTRALOG_COLLECTOR_URL': url}), patch('urllib.request.OpenerDirector.open') as opened:
                with self.assertRaises(AccountError): forwarding.metrics(b'{}')
                opened.assert_not_called()
