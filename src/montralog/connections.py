"""Server-side saved Prometheus data sources, safe metadata and connection tests."""
import base64
import ipaddress
import json
import math
import os
import secrets
import socket
import time
import urllib.parse
import urllib.request
from .accounts import AccountError, require_csrf
from .storage import database
from .config import MAX_BODY

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def validate_url(raw):
    if not isinstance(raw,str) or len(raw)>1000 or any(c.isspace() for c in raw):raise AccountError('Enter a valid server URL.')
    try:
        url=urllib.parse.urlsplit(raw)
        port=url.port
    except ValueError:raise AccountError('Enter a valid server URL.') from None
    if url.scheme not in ('http','https') or not url.hostname or url.username or url.password or url.query or url.fragment or '%' in url.hostname or (port is not None and not 1<=port<=65535):
        raise AccountError('Use an HTTP or HTTPS server URL without embedded credentials, query or fragment.')
    if url.hostname.lower().rstrip('.') in ('metadata.google.internal','metadata','instance-data'):
        raise AccountError('Metadata endpoints cannot be used as data sources.')
    try:addresses={entry[4][0] for entry in socket.getaddrinfo(url.hostname,port or (443 if url.scheme=='https' else 80),type=socket.SOCK_STREAM)}
    except OSError:raise AccountError('Server name could not be resolved. Use an address reachable from Montralog.') from None
    for address in addresses:
        ip=ipaddress.ip_address(address)
        if ip.version==6 and ip.ipv4_mapped:ip=ip.ipv4_mapped
        if ip.is_link_local or ip.is_multicast or ip.is_unspecified or str(ip) in ('169.254.169.254','fd00:ec2::254','100.100.100.200'):
            raise AccountError('Link-local, metadata, multicast and unspecified addresses are not supported.')
    return raw.rstrip('/')

def finite_json_number(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('Non-finite JSON number')
    return number


def query(source,path,params=None):
    if path not in ('query','query_range','targets','alerts'):raise ValueError('Unsupported Prometheus API')
    try:
        base=validate_url(source['url'])
        headers={'Accept':'application/json'}
        if source.get('auth_type')=='basic':
            credentials=(source.get('username','')+':'+source.get('secret','')).encode()
            headers['Authorization']='Basic '+base64.b64encode(credentials).decode()
        elif source.get('auth_type')=='bearer':headers['Authorization']='Bearer '+source.get('secret','')
        url=base+'/api/v1/'+path
        if params:url+='?'+urllib.parse.urlencode(params)
        request=urllib.request.Request(url,headers=headers)
        with urllib.request.build_opener(NoRedirect()).open(request,timeout=8) as response:
            raw=response.read(MAX_BODY+1)
            if len(raw)>MAX_BODY:raise ValueError('Response too large')
            result=json.loads(raw,parse_float=finite_json_number,parse_constant=finite_json_number)
            if not isinstance(result,dict) or result.get('status')!='success' or not isinstance(result.get('data'),dict):
                return {'available':False,'error':'The server did not return a successful Prometheus API response.'}
            return {'available':True,**result,'source':{'id':source.get('id','builtin'),'name':source.get('name','Bundled Prometheus')}}
    except AccountError as error:return {'available':False,'error':error.message}
    except (OSError,ValueError):return {'available':False,'error':'Connection failed. Check the server address, credentials, TLS certificate and network access.'}

def resolve(ident=''):
    with database() as db:
        row=db.execute('SELECT * FROM data_sources WHERE id=?',(ident,)).fetchone() if ident and ident!='builtin' else (db.execute('SELECT * FROM data_sources WHERE is_default=1 LIMIT 1').fetchone() if not ident else None)
    if row:return dict(row)
    if ident and ident!='builtin':raise AccountError('Data source not found.',404)
    return {'id':'builtin','name':'Bundled Prometheus','url':os.getenv('PROMETHEUS_URL',''),'auth_type':'none','username':'','secret':''}

def public(row):
    return {key:row[key] for key in ('id','name','url','auth_type','username','is_default','last_checked','last_status','last_detail','created_at')}

def route(method,data,user,environ):
    if not user:raise AccountError('Sign in to continue.',401)
    if method=='GET':
        with database() as db:items=[public(dict(r)) for r in db.execute('SELECT * FROM data_sources ORDER BY name')]
        builtin={'id':'builtin','name':'Bundled Prometheus','url':os.getenv('PROMETHEUS_URL',''),'auth_type':'none','username':'','is_default':int(not any(r['is_default'] for r in items)),'last_checked':0,'last_status':'bundled','last_detail':'Configured by your Docker or Helm deployment','created_at':0}
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
        if old and old['auth_type']==auth and not secret:secret=old['secret']
        if auth=='none':secret='';username=''
        if auth=='basic' and (not username or not secret):raise AccountError('Enter the server username and password.')
        if auth=='bearer' and not secret:raise AccountError('Enter the server bearer credential.')
        source={'id':ident,'name':name.strip(),'url':url,'auth_type':auth,'username':username,'secret':secret}
    result=query(source,'query',{'query':'up'})
    count=len(result.get('data',{}).get('result',[])) if result.get('available') else 0
    detail=f'Connected. Prometheus returned {count} scrape-status series.' if result.get('available') else result.get('error','Connection failed.')
    status='connected' if result.get('available') else 'error';now=time.time()
    if action=='test-saved':
        if ident!='builtin':
            with database() as db:db.execute('UPDATE data_sources SET last_checked=?,last_status=?,last_detail=? WHERE id=?',(now,status,detail,ident))
        return {'ok':bool(result.get('available')),'message':detail,'series':count}
    if action=='test':return {'ok':bool(result.get('available')),'message':detail,'series':count}
    if action!='save':raise AccountError('Unknown connection action.')
    if not result.get('available'):raise AccountError(detail)
    default=int(data.get('is_default',False) is True)
    with database() as db:
        if default:db.execute('UPDATE data_sources SET is_default=0 WHERE is_default=1')
        if ident:
            db.execute('UPDATE data_sources SET name=?,url=?,auth_type=?,username=?,secret=?,is_default=?,last_checked=?,last_status=?,last_detail=? WHERE id=?',
                       (source['name'],source['url'],source['auth_type'],source['username'],source['secret'],default,now,status,detail,ident))
        else:
            if db.execute('SELECT COUNT(*) FROM data_sources').fetchone()[0]>=30:raise AccountError('Maximum of 30 saved data sources.')
            ident=secrets.token_hex(16)
            db.execute('INSERT INTO data_sources(id,name,url,auth_type,username,secret,is_default,last_checked,last_status,last_detail,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                       (ident,source['name'],source['url'],source['auth_type'],source['username'],source['secret'],default,now,status,detail,now))
    return {'id':ident,'ok':True,'message':detail,'series':count}
