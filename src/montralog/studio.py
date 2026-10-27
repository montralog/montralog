"""Validated dashboard definitions and admin-managed scoped API credentials."""
import hashlib
import json
import math
import secrets
import time
from .accounts import AccountError, require_csrf
from .storage import database
from .metrics import PANELS

def admin(user):
    if not user or user.get('role') != 'admin':
        raise AccountError('An administrator account is required.',403)

def clean_definition(definition):
    if not isinstance(definition,dict):raise AccountError('Invalid dashboard definition.')
    minutes=int(definition.get('minutes',60))
    if minutes not in (15,60,360,1440):raise AccountError('Choose a supported time window.')
    panels=definition.get('panels',[])
    if not isinstance(panels,list) or not 0<=len(panels)<=24:raise AccountError('Choose up to 24 panels.')
    clean=[]
    for p in panels:
        if isinstance(p,str):
            if p not in PANELS:raise AccountError('Unknown metric panel.')
            clean.append(p);continue
        if not isinstance(p,dict):raise AccountError('Invalid panel.')
        source=p.get('source','metric');visual=p.get('visual','line')
        allowed={'metric':('line','bar','stat','table'),'logs':('table','timeline'),
                 'patterns':('table','bar'),'events':('table','timeline'),'traces':('table','timeline')}
        if source not in allowed or visual not in allowed[source]:raise AccountError('Unsupported panel view for this signal.')
        metric=p.get('metric','cpu')
        if source=='metric' and metric not in PANELS:raise AccountError('Unknown metric panel.')
        item={'source':source,'visual':visual,'metric':metric if source=='metric' else '',
              'title':str(p.get('title','')).strip()[:100], 'width':'full' if p.get('width')=='full' else 'half'}
        for key in ('service','environment','q'):
            value=p.get(key,'')
            if not isinstance(value,str) or len(value)>200:raise AccountError('Panel filter is too long.')
            item[key]=value
        severity=p.get('severity','')
        if severity not in ('','TRACE','DEBUG','INFO','WARN','ERROR','FATAL'):raise AccountError('Invalid severity.')
        item['severity']=severity
        datasource=p.get('datasource','')
        if not isinstance(datasource,str) or len(datasource)>64:raise AccountError('Invalid data source.')
        if datasource:
            from .connections import resolve
            resolve(datasource)
        item['datasource']=datasource
        clean.append(item)
    return {'minutes':minutes,'panels':clean}

def token_valid(raw,scope):
    if not raw.startswith('mtl_') or not 40<=len(raw)<=160:return False
    digest=hashlib.sha256(raw.encode()).hexdigest()
    with database() as db:
        row=db.execute('SELECT id FROM api_tokens WHERE token_hash=? AND scope=? AND revoked=0 AND expires_at>?',(digest,scope,time.time())).fetchone()
        if row:db.execute('UPDATE api_tokens SET last_used_at=? WHERE id=?',(time.time(),row['id']))
    return bool(row)

def tokens_route(method,data,user,environ):
    admin(user)
    if method=='GET':
        with database() as db:
            return {'items':[dict(r) for r in db.execute('SELECT id,name,prefix,scope,created_at,expires_at,last_used_at,revoked FROM api_tokens ORDER BY created_at DESC LIMIT 200')]}
    require_csrf(environ,user)
    if data.get('action')=='revoke':
        with database() as db:db.execute('UPDATE api_tokens SET revoked=1 WHERE id=?',(str(data.get('id','')),))
        return {'ok':True}
    name=data.get('name','');scope=data.get('scope','read');days=int(data.get('days',30))
    if not isinstance(name,str) or not 1<=len(name.strip())<=80 or scope not in ('read','ingest') or days not in (1,7,30,90):
        raise AccountError('Choose a name, read/ingest scope and a supported expiry.')
    from .tenancy import tenant_id
    raw='mtl_'+tenant_id()+'.'+secrets.token_urlsafe(36);now=time.time()
    with database() as db:
        if db.execute('SELECT COUNT(*) FROM api_tokens WHERE revoked=0 AND expires_at>?',(now,)).fetchone()[0]>=100:
            raise AccountError('Maximum of 100 active API tokens reached.')
        db.execute('INSERT INTO api_tokens(id,name,prefix,token_hash,scope,created_at,expires_at,last_used_at,revoked) VALUES (?,?,?,?,?,?,?,?,0)',
                   (secrets.token_hex(16),name.strip(),raw[:12],hashlib.sha256(raw.encode()).hexdigest(),scope,now,now+days*86400,0))
    return {'token':raw,'scope':scope,'expires_at':now+days*86400}
