import time
import base64
import hashlib
import json
import math
from .config import VERSION
from .storage import database, postgres_enabled
from .validation import text, identifier


def where(params, table='', end=None):
    prefix = table + '.' if table else ''
    minutes = int(params.get('minutes', '60'))
    if not 1 <= minutes <= 10080:
        raise ValueError('minutes must be 1–10080')
    clauses, values = [prefix + 'time >= ?'], [(time.time() if end is None else end) - minutes * 60]
    for field in ('service', 'environment'):
        if params.get(field):
            clauses.append(prefix + field + ' = ?')
            values.append(text(params[field]))
    return ' AND '.join(clauses), values


def log_filter_key(params):
    fields = ('minutes', 'service', 'environment', 'q', 'severity', 'trace_id')
    values = [str(params.get(k, '60' if k == 'minutes' else '')) for k in fields]
    return hashlib.sha256(json.dumps(values, separators=(',', ':')).encode()).hexdigest()


def log_cursor(params):
    value = params.get('cursor', '')
    if not value:
        return time.time(), None, None
    try:
        if not isinstance(value, str) or len(value) > 512:
            raise ValueError()
        version, end, stamp, ident, maximum, scope = json.loads(base64.urlsafe_b64decode(value + '=' * (-len(value) % 4)))
        if (type(version) is not int or version != 1 or type(end) not in (int, float) or type(stamp) not in (int, float)
                or not math.isfinite(end) or not math.isfinite(stamp)
                or not time.time() - 3600 <= end <= time.time() + 5
                or not end - int(params.get('minutes', '60')) * 60 <= stamp <= end
                or type(maximum) is not int or not 0 < maximum <= 2**63 - 1
                or type(ident) is not int or not 0 < ident <= maximum
                or scope != log_filter_key(params)):
            raise ValueError()
        return end, (stamp, ident), maximum
    except (ValueError, TypeError, OverflowError, UnicodeError):
        raise ValueError('Invalid or expired log cursor; refresh the search.') from None


def next_log_cursor(params, end, maximum, row):
    data = [1, end, row['time'], row['id'], maximum, log_filter_key(params)]
    return base64.urlsafe_b64encode(json.dumps(data, separators=(',', ':')).encode()).decode().rstrip('=')

def query_view(view, params):
    end, position, maximum = log_cursor(params) if view == 'logs' else (None, None, None)
    clause, args = where(params, end=end)
    with database() as db:
        if view == 'overview':
            services = [dict(r) for r in db.execute(f'''SELECT service,environment,COUNT(*) logs,
                SUM(CASE WHEN severity IN ('ERROR','FATAL') THEN 1 ELSE 0 END) errors, MAX(time) last_seen
                FROM logs WHERE {clause} GROUP BY service,environment ORDER BY errors DESC LIMIT 200''', args)]
            totals = dict(db.execute(f"SELECT COUNT(*) logs, COALESCE(SUM(CASE WHEN severity IN ('ERROR','FATAL') THEN 1 ELSE 0 END),0) errors, COUNT(DISTINCT trace_id) FILTER(WHERE trace_id != '') linked_traces FROM logs WHERE {clause}", args).fetchone())
            totals['spans'] = db.execute(f'SELECT COUNT(*) FROM spans WHERE {clause}', args).fetchone()[0]
            series = [dict(r) for r in db.execute(f'''SELECT CAST(FLOOR(time/60) AS BIGINT)*60 time,
                COUNT(*) logs,SUM(CASE WHEN severity IN ('ERROR','FATAL') THEN 1 ELSE 0 END) errors FROM logs WHERE {clause} GROUP BY 1 ORDER BY 1''', args)]
            # Include resources observed only through spans or host samples.
            known = {(s['service'],s['environment']) for s in services}
            for table in ('samples', 'spans'):
                for r in db.execute(f'SELECT service,environment,MAX(time) last_seen FROM {table} WHERE {clause} GROUP BY service,environment LIMIT 200', args):
                    if (r['service'],r['environment']) not in known:
                        services.append(dict(r, logs=0, errors=0))
                        known.add((r['service'],r['environment']))
            return {'totals': totals, 'services': services[:200], 'series': series, 'version': VERSION}
        if view == 'logs':
            if params.get('q'):
                clause += " AND LOWER(message) LIKE LOWER(?) ESCAPE '\\'"
                escaped = params['q'].replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
                args.append('%' + text(escaped, 500) + '%')
            for field in ('severity', 'trace_id'):
                if params.get(field):
                    clause += ' AND ' + field + ' = ?'
                    args.append(text(params[field]))
            if maximum is None:
                maximum = db.execute('SELECT COALESCE(MAX(id),0) FROM logs').fetchone()[0]
            clause += ' AND time <= ? AND id <= ?'
            args.extend([end, maximum])
            offset = max(0, min(100000, int(params.get('offset', 0)))) if position is None else 0
            if position is not None:
                clause += ' AND (time,id) < (?,?)'
                args.extend(position)
            # One look-ahead row answers has_more without counting the full dataset.
            rows = [dict(r) for r in db.execute(f'SELECT * FROM logs WHERE {clause} ORDER BY time DESC,id DESC LIMIT 101 OFFSET ?', [*args,offset])]
            more = len(rows) > 100
            rows = rows[:100]
            return {'items': rows, 'offset': offset, 'has_more': more,
                    'next_cursor': next_log_cursor(params, end, maximum, rows[-1]) if more else None,
                    'snapshot_end': end}
        if view == 'patterns':
            return {'items': [dict(r) for r in db.execute(f'''SELECT service,environment,pattern,COUNT(*) occurrences,
                SUM(CASE WHEN severity IN ('ERROR','FATAL') THEN 1 ELSE 0 END) errors,MIN(time) first_seen,MAX(time) last_seen
                FROM logs WHERE {clause} GROUP BY service,environment,pattern ORDER BY errors DESC,occurrences DESC LIMIT 100''', args)]}
        if view == 'traces':
            if params.get('trace_id'):
                clause += ' AND trace_id = ?'
                args.append(identifier(params['trace_id'],32))
                return {'items':[dict(r) for r in db.execute(f'SELECT * FROM spans WHERE {clause} ORDER BY time LIMIT 1000', args)]}
            aggregate = "STRING_AGG(DISTINCT service, ',')" if postgres_enabled() else 'GROUP_CONCAT(DISTINCT service)'
            return {'items':[dict(r) for r in db.execute(f'''SELECT trace_id,COUNT(*) spans,MIN(time) time,MAX(time+duration_ms/1000)-MIN(time) duration_s,
                {aggregate} services,SUM(CASE WHEN status='ERROR' THEN 1 ELSE 0 END) errors FROM spans WHERE {clause} GROUP BY trace_id ORDER BY time DESC LIMIT 100''',args)]}
        if view == 'samples':
            return {'items':[dict(r) for r in db.execute(f'SELECT * FROM samples WHERE {clause} ORDER BY time DESC LIMIT 2000',args)]}
        if view == 'events':
            return {'items':[dict(r) for r in db.execute(f'SELECT * FROM events WHERE {clause} ORDER BY time DESC LIMIT 100',args)]}
    raise ValueError('Unknown view')
