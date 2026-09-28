"""Connection defaults, remote routing and Digest authentication regression tests."""
import importlib.util, pathlib, unittest
from unittest.mock import patch
import requests
from fritzconnection import FritzConnection
spec = importlib.util.spec_from_file_location('remote_connection', pathlib.Path(__file__).resolve().parents[1] / 'custom_components/fritzbox_netzwerk/connection.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Tests(unittest.TestCase):

    def test_urls(self):
        for path, want in [('/tr64desc.xml', '/tr064/tr64desc.xml'), ('/upnp/control/hosts', '/tr064/upnp/control/hosts'), ('/tr064/hosts.xml?sid=abc', '/tr064/hosts.xml?sid=abc')]:
            self.assertEqual(m.remote_url('http://box:49000' + path, 'box', 65443), 'https://box:65443' + want)
        self.assertEqual(m.remote_url('https://other/x', 'box', 65443), 'https://other/x')

    def test_local_and_remote(self):
        with patch.object(FritzConnection, '_load_router_api'), patch.object(FritzConnection, '_reset_user'):
            data = {'host': 'box', 'username': 'test', 'password': 'test'}
            local = m.create_connection(data)
            self.assertEqual(local.port, 49000)
            self.assertEqual(type(local), FritzConnection)
            secure = m.create_connection(dict(data, use_tls=True))
            self.assertEqual(secure.port, 49443)
            remote = m.create_connection(dict(data, remote_access=True, port=65443))
            self.assertEqual(remote.port, 65443)
            self.assertEqual(remote.address, 'https://box')
            default = m.create_connection(dict(data, remote_access=True))
            self.assertEqual(default.port, 443)
            auth = remote.session.auth
            auth.init_per_thread_state()
            auth._thread_local.chal = {'realm': 'test', 'nonce': 'abc', 'qop': 'auth', 'algorithm': 'MD5'}
            auth._thread_local.last_nonce = 'abc'
            captured = []

            def send(session, request, **kwargs):
                captured.append(request)
                r = requests.Response()
                r.status_code = 200
                r._content = b'ok'
                r.request = request
                return r
            with patch.object(requests.Session, 'send', send):
                remote.session.post('https://box:65443/upnp/control/hosts', data='soap')
                remote.session.get('https://box:65443/tr64desc.xml')
                local.session.get('http://box:49000/tr64desc.xml')
            self.assertEqual(captured[0].url, 'https://box:65443/tr064/upnp/control/hosts')
            self.assertIn('uri="/tr064/upnp/control/hosts"', captured[0].headers['Authorization'])
            self.assertEqual(captured[1].url, 'https://box:65443/tr064/tr64desc.xml')
            self.assertEqual(captured[2].url, 'http://box:49000/tr64desc.xml')
if __name__ == '__main__':
    unittest.main()
