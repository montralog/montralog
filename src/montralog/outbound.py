"""Direct, DNS-pinned HTTP transport. No proxies, redirects or TLS bypasses."""
import http.client
import ipaddress
import os
import socket
import ssl
import threading
import time
import urllib.parse
from contextlib import contextmanager


class DestinationError(ValueError):
    pass


def endpoint(raw):
    if not isinstance(raw, str) or len(raw) > 2000 or any(ord(c) < 33 or ord(c) == 127 for c in raw) or '\\' in raw:
        raise DestinationError('Invalid endpoint URL.')
    try:
        parsed = urllib.parse.urlsplit(raw)
        port = parsed.port if parsed.port is not None else (443 if parsed.scheme == 'https' else 80)
    except ValueError:
        raise DestinationError('Invalid endpoint URL.') from None
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.fragment or '%' in parsed.hostname or not 1 <= port <= 65535:
        raise DestinationError('Use an HTTP(S) endpoint without embedded credentials or fragment.')
    return parsed, port


def destination(raw, private_origins=()):
    parsed, port = endpoint(raw)
    host = parsed.hostname.lower().rstrip('.')
    if host in ('metadata', 'metadata.google.internal', 'instance-data'):
        raise DestinationError('Metadata endpoints are forbidden.')
    allowed = {x.strip().lower() for x in os.getenv('MONTRALOG_ALLOWED_DESTINATIONS', '').split(',') if x.strip()}
    allowed.update(private_origins)
    try:
        resolved = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        addresses = list(dict.fromkeys(entry[4][0] for entry in resolved))
        if not addresses:
            raise DestinationError('Endpoint did not resolve.')
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if ip.version == 6 and ip.ipv4_mapped:
                ip = ip.ipv4_mapped
            if ip.version==6 and (ip.sixtofour or ip.teredo or ip in ipaddress.ip_network('64:ff9b::/96') or ip in ipaddress.ip_network('64:ff9b:1::/48')):
                raise DestinationError('IPv4 translation and tunnel destinations are not supported.')
            if ip.is_link_local or ip.is_multicast or ip.is_unspecified or str(ip) in ('100.100.100.200', 'fd00:ec2::254'):
                raise DestinationError('Metadata, link-local, multicast and unspecified destinations are forbidden.')
            if not ip.is_global and f'{host}:{port}' not in allowed:
                raise DestinationError('Private destinations require an operator allowlist entry (hostname:port).')
    except (OSError, ValueError) as error:
        if isinstance(error, DestinationError):
            raise
        raise DestinationError('Endpoint DNS resolution failed.') from None
    return parsed, port, addresses


@contextmanager
def open_request(request, timeout=8, private_origins=(), insecure_credential_origin=None, require_private=False):
    parsed, port, addresses = destination(request.full_url, private_origins)
    if require_private and any(ipaddress.ip_address(address).is_global for address in addresses):
        raise DestinationError('Local-only destination resolved outside the private network.')
    if request.has_header('Authorization') or request.data is not None:
        if parsed.scheme != 'https' and (parsed.hostname, port) != insecure_credential_origin:
            raise DestinationError('Credentials and request bodies require HTTPS.')
    # Resolve exactly once. Connect to a numeric address, preserving the original
    # Host header and TLS SNI/certificate verification. Environment proxies are ignored.
    connection = http.client.HTTPConnection(parsed.hostname, port, timeout=timeout)
    sock = None
    deadline = time.monotonic() + timeout
    def expire():
        active = sock
        if active is not None:
            try: active.shutdown(socket.SHUT_RDWR)
            except OSError: pass
            active.close()
    timer = threading.Timer(timeout, expire)
    timer.daemon = True
    timer.start()
    try:
        for address in addresses:
            try:
                family = socket.AF_INET6 if ':' in address else socket.AF_INET
                sock = socket.socket(family, socket.SOCK_STREAM)
                remaining = deadline - time.monotonic()
                if remaining <= 0: raise TimeoutError("Endpoint deadline exceeded")
                sock.settimeout(remaining)
                sock.connect((address, port))
                break
            except OSError:
                if sock is not None:
                    sock.close()
                sock = None
        if sock is None:
            raise OSError('Endpoint connection failed')
        if parsed.scheme == 'https':
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=parsed.hostname)
        connection.sock = sock
        path = urllib.parse.urlunsplit(('', '', parsed.path or '/', parsed.query, ''))
        connection.request(request.get_method(), path, body=request.data, headers=dict(request.header_items()))
        response = connection.getresponse()
        if not 200 <= response.status < 300:
            raise DestinationError('Endpoint returned a non-success status; redirects are forbidden.')
        yield response
    except http.client.HTTPException:
        raise DestinationError('Endpoint returned an invalid HTTP response.') from None
    finally:
        timer.cancel()
        connection.close()
        if sock is not None:
            sock.close()
