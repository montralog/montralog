import json
import math
import re
import time


def text(value, maximum=200, default=''):
    if value is None:
        value = default
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError('Invalid text field')
    return value

def number(value):
    if isinstance(value, bool):
        raise ValueError('Expected finite number')
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('Expected finite number')
    return result

def timestamp(value):
    result = number(value)
    if result < 0 or result > time.time() + 300:
        raise ValueError('Timestamp outside supported range')
    return result

def identity(item):
    service = text(item.get('service'))
    if not service.strip():
        raise ValueError('service is required')
    return service, text(item.get('environment'), default='default')

def identifier(value, size, optional=False):
    result = text(value, size)
    if not result and optional:
        return ''
    if not re.fullmatch('[0-9a-fA-F]{' + str(size) + '}', result) or int(result, 16) == 0:
        raise ValueError('Invalid trace/span identifier')
    return result.lower()

def redact(message):
    # Best-effort defaults, not a guarantee that logs contain no sensitive data.
    message = re.sub(r'(?i)Bearer\s+[A-Za-z0-9._~+/=-]+', 'Bearer [REDACTED]', message)
    message = re.sub(r'(?i)(password|passwd|token|secret|authorization|api[_-]?key)([\s"\x27:=]+)([^\s,;"\x27}]+)', r'\1\2[REDACTED]', message)
    return message

def pattern(message):
    message = re.sub(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}\b', '<uuid>', message)
    message = re.sub(r'\b[0-9a-fA-F]{16,}\b', '<id>', message)
    return re.sub(r'\b\d+(?:\.\d+)*\b', '<n>', message)

def attributes(item):
    value = item.get('attributes', {})
    if not isinstance(value, dict) or len(value) > 64:
        raise ValueError('attributes must be an object with at most 64 keys')
    encoded = json.dumps(value, allow_nan=False)
    if len(encoded) > 16384:
        raise ValueError('attributes too large')
    # Apply redaction to individual strings rather than serialized JSON syntax.
    def clean(obj):
        if isinstance(obj, dict):
            return {k: '[REDACTED]' if re.search(r'(?i)password|token|secret|authorization|api.?key', k) else clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [clean(v) for v in obj]
        return redact(obj) if isinstance(obj, str) else obj
    return json.dumps(clean(value), allow_nan=False)
