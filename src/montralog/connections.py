"""Server-side saved observability data sources, safe metadata and connection tests."""
import base64
import ipaddress
import json
import math
import os
import secrets
import socket
import time
import urllib.parse
import urllib.error
import urllib.request
from .accounts import AccountError, require_csrf
from .storage import database
from .config import MAX_BODY
from .secret_store import seal, reveal
from .outbound import open_request

SOURCE_KINDS = {
    'prometheus': ('Prometheus', 'metric'), 'victoriametrics': ('VictoriaMetrics', 'metric'),
    'mimir': ('Mimir', 'metric'), 'thanos': ('Thanos', 'metric'),
    'loki': ('Loki', 'logs'), 'tempo': ('Tempo', 'traces'),
}

def source_signal(source):
    return SOURCE_KINDS.get(source.get('kind','prometheus'), ('', ''))[1]

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def validate_url(raw):
    from .outbound import destination, DestinationError
    try:
        parsed, _, _ = destination(raw, private_origins=builtin_origins(raw))
        if parsed.query:
            raise DestinationError('Base endpoints cannot contain query parameters.')
        return raw.rstrip('/')
    except DestinationError as error:
        raise AccountError(str(error)) from None


def builtin_origins(raw):
    # Only the operator-configured bundled endpoint receives the internal exception.
    configured = os.getenv('PROMETHEUS_URL', '').rstrip('/')
    if configured and raw.rstrip('/') == configured:
        parsed = urllib.parse.urlsplit(configured)
        return (f'{parsed.hostname}:{parsed.port or (443 if parsed.scheme == "https" else 80)}',)
    return ()


def finite_json_number(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('Non-finite JSON number')
    return number


def query(source,path,params=None):
    if path not in ('query','query_range','targets','alerts'):raise ValueError('Unsupported Prometheus API')
    if source_signal(source)!='metric':return {'available':False,'error':'This source does not provide Prometheus metrics.'}
    try:
        base=validate_url(source['url'])
        headers={'Accept':'application/json'}
        if source.get('auth_type')=='basic':
            credentials=(source.get('username','')+':'+reveal(source.get('secret',''))).encode()
            headers['Authorization']='Basic '+base64.b64encode(credentials).decode()
        elif source.get('auth_type')=='bearer':headers['Authorization']='Bearer '+reveal(source.get('secret',''))
        url=base+'/api/v1/'+path
        if params:url+='?'+urllib.parse.urlencode(params)
        request=urllib.request.Request(url,headers=headers)
        with open_request(request, timeout=8, private_origins=builtin_origins(source['url'])) as response:
            raw=response.read(MAX_BODY+1)
            if len(raw)>MAX_BODY:raise ValueError('Response too large')
            result=json.loads(raw,parse_float=finite_json_number,parse_constant=finite_json_number)
            if not isinstance(result,dict) or result.get('status')!='success' or not isinstance(result.get('data'),dict):
                return {'available':False,'error':'The server did not return a successful Prometheus API response.'}
            return {'available':True,**result,'source':{'id':source.get('id','builtin'),'name':source.get('name','Bundled Prometheus')}}
    except AccountError as error:return {'available':False,'error':error.message}
    except urllib.error.HTTPError as error:
        error.close()
        return {'available':False,'error':'Connection failed. Check the server address, credentials, TLS certificate and network access.'}
    except (OSError,ValueError):return {'available':False,'error':'Connection failed. Check the server address, credentials, TLS certificate and network access.'}

def resolve(ident=''):
    with database() as db:
        row=db.execute('SELECT * FROM data_sources WHERE id=?',(ident,)).fetchone() if ident and ident!='builtin' else (db.execute('SELECT * FROM data_sources WHERE is_default=1 LIMIT 1').fetchone() if not ident else None)
    if row:return dict(row)
    if ident and ident!='builtin':raise AccountError('Data source not found.',404)
    return {'id':'builtin','name':'Bundled Prometheus','url':os.getenv('PROMETHEUS_URL',''),'auth_type':'none','username':'','secret':''}

def public(row):
    return {key:row[key] for key in ('id','name','url','auth_type','username','is_default','last_checked','last_status','last_detail','created_at','kind')}

def route(method,data,user,environ):
    if not user:raise AccountError('Sign in to continue.',401)
    if method=='GET':
        with database() as db:items=[public(dict(r)) for r in db.execute('SELECT * FROM data_sources ORDER BY name')]
        builtin={'id':'builtin','name':'Bundled Prometheus','url':os.getenv('PROMETHEUS_URL',''),'auth_type':'none','username':'','is_default':int(not any(r['is_default'] for r in items)),'last_checked':0,'last_status':'bundled','last_detail':'Configured by your Docker or Helm deployment','created_at':0,'kind':'prometheus'}
        return {'items':[builtin,*items]}
    from .studio import admin
    admin(user);require_csrf(environ,user)
    action=data.get('action','save');ident=str(data.get('id',''))
    if action=='delete':
        if ident=='builtin':raise AccountError('The bundled connection is managed by your deployment.')
        with database() as db:db.execute('DELETE FROM data_sources WHERE id=?',(ident,))
        return {'ok':True}
    if action=='test-saved':
        source=resolve(ident)
    else:
        name=data.get('name','');url=data.get('url','');auth=data.get('auth_type','none');username=data.get('username','');secret=data.get('secret','')
        if not isinstance(name,str) or not 1<=len(name.strip())<=80:raise AccountError('Provide a connection name of 1–80 characters.')
        if auth not in ('none','basic','bearer') or not isinstance(username,str) or len(username)>200 or ':' in username or not isinstance(secret,str) or len(secret)>8192 or any(c in secret for c in ('\r','\n')):
            raise AccountError('Invalid authentication settings.')
        if ident=='builtin':raise AccountError('Create a saved connection to customize the bundled address.')
        url=validate_url(url)
        with database() as db:old=db.execute('SELECT * FROM data_sources WHERE id=?',(ident,)).fetchone() if ident else None
        if ident and not old:raise AccountError('Connection not found.',404)
        if old and old['auth_type']==auth and not secret:
            if auth!='none' and (old['url'].rstrip('/')!=url or data.get('kind',dict(old).get('kind','prometheus'))!=dict(old).get('kind','prometheus')):
                raise AccountError('Re-enter the credential when changing its server endpoint.')
            secret=reveal(old['secret'])
        if auth=='none':secret='';username=''
        if auth!='none' and urllib.parse.urlsplit(url).scheme!='https':
            raise AccountError('Saved credentials require an HTTPS data source.')
        if auth=='basic' and (not username or not secret):raise AccountError('Enter the server username and password.')
        if auth=='bearer' and not secret:raise AccountError('Enter the server bearer credential.')
        kind=data.get('kind',dict(old).get('kind','prometheus') if old else 'prometheus')
        if not isinstance(kind,str) or kind not in SOURCE_KINDS:raise AccountError('Unsupported source kind.')
        source={'kind':kind,'id':ident,'name':name.strip(),'url':url,'auth_type':auth,'username':username,'secret':secret}
    result=query(source,'query',{'query':'up'}) if source_signal(source)=='metric' else test_remote(source)
    count=len(result.get('data',{}).get('result',[])) if result.get('available') else 0
    detail=f'Connected. {SOURCE_KINDS.get(source.get("kind","prometheus"), ("Backend",))[0]} API test passed ({count} results).' if result.get('available') else result.get('error','Connection failed.')
    status='connected' if result.get('available') else 'error';now=time.time()
    if action=='test-saved':
        if ident!='builtin':
            with database() as db:db.execute('UPDATE data_sources SET last_checked=?,last_status=?,last_detail=? WHERE id=?',(now,status,detail,ident))
        return {'ok':bool(result.get('available')),'message':detail,'series':count}
    if action=='test':return {'ok':bool(result.get('available')),'message':detail,'series':count}
    if action!='save':raise AccountError('Unknown connection action.')
    if not result.get('available'):raise AccountError(detail)
    source['secret']=seal(source['secret'])
    default=int(data.get('is_default',False) is True and source_signal(source)=='metric')
    with database() as db:
        if default:db.execute('UPDATE data_sources SET is_default=0 WHERE is_default=1')
        if ident:
            db.execute('UPDATE data_sources SET name=?,url=?,auth_type=?,username=?,secret=?,is_default=?,last_checked=?,last_status=?,last_detail=?,kind=? WHERE id=?',
                       (source['name'],source['url'],source['auth_type'],source['username'],source['secret'],default,now,status,detail,source['kind'],ident))
        else:
            if db.execute('SELECT COUNT(*) FROM data_sources').fetchone()[0]>=30:raise AccountError('Maximum of 30 saved data sources.')
            ident=secrets.token_hex(16)
            db.execute('INSERT INTO data_sources(id,name,url,auth_type,username,secret,is_default,last_checked,last_status,last_detail,created_at,kind) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                       (ident,source['name'],source['url'],source['auth_type'],source['username'],source['secret'],default,now,status,detail,now,source['kind']))
    return {'id':ident,'ok':True,'message':detail,'series':count}


def remote_json(source, path, params=None):
    """Fixed-path adapters share the DNS-pinned, no-redirect secret transport."""
    base=validate_url(source['url'])
    headers={'Accept':'application/json'}
    if source.get('auth_type')=='basic':
        raw=(source.get('username','')+':'+reveal(source.get('secret',''))).encode()
        headers['Authorization']='Basic '+base64.b64encode(raw).decode()
    elif source.get('auth_type')=='bearer':headers['Authorization']='Bearer '+reveal(source.get('secret',''))
    if source.get('auth_type','none')!='none' and not base.startswith('https://'):
        raise AccountError('Credentials require HTTPS.')
    url=base+path+('?' + urllib.parse.urlencode(params) if params else '')
    with open_request(urllib.request.Request(url,headers=headers),timeout=8,private_origins=builtin_origins(source['url'])) as response:
        raw=response.read(MAX_BODY+1)
        if len(raw)>MAX_BODY:raise ValueError('Response too large')
        result=json.loads(raw,parse_float=finite_json_number,parse_constant=finite_json_number)
        if not isinstance(result,dict):raise ValueError('Invalid backend response')
        return result


def test_remote(source):
    try:
        kind=source.get('kind')
        if kind=='loki':
            result=remote_json(source,'/loki/api/v1/labels',{'start':int((time.time()-900)*1e9)})
            if result.get('status')!='success' or not isinstance(result.get('data'),list):raise ValueError()
        elif kind=='tempo':
            result=remote_json(source,'/api/search',{'start':int(time.time()-900),'end':int(time.time()),'limit':1})
            if not isinstance(result.get('traces'),list):raise ValueError()
        else:raise ValueError()
        return {'available':True,'data':{'result':[]}}
    except urllib.error.HTTPError as error:
        error.close()
        return {'available':False,'error':'Backend API test failed. Check endpoint, credentials, TLS and network policy.'}
    except (AccountError,OSError,ValueError):
        return {'available':False,'error':'Backend API test failed. Check endpoint, credentials, TLS and network policy.'}


def remote_records(source, signal, params):
    from .validation import pattern
    if source_signal(source)!=('logs' if signal=='patterns' else signal):raise AccountError('Data source does not support this signal.')
    minutes=max(1,min(1440,int(params.get('minutes',60))))
    now=time.time();service=params.get('service','');environment=params.get('environment','');text=params.get('q','');severity=params.get('severity','')
    if any(not isinstance(v,str) or len(v)>200 for v in (service,environment,text,severity)):raise AccountError('Invalid source filter.')
    try:
        if source.get('kind')=='loki':
            labels=[f'{key}={json.dumps(value)}' for key,value in (('service_name',service),('environment',environment)) if value]
            selector='{'+','.join(labels or ['service_name=~".+"'])+'}'
            if text:selector+=' |= '+json.dumps(text)
            result=remote_json(source,'/loki/api/v1/query_range',{'query':selector,'start':int((now-minutes*60)*1e9),'end':int(now*1e9),'limit':100,'direction':'backward'})
            if result.get('status')!='success' or result.get('data',{}).get('resultType')!='streams':raise ValueError()
            items=[]
            for stream in result['data'].get('result',[]):
                labels=stream['stream']
                for stamp,line,*_ in stream['values']:
                    level=str(labels.get('severity',labels.get('level','INFO'))).upper()
                    if severity and level!=severity:continue
                    items.append({'time':int(stamp)/1e9,'message':str(line)[:16000],'severity':level,'service':labels.get('service_name',''),'environment':labels.get('environment','')})
            items=sorted(items,key=lambda item:item['time'],reverse=True)[:100]
            if signal=='patterns':
                groups={}
                for item in items:
                    key=(item['service'],item['environment'],pattern(item['message']))
                    group=groups.setdefault(key,{'service':key[0],'environment':key[1],'pattern':key[2],'occurrences':0,'errors':0})
                    group['occurrences']+=1;group['errors']+=int(item['severity'] in ('ERROR','FATAL'))
                items=sorted(groups.values(),key=lambda item:item['occurrences'],reverse=True)
            return {'items':items,'sampled':True,'limit':100}
        clauses=[f'resource.{key} = {json.dumps(value)}' for key,value in (('service.name',service),('deployment.environment.name',environment)) if value]
        result=remote_json(source,'/api/search',{'q':'{ '+ ' && '.join(clauses)+' }','start':int(now-minutes*60),'end':int(now),'limit':100})
        if not isinstance(result.get('traces'),list):raise ValueError()
        for trace in result['traces'][:100]:
            if not isinstance(trace,dict) or not isinstance(trace.get('traceID'),str) or not math.isfinite(float(trace.get('durationMs',0))):raise ValueError()
        return {'items':[{'time':int(t.get('startTimeUnixNano',0))/1e9,'trace_id':t['traceID'],'services':t.get('rootServiceName',''),'name':t.get('rootTraceName',''),'spans':0,'duration_s':float(t.get('durationMs',0))/1000,'remote':True} for t in result['traces'][:100]],'limit':100}
    except urllib.error.HTTPError as error:
        error.close();raise AccountError('Source query failed. Check endpoint, access and query compatibility.',502) from None
    except (OSError,ValueError,KeyError,TypeError):
        raise AccountError('Source query failed. Check endpoint, access and query compatibility.',502) from None
