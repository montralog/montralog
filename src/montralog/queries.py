import time
from .config import VERSION
from .storage import database, postgres_enabled
from .validation import text, identifier


def where(params, table=''):
    prefix = table + '.' if table else ''
    minutes = int(params.get('minutes', '60'))
    if not 1 <= minutes <= 10080:
        raise ValueError('minutes must be 1–10080')
    clauses, values = [prefix + 'time >= ?'], [time.time() - minutes * 60]
    for field in ('service', 'environment'):
        if params.get(field):
            clauses.append(prefix + field + ' = ?')
            values.append(text(params[field]))
    return ' AND '.join(clauses), values

def query_view(view, params):
    clause, args = where(params)
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
            offset = max(0, min(100000, int(params.get('offset', 0))))
            rows = [dict(r) for r in db.execute(f'SELECT * FROM logs WHERE {clause} ORDER BY time DESC,id DESC LIMIT 100 OFFSET ?', [*args,offset])]
            return {'items': rows, 'offset': offset, 'has_more': db.execute(f'SELECT COUNT(*) FROM logs WHERE {clause}', args).fetchone()[0] > offset+100}
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
