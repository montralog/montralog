import json
import time
from .ingestion import ingest


def otel_attributes(entries):
    out = {}
    for entry in entries:
        value = entry.get('value', {})
        out[entry['key']] = next(iter(value.values()), '')
    return out

def otel_logs_or_spans(payload, kind):
    root, scopes, records = ('resourceLogs', 'scopeLogs', 'logRecords') if kind == 'logs' else ('resourceSpans', 'scopeSpans', 'spans')
    if not isinstance(payload, dict) or root not in payload or not isinstance(payload[root], list):
        raise ValueError('Expected OTLP JSON envelope')
    items = []
    for resource in payload[root]:
        attrs = otel_attributes(resource.get('resource', {}).get('attributes', []))
        for scope in resource.get(scopes, []):
            for record in scope.get(records, []):
                item = {'service': attrs.get('service.name', 'unknown'), 'environment': attrs.get('deployment.environment.name', attrs.get('deployment.environment', 'default')),
                        'attributes': {**attrs, **otel_attributes(record.get('attributes', []))}, 'trace_id': record.get('traceId', '')}
                if kind == 'logs':
                    ns = int(record.get('timeUnixNano') or record.get('observedTimeUnixNano') or 0)
                    severity = int(record.get('severityNumber', 0))
                    body = record.get('body', {})
                    item.update(time=ns / 1e9 if ns else time.time(), message=str(body.get('stringValue', json.dumps(body))),
                                severity=('FATAL' if severity >= 21 else 'ERROR' if severity >= 17 else 'WARN' if severity >= 13 else 'INFO' if severity >= 9 else 'DEBUG' if severity >= 5 else 'TRACE'))
                else:
                    start, end = int(record['startTimeUnixNano']), int(record['endTimeUnixNano'])
                    item.update(time=start / 1e9, duration_ms=(end-start)/1e6, span_id=record['spanId'], parent_id=record.get('parentSpanId', ''), name=record.get('name', 'unnamed'), status={0:'UNSET',1:'OK',2:'ERROR'}.get(record.get('status', {}).get('code', 0), 'UNSET'))
                items.append(item)
    return ingest(kind, items) if items else 0
