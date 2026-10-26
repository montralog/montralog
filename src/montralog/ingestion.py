import time
import re
from .validation import attributes, identifier, identity, number, pattern, redact, text, timestamp
from .storage import database
from .config import MAX_BATCH


class IdempotencyConflict(ValueError):
    pass


def ingest(kind, items, receipt=None):
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_BATCH or not all(isinstance(i, dict) for i in items):
        raise ValueError('Expected an array of 1–1000 objects')
    rows = []
    now = time.time()
    for item in items:
        service, env = identity(item)
        at = timestamp(item.get('time', now))
        if kind == 'logs':
            severity = text(item.get('severity', 'INFO')).upper()
            if severity not in ('TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL'):
                raise ValueError('Unsupported severity')
            message = redact(text(item.get('message'), 16384))
            if not message:
                raise ValueError('message required')
            rows.append((at, now, service, env, severity, message, pattern(message), identifier(item.get('trace_id'), 32, True), attributes(item)))
        elif kind == 'spans':
            duration = number(item.get('duration_ms', 0))
            if duration < 0:
                raise ValueError('Negative duration')
            status = text(item.get('status', 'UNSET'))
            if status not in ('UNSET', 'OK', 'ERROR'):
                raise ValueError('Invalid status')
            rows.append((identifier(item.get('trace_id'), 32), identifier(item.get('span_id'), 16), identifier(item.get('parent_id'), 16, True), at, duration, service, env, text(item.get('name', 'unnamed'), 500), status, attributes(item)))
        elif kind == 'samples':
            name = text(item.get('name'))
            if not re.fullmatch('[a-zA-Z_:][a-zA-Z0-9_:]*', name):
                raise ValueError('Invalid metric name')
            rows.append((at, service, env, name, number(item.get('value')), text(item.get('unit'), 32)))
        elif kind == 'events':
            rows.append((at, service, env, text(item.get('kind', 'change')), redact(text(item.get('message'), 2000))))
    sql = {'logs': 'INSERT INTO logs(time,received,service,environment,severity,message,pattern,trace_id,attributes) VALUES (?,?,?,?,?,?,?,?,?)',
           'spans': 'INSERT INTO spans VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(trace_id,span_id) DO NOTHING',
           'samples': 'INSERT INTO samples(time,service,environment,name,value,unit) VALUES (?,?,?,?,?,?)',
           'events': 'INSERT INTO events(time,service,environment,kind,message) VALUES (?,?,?,?,?)'}
    with database() as db:
        if receipt:
            from .storage import postgres_enabled,StorageError
            if not postgres_enabled():db.execute('BEGIN IMMEDIATE')
            receipt_key,body_hash=receipt
            db.execute('DELETE FROM ingest_receipts WHERE created_at<?',(now-86400,))
            row=db.execute('SELECT body_hash,accepted FROM ingest_receipts WHERE receipt_key=?',(receipt_key,)).fetchone()
            if not row:
                if db.execute('SELECT COUNT(*) FROM ingest_receipts').fetchone()[0]>=100000:
                    raise StorageError('Idempotency receipt capacity reached; retry later.')
                db.execute('INSERT INTO ingest_receipts VALUES (?,?,?,?) ON CONFLICT(receipt_key) DO NOTHING',(receipt_key,body_hash,-1,now))
                row=db.execute('SELECT body_hash,accepted FROM ingest_receipts WHERE receipt_key=?',(receipt_key,)).fetchone()
            if row['body_hash']!=body_hash:raise IdempotencyConflict('Idempotency key was already used for another payload')
            if row['accepted']>=0:return row['accepted']
        before = db.total_changes
        db.executemany(sql[kind], rows)
        accepted = db.total_changes - before
        if receipt:db.execute('UPDATE ingest_receipts SET accepted=? WHERE receipt_key=?',(accepted,receipt[0]))
    return accepted
