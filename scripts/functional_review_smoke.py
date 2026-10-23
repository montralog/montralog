"""Isolated loopback HTTP and SQLite restore exercise; not a capacity guarantee."""
import concurrent.futures
from contextlib import closing
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import sqlite3
import sys
import tempfile
import threading
import time
import urllib.request
from wsgiref.simple_server import make_server, WSGIRequestHandler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from montralog import storage
from montralog.accounts import create_account
from montralog.http import application


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


def main():
    # This process ignores operator storage and credentials. Only temporary data is used.
    read_token, ingest_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    os.environ.update(MONTRALOG_DATABASE_URL='', MONTRALOG_READ_TOKEN=read_token,
                      MONTRALOG_INGEST_TOKEN=ingest_token, MONTRALOG_COOKIE_SECURE='false')
    with tempfile.TemporaryDirectory(prefix='montralog-review-') as temporary:
        storage.DB = Path(temporary) / 'source.db'
        storage.initialize()
        password = secrets.token_urlsafe(32)
        create_account('admin', 'Review administrator', password)
        jar = http.cookiejar.CookieJar()
        browser = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        with make_server('127.0.0.1', 0, application, handler_class=QuietHandler) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = 'http://127.0.0.1:' + str(server.server_port)
            def request(path, data=None, token=None, csrf=None, opener=browser):
                headers = {'Content-Type': 'application/json'}
                if token:
                    headers['Authorization'] = 'Bearer ' + token
                if csrf:
                    headers['X-CSRF-Token'] = csrf
                payload = json.dumps(data).encode() if data is not None else None
                req = urllib.request.Request(base + path, data=payload, headers=headers)
                with opener.open(req, timeout=30) as response:
                    return json.load(response)
            try:
                auth = request('/api/auth/login', {'username': 'admin', 'password': password})
                saved = request('/api/saved-dashboards', {'name': 'Recovery evidence', 'definition': {
                    'minutes': 15, 'panels': [{'source': 'logs', 'visual': 'timeline'}]}}, csrf=auth['csrf'])
                def send(batch):
                    records = [{'service': 'review', 'environment': 'isolated',
                                'message': f'Batch {batch} event {index}'} for index in range(50)]
                    # Clients do not share the browser cookie jar.
                    result = request('/api/logs', records, token=ingest_token,
                                     opener=urllib.request.build_opener())
                    assert result['accepted'] == 50
                started = time.perf_counter()
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                    list(pool.map(send, range(20)))
                elapsed = time.perf_counter() - started
                before = request('/api/overview?service=review&environment=isolated')
                assert before['totals']['logs'] == 1000
                backup = Path(temporary) / 'restored.db'
                with storage.database() as source, closing(sqlite3.connect(backup)) as destination:
                    source.backup(destination)
                with storage.database() as source:
                    source.execute('DELETE FROM logs')
                    source.execute('DELETE FROM dashboards')
                assert request('/api/overview')['totals']['logs'] == 0
                storage.DB = backup
                assert request('/api/overview')['totals']['logs'] == 1000
                dashboards = request('/api/saved-dashboards')['items']
                assert len(dashboards) == 1 and dashboards[0]['id'] == saved['id']
                assert dashboards[0]['definition']['panels'][0]['visual'] == 'timeline'
                # A second login checks that the restored account/password remains usable.
                assert request('/api/auth/login', {'username': 'admin', 'password': password})['user']['role'] == 'admin'
                print(json.dumps({'result': 'PASS', 'transport': 'loopback HTTP', 'records': 1000,
                                  'batches': 20, 'concurrent_clients': 4, 'elapsed_seconds': round(elapsed, 3),
                                  'restored': ['telemetry', 'dashboard definition', 'account', 'session'],
                                  'limits': 'Temporary SQLite data and a single-threaded test HTTP server; '
                                            'not production sizing, PostgreSQL failover or full incident recovery.'}, indent=2))
            finally:
                server.shutdown()
                worker.join(timeout=10)


if __name__ == '__main__':
    main()
