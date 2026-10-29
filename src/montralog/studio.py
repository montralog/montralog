"""Validated dashboard definitions and admin-managed scoped API credentials."""
import hashlib
import json
import math
import secrets
import time
import urllib.parse
from .accounts import AccountError, require_csrf
from .storage import database
from .metrics import PANELS, build_query

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
        allowed={'metric':('line','bar','stat','table','gauge'),'logs':('table','timeline'),
                 'patterns':('table','bar'),'events':('table','timeline'),'traces':('table','timeline')}
        if source not in allowed or visual not in allowed[source]:raise AccountError('Unsupported panel view for this signal.')
        metric=p.get('metric','cpu')
        if source=='metric' and metric not in PANELS:raise AccountError('Unknown metric panel.')
        item={'source':source,'visual':visual,'metric':metric if source=='metric' else '',
              'title':str(p.get('title','')).strip()[:100], 'width':p.get('width') if p.get('width') in ('third','half','full') else 'half'}
        for key,limit in (('description',600),('reference',1000)):
            value=p.get(key,'')
            if not isinstance(value,str) or len(value)>limit:raise AccountError('Invalid panel '+key+'.')
            item[key]=value.strip()
        if item['reference']:
            try:
                link=urllib.parse.urlsplit(item['reference'])
                if link.scheme!='https' or not link.hostname or link.username or link.password or any(ord(c)<=32 for c in item['reference']):raise ValueError()
                link.port
            except ValueError:raise AccountError('Panel references require an HTTPS URL without embedded credentials.') from None
        icon=p.get('icon','activity')
        if icon not in ('activity','server','container','cloud','application','logs','shield'):raise AccountError('Invalid panel icon.')
        height=p.get('height','standard')
        if height not in ('compact','standard','tall'):raise AccountError('Invalid panel height.')
        item.update(icon=icon,height=height)
        if visual=='gauge':
            try:
                gauge={key:float(p.get(key,default)) for key,default in (('min',0),('max',100),('warning',70),('critical',90))}
                if not all(math.isfinite(v) and abs(v)<=1e12 for v in gauge.values()) or not gauge['min']<gauge['warning']<gauge['critical']<=gauge['max']:raise ValueError()
            except (TypeError,ValueError):raise AccountError('Gauge needs finite min < warning < critical <= max values.') from None
            item.update(gauge)
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
            connection=resolve(datasource)
            from .connections import source_signal
            if source_signal(connection)!=('logs' if source=='patterns' else source):raise AccountError('Data source does not support this panel signal.')
        if source == 'metric':
            aggregation=p.get('aggregation','none');group_by=p.get('group_by','')
            try:build_query(metric,aggregation,group_by)
            except ValueError as exc:raise AccountError(str(exc)) from exc
            item.update(aggregation=aggregation,group_by=group_by)
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
