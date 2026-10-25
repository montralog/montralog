import io
import os
import socket
import unittest
import urllib.request
from unittest.mock import MagicMock, patch
from montralog import outbound, connections


def resolved(address):
    return [(socket.AF_INET6 if ':' in address else socket.AF_INET, socket.SOCK_STREAM, 6, '', (address, 443))]


class OutboundTests(unittest.TestCase):
    def test_invalid_endpoints_never_resolve(self):
        for url in ('file:///etc/passwd', 'https://user:secret@host', 'https://host:99999', 'https://host:0', 'https://host\\@elsewhere', 'https://host\r\nx:1', 'https://[::1', 'https://host/%20#fragment', 'https://[fe80::1%eth0]'):
            with self.subTest(url=url), patch.object(socket, 'getaddrinfo') as dns:
                with self.assertRaises(outbound.DestinationError): outbound.destination(url)
                dns.assert_not_called()

    def test_private_addresses_require_operator_approval_and_metadata_never_allowed(self):
        for address in ('127.0.0.1', '10.1.2.3', '192.168.1.1', '::1', '::ffff:127.0.0.1'):
            with self.subTest(address=address), patch.dict(os.environ, {'MONTRALOG_ALLOWED_DESTINATIONS': ''}), patch.object(socket, 'getaddrinfo', return_value=resolved(address)):
                with self.assertRaises(outbound.DestinationError): outbound.destination('https://metrics.example')
                self.assertEqual(outbound.destination('https://metrics.example', ('metrics.example:443',))[2], [address])
        for address in ('169.254.169.254', 'fd00:ec2::254', '100.100.100.200', '224.0.0.1', '0.0.0.0'):
            with self.subTest(address=address), patch.object(socket, 'getaddrinfo', return_value=resolved(address)):
                with self.assertRaises(outbound.DestinationError): outbound.destination('https://metrics.example', ('metrics.example:443',))

    def test_mixed_dns_answers_fail_closed(self):
        with patch.dict(os.environ, {'MONTRALOG_ALLOWED_DESTINATIONS': ''}), patch.object(socket, 'getaddrinfo', return_value=resolved('8.8.8.8') + resolved('127.0.0.1')):
            with self.assertRaises(outbound.DestinationError): outbound.destination('https://metrics.example')

    def test_http_credentials_never_reach_socket(self):
        req = urllib.request.Request('http://metrics.example/api', headers={'Authorization': 'Bearer fixture-secret'})
        with patch.object(socket, 'getaddrinfo', return_value=resolved('8.8.8.8')), patch.object(socket, 'socket') as sock:
            with self.assertRaises(outbound.DestinationError):
                with outbound.open_request(req): pass
            sock.assert_not_called()

    def test_dns_change_between_validation_and_request_is_rejected(self):
        source = {'url': 'https://metrics.example', 'auth_type': 'bearer', 'secret': 'fixture-secret'}
        with patch.dict(os.environ, {'MONTRALOG_ALLOWED_DESTINATIONS': '', 'PROMETHEUS_URL': ''}), patch.object(socket, 'getaddrinfo', side_effect=[resolved('8.8.8.8'), resolved('127.0.0.1')]), patch.object(socket, 'socket') as sock:
            self.assertFalse(connections.query(source, 'query')['available'])
            sock.assert_not_called()

    def test_connection_pins_numeric_ip_preserves_tls_hostname_and_disables_redirects(self):
        req = urllib.request.Request('https://metrics.example/api?query=up', headers={'Authorization': 'Bearer fixture-secret'})
        for status in (200, 301, 302, 303, 307, 308):
            response = io.BytesIO(b'{}'); response.status = status
            connection = MagicMock(); connection.getresponse.return_value = response
            sock = MagicMock(); context = MagicMock(); context.wrap_socket.return_value = sock
            with self.subTest(status=status), patch.object(socket, 'getaddrinfo', side_effect=[resolved('8.8.8.8'), resolved('127.0.0.1')]) as dns, patch.object(socket, 'socket', return_value=sock), patch.object(outbound.ssl, 'create_default_context', return_value=context), patch.object(outbound.http.client, 'HTTPConnection', return_value=connection):
                if status == 200:
                    with outbound.open_request(req) as received: self.assertEqual(received.read(), b'{}')
                else:
                    with self.assertRaises(outbound.DestinationError):
                        with outbound.open_request(req): pass
                self.assertEqual(dns.call_count, 1)
                sock.connect.assert_called_once_with(('8.8.8.8', 443))
                context.wrap_socket.assert_called_once_with(sock, server_hostname='metrics.example')
                connection.request.assert_called_once()
                connection.close.assert_called_once()

    def test_private_allowlist_is_exact_host_and_port(self):
        with patch.dict(os.environ, {'MONTRALOG_ALLOWED_DESTINATIONS': 'metrics.example:9090'}), patch.object(socket, 'getaddrinfo', return_value=resolved('10.0.0.2')):
            outbound.destination('http://metrics.example:9090')
            for url in ('http://metrics.example:9091', 'http://evil.metrics.example:9090'):
                with self.assertRaises(outbound.DestinationError): outbound.destination(url)
