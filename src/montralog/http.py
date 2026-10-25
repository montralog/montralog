import json
import time
import sqlite3
import urllib.parse
from .config import VERSION, ROOT, MAX_BODY
from .storage import database, StorageError
from .ingestion import ingest
from .otlp import otel_logs_or_spans
from .queries import query_view
from .metrics import PANELS, prometheus
from .security import token_matches
from . import accounts
from .tenancy import tenant_id


def application(environ, start_response):
    status, content_type = 200, 'application/json; charset=utf-8'
    headers = [('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),('X-Frame-Options','DENY'),
               ('Referrer-Policy','no-referrer'),('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")]
    try:
        path, method = environ.get('PATH_INFO','/'), environ['REQUEST_METHOD']
        tenant = tenant_id()
        headers.append(('X-Montralog-Tenant', tenant))
        if environ.get('HTTP_X_MONTRALOG_TENANT', tenant) != tenant:
            raise accounts.AccountError('Tenant does not match this deployment.', 403)
        if path in ('/','/app.js','/workspace.js','/studio.js','/connections.js','/access.js','/style.css') and method == 'GET':
            filename, content_type = {'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','application/javascript'),'/workspace.js':('workspace.js','application/javascript'),'/studio.js':('studio.js','application/javascript'),'/connections.js':('connections.js','application/javascript'),'/access.js':('access.js','application/javascript'),'/style.css':('style.css','text/css')}[path]
            body = (ROOT/'static'/filename).read_bytes()
        elif path in ('/healthz','/livez') and method == 'GET':
            body = {'status':'alive','version':VERSION}
        elif path == '/health/ready' and method == 'GET':
            with database() as db:
                db.execute('SELECT 1').fetchone()
            body = {'status':'ready'}
        elif path == '/api/auth/status' and method == 'GET':
            with database() as db:
                exists = bool(db.execute('SELECT id FROM users LIMIT 1').fetchone())
            body = {'configured': exists}
        elif path == '/api/auth/providers' and method == 'GET':
            from .identity import public_providers
            body=public_providers()
        elif path.startswith(('/auth/oidc/start/','/auth/oidc/callback/')) and method=='GET':
            from .identity import flow
            params={k:v[-1] for k,v in urllib.parse.parse_qs(environ.get('QUERY_STRING','')).items()}
            location,extra=flow(path,params,environ)
            status,body=302,{'redirect':True}
            headers.extend(extra);headers.append(('Location',location))
        elif path == '/api/auth/login' and method == 'POST':
            body, extra = accounts.login(read_json(environ), environ)
            headers.append(extra)
        elif path.startswith('/api/control/'):
            from . import studio, notifications
            user=accounts.session(environ)
            data=read_json(environ) if method=='POST' else {}
            if path=='/api/control/identity':
                from .identity import settings as identity_settings
                body=identity_settings(method,data,user,environ)
            elif path=='/api/control/access':
                from .access import route as access_route
                body=access_route(method,data,user,environ)
            elif path=='/api/control/data-sources':
                from .connections import route as connection_route
                body=connection_route(method,data,user,environ)
            elif path=='/api/control/tokens':body=studio.tokens_route(method,data,user,environ)
            else:body=notifications.route(path,method,data,user,environ)
        elif path.startswith('/api/account') or path.startswith('/api/saved-dashboards'):
            user = accounts.session(environ)
            data = read_json(environ) if method == 'POST' else {}
            body, extra = accounts.account_route(path, method, data, environ, user)
            headers.extend(extra)
        else:
            auth = environ.get('HTTP_AUTHORIZATION','')
            candidate = auth[7:] if auth.startswith('Bearer ') else ''
            write = method == 'POST'
            allowed = token_matches('MONTRALOG_INGEST_TOKEN' if write else 'MONTRALOG_READ_TOKEN',candidate)
            if method == 'GET' and not allowed:
                allowed = accounts.session(environ) is not None
            if not allowed:
                status, body = 401, {'error':'Valid ingest token required' if write else 'Valid read token required'}
            elif method == 'GET':
                params = {k:v[-1] for k,v in urllib.parse.parse_qs(environ.get('QUERY_STRING','')).items()}
                view = path.removeprefix('/api/')
                if view in ('overview','logs','patterns','traces','samples','events'):
                    body = query_view(view, params)
                elif view == 'metrics':
                    panel = params.get('panel','targets')
                    if panel not in PANELS:
                        raise ValueError('Unknown dashboard panel')
                    minutes = max(1,min(1440,int(params.get('minutes','60'))))
                    now = time.time()
                    body = prometheus('query_range',{'query':PANELS[panel][1],'start':now-minutes*60,'end':now,'step':max(15,minutes*60//120)},params.get('datasource',''))
                    body['panel'] = {'id':panel,'title':PANELS[panel][0],'unit':PANELS[panel][2]}
                elif view == 'targets':
                    body = prometheus('targets',source_id=params.get('datasource',''))
                elif view == 'alerts':
                    body = prometheus('alerts',source_id=params.get('datasource',''))
                elif view == 'dashboards':
                    body = {'items':[{'id':k,'title':v[0],'unit':v[2]} for k,v in PANELS.items()]}
                elif path == '/readyz':
                    with database() as db:
                        db.execute('SELECT 1').fetchone()
                    body = {'status':'ready'}
                else:
                    status,body = 404,{'error':'Not found'}
            elif method == 'POST' and path in ('/api/logs','/api/spans','/api/samples','/api/events','/v1/logs','/v1/traces','/v1/metrics'):
                length = int(environ.get('CONTENT_LENGTH') or '0')
                if length <= 0 or length > MAX_BODY:
                    status,body = 413,{'error':'Expected body up to 2 MiB'}
                elif environ.get('CONTENT_TYPE','').split(';')[0] != 'application/json':
                    status,body = 415,{'error':'application/json required; use the bundled collector for OTLP protobuf/gRPC'}
                else:
                    raw = environ['wsgi.input'].read(length)
                    if len(raw) != length:
                        raise ValueError('Truncated request')
                    data = json.loads(raw)
                    if path=='/v1/metrics':
                        from .forwarding import metrics as forward_metrics
                        body=forward_metrics(raw)
                    elif path.startswith('/v1/'):
                        otel_logs_or_spans(data, 'logs' if path.endswith('logs') else 'spans')
                        body = {}
                    else:
                        body = {'accepted':ingest(path.split('/')[-1],data)}
                        status = 201
            else:
                status,body = 404,{'error':'Not found'}
    except accounts.AccountError as error:
        status,body = error.status,{'error':error.message}
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        status,body = 400,{'error':'Invalid request fields or payload. See docs/API.md.'}
    except (StorageError, sqlite3.Error):
        status,body = 503,{'error':'Storage unavailable; retry with backoff'}
    except Exception:
        import logging
        logging.exception('Unhandled request failure')
        status,body = 500,{'error':'Internal server error'}
    if not isinstance(body, bytes):
        body = json.dumps(body,allow_nan=False).encode()
    labels = {302:'Found',200:'OK',201:'Created',400:'Bad Request',401:'Unauthorized',403:'Forbidden',404:'Not Found',429:'Too Many Requests',413:'Content Too Large',415:'Unsupported Media Type',500:'Internal Server Error',503:'Service Unavailable'}
    start_response(f'{status} {labels[status]}',headers+[('Content-Type',content_type),('Content-Length',str(len(body)))])
    return [body]


def read_json(environ):
    length = int(environ.get('CONTENT_LENGTH') or '0')
    if not 0 < length <= 65536:
        raise accounts.AccountError('Expected JSON body up to 64 KiB.',413)
    if environ.get('CONTENT_TYPE','').split(';')[0] != 'application/json':
        raise accounts.AccountError('application/json required.',415)
    raw = environ['wsgi.input'].read(length)
    if len(raw) != length:
        raise ValueError('Truncated request')
    data=json.loads(raw)
    if not isinstance(data,dict):
        raise accounts.AccountError('Expected a JSON object.')
    return data
