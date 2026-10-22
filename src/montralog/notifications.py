"""Persisted alert rules, in-app notifications and retrying Slack delivery."""
import hashlib
import json
import math
import re
import secrets
import time
import urllib.request
from .accounts import AccountError, require_csrf
from .studio import admin
from .storage import database
from .metrics import PANELS, prometheus

def valid_webhook(url):
    return isinstance(url,str) and bool(re.fullmatch(r'https://hooks\.slack\.com/services/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+',url)) and len(url)<=512

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def send_slack(url,text):
    if not valid_webhook(url):raise ValueError('Invalid Slack endpoint')
    req=urllib.request.Request(url,data=json.dumps({'text':text,'mrkdwn':False,'unfurl_links':False,'unfurl_media':False}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.build_opener(NoRedirect()).open(req,timeout=8) as response:
        if response.read(128).strip()!=b'ok':raise ValueError('Slack did not acknowledge delivery')

def route(path,method,data,user,environ):
    if not user:raise AccountError('Sign in to continue.',401)
    if path=='/api/control/inbox' and method=='GET':
        with database() as db:return {'items':[dict(r) for r in db.execute('SELECT id,title,message,state,created_at FROM notification_inbox ORDER BY created_at DESC LIMIT 100')]}
    admin(user)
    if method!='GET':require_csrf(environ,user)
    if path=='/api/control/channels':
        if method=='GET':
            with database() as db:
                items=[dict(r) for r in db.execute('SELECT id,name,kind,enabled,created_at FROM notification_channels ORDER BY created_at')]
                worker=db.execute("SELECT updated_at FROM worker_heartbeat WHERE id='notifications'").fetchone()
            return {'items':items,'worker_last_seen':worker[0] if worker else None}
        action=data.get('action','save');ident=str(data.get('id',''))
        if action=='delete':
            with database() as db:
                db.execute("UPDATE notification_outbox SET status='cancelled' WHERE channel_id=? AND status='pending'",(ident,))
                db.execute('DELETE FROM notification_channels WHERE id=?',(ident,))
            return {'ok':True}
        if action=='test':
            with database() as db:row=db.execute('SELECT * FROM notification_channels WHERE id=?',(ident,)).fetchone()
            if not row:raise AccountError('Channel not found.',404)
            if not row['enabled']:raise AccountError('Enable this contact point before sending a test.')
            with database() as db:
                if db.execute("SELECT COUNT(*) FROM notification_outbox WHERE status='pending'").fetchone()[0]>=1000:
                    raise AccountError('Notification queue is full; check delivery health.')
                db.execute('INSERT INTO notification_outbox(id,channel_id,message,status,attempts,next_attempt,created_at,last_error) VALUES (?,?,?,?,?,?,?,?)',
                           (secrets.token_hex(16),ident,'Montralog test notification: your notification route is connected.','pending',0,time.time(),time.time(),''))
            return {'ok':True,'message':'Test queued. Delivery status will appear below.'}
        name=data.get('name','');url=data.get('webhook','');enabled=int(data.get('enabled',True) is True)
        if not isinstance(name,str) or not 1<=len(name.strip())<=80:raise AccountError('Provide a channel name.')
        with database() as db:
            old=db.execute('SELECT * FROM notification_channels WHERE id=?',(ident,)).fetchone() if ident else None
            if old and not url:url=old['secret']
            if not valid_webhook(url):raise AccountError('Enter a valid Slack incoming webhook URL from hooks.slack.com.')
            if old:db.execute('UPDATE notification_channels SET name=?,secret=?,enabled=? WHERE id=?',(name.strip(),url,enabled,ident))
            else:
                if db.execute('SELECT COUNT(*) FROM notification_channels').fetchone()[0]>=20:raise AccountError('Maximum of 20 channels.')
                ident=secrets.token_hex(16)
                db.execute('INSERT INTO notification_channels(id,name,kind,secret,enabled,created_at) VALUES (?,?,?,?,?,?)',(ident,name.strip(),'slack',url,enabled,time.time()))
        return {'id':ident}
    if path=='/api/control/deliveries' and method=='GET':
        with database() as db:return {'items':[dict(r) for r in db.execute('SELECT o.id,c.name AS channel,o.status,o.attempts,o.last_error,o.created_at FROM notification_outbox o LEFT JOIN notification_channels c ON c.id=o.channel_id ORDER BY o.created_at DESC LIMIT 100')]}
    if path=='/api/control/rules':
        if method=='GET':
            with database() as db:
                rows=[dict(r) for r in db.execute('SELECT r.*,s.state,s.value,s.checked_at,s.detail FROM alert_rules r LEFT JOIN alert_states s ON s.rule_id=r.id ORDER BY r.created_at DESC')]
            for row in rows:row['definition']=json.loads(row['definition'])
            return {'items':rows}
        ident=str(data.get('id',''))
        if data.get('action')=='delete':
            with database() as db:
                db.execute('DELETE FROM alert_states WHERE rule_id=?',(ident,));db.execute('DELETE FROM alert_rules WHERE id=?',(ident,))
            return {'ok':True}
        name=data.get('name','');d=data.get('definition',{})
        if not isinstance(name,str) or not 1<=len(name.strip())<=100 or not isinstance(d,dict):raise AccountError('Provide a rule name.')
        source=d.get('source','metric');metric=d.get('metric','cpu');op=d.get('op','gt');threshold=float(d.get('threshold',0));duration=int(d.get('for_seconds',60))
        if source not in ('metric','logs') or (source=='metric' and metric not in PANELS) or op not in ('gt','lt') or not math.isfinite(threshold) or not 0<=duration<=3600:
            raise AccountError('Invalid alert condition.')
        clean={'source':source,'metric':metric,'op':op,'threshold':threshold,'for_seconds':duration}
        for field in ('service','environment','q'):
            value=d.get(field,'')
            if not isinstance(value,str) or len(value)>200:raise AccountError('Rule filter too long.')
            clean[field]=value
        clean['severity']=d.get('severity','ERROR')
        if clean['severity'] not in ('','ERROR','FATAL','WARN','INFO'):raise AccountError('Invalid log severity.')
        channels=d.get('channels',[])
        if not isinstance(channels,list) or len(channels)>20 or not all(isinstance(c,str) for c in channels):raise AccountError('Invalid notification routes.')
        clean['channels']=list(dict.fromkeys(channels))
        with database() as db:
            for c in channels:
                if not db.execute('SELECT id FROM notification_channels WHERE id=?',(c,)).fetchone():raise AccountError('Unknown channel.')
            if ident:
                if not db.execute('SELECT id FROM alert_rules WHERE id=?',(ident,)).fetchone():raise AccountError('Rule not found.',404)
                db.execute('UPDATE alert_rules SET name=?,definition=?,enabled=? WHERE id=?',(name.strip(),json.dumps(clean),int(data.get('enabled',True) is True),ident))
                db.execute('DELETE FROM alert_states WHERE rule_id=?',(ident,))
            else:
                if db.execute('SELECT COUNT(*) FROM alert_rules').fetchone()[0]>=50:raise AccountError('Maximum of 50 rules.')
                ident=secrets.token_hex(16)
                db.execute('INSERT INTO alert_rules(id,name,definition,enabled,created_at) VALUES (?,?,?,?,?)',(ident,name.strip(),json.dumps(clean),int(data.get('enabled',True) is True),time.time()))
        return {'id':ident}
    raise AccountError('Not found',404)

def evaluate(definition):
    if definition['source']=='metric':
        result=prometheus('query',{'query':PANELS[definition['metric']][1]})
        if not result.get('available') or result.get('status')!='success':return None,'Metric backend unavailable'
        values=[float(s['value'][1]) for s in result.get('data',{}).get('result',[]) if math.isfinite(float(s['value'][1]))]
        if not values:return None,'No current metric samples'
        return (max(values) if definition['op']=='gt' else min(values)),'Across matching metric series'
    clauses=['time>=?'];args=[time.time()-300]
    for field in ('service','environment','severity'):
        if definition.get(field):clauses.append(field+'=?');args.append(definition[field])
    if definition.get('q'):
        clauses.append("LOWER(message) LIKE LOWER(?) ESCAPE '\\'")
        args.append('%'+definition['q'].replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%')
    with database() as db:value=db.execute('SELECT COUNT(*) FROM logs WHERE '+' AND '.join(clauses),args).fetchone()[0]
    return float(value),'Matching logs in last 5 minutes'

def tick():
    now=time.time()
    with database() as db:
        db.execute("INSERT INTO worker_heartbeat(id,updated_at) VALUES ('notifications',?) ON CONFLICT(id) DO UPDATE SET updated_at=excluded.updated_at",(now,))
        rules=[dict(r) for r in db.execute('SELECT * FROM alert_rules WHERE enabled=1')]
    for rule in rules:
        d=json.loads(rule['definition'])
        try:value,detail=evaluate(d)
        except Exception:value,detail=None,'Evaluation failed; check backend availability'
        with database() as db:
            previous=db.execute('SELECT * FROM alert_states WHERE rule_id=?',(rule['id'],)).fetchone()
            old=previous['state'] if previous else 'normal';since=previous['since_at'] if previous else now
            if value is None:state='unknown'
            elif (value>d['threshold'] if d['op']=='gt' else value<d['threshold']):
                if old not in ('pending','firing'):since=now
                state='firing' if now-since>=d['for_seconds'] else 'pending'
            else:state='normal';since=now
            db.execute('INSERT INTO alert_states(rule_id,state,value,since_at,checked_at,detail) VALUES (?,?,?,?,?,?) ON CONFLICT(rule_id) DO UPDATE SET state=excluded.state,value=excluded.value,since_at=excluded.since_at,checked_at=excluded.checked_at,detail=excluded.detail',
                       (rule['id'],state,value,since,now,detail))
            if (state=='firing' and old!='firing') or (state=='normal' and old=='firing'):
                title=('FIRING' if state=='firing' else 'RESOLVED')+' · '+rule['name']
                message=f'{title}\nObserved: {value:g}; threshold: {d["op"]} {d["threshold"]:g}. {detail}.'
                db.execute('INSERT INTO notification_inbox(id,title,message,state,created_at) VALUES (?,?,?,?,?)',(secrets.token_hex(16),title,message,state,now))
                for channel in d['channels']:
                    if db.execute('SELECT id FROM notification_channels WHERE id=? AND enabled=1',(channel,)).fetchone():
                        db.execute('INSERT INTO notification_outbox(id,channel_id,message,status,attempts,next_attempt,created_at,last_error) VALUES (?,?,?,?,?,?,?,?)',(secrets.token_hex(16),channel,message,'pending',0,now,now,''))
    deliver()

def deliver():
    now=time.time()
    with database() as db:items=[dict(r) for r in db.execute("SELECT o.*,c.secret,c.enabled FROM notification_outbox o JOIN notification_channels c ON c.id=o.channel_id WHERE o.status='pending' AND o.next_attempt<=? ORDER BY o.created_at LIMIT 20",(now,))]
    for item in items:
        if not item['enabled']:continue
        try:send_slack(item['secret'],item['message']);status,error='sent',''
        except Exception:status,error=('failed' if item['attempts']>=4 else 'pending'),'Slack delivery failed; check the webhook, channel and network'
        with database() as db:db.execute('UPDATE notification_outbox SET status=?,attempts=?,next_attempt=?,last_error=? WHERE id=?',(status,item['attempts']+1,now+min(900,30*2**item['attempts']),error,item['id']))

def main():
    from .storage import initialize
    initialize()
    while True:
        try:tick()
        except Exception:
            import logging
            logging.error('Notification evaluation cycle failed; retrying')
        time.sleep(30)

if __name__=='__main__':main()
