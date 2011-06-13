# -*- coding: utf-8 -*-
# gpodder.net API Client
# Copyright (C) 2009-2010 Thomas Perl
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from mygpoclient import http

import unittest
import multiprocessing
import BaseHTTPServer

def http_server(port, username, password, response):
    storage = {}
    class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

        def _checks(self):
            if not self._check_auth():
                return False
            elif not self._check_errors():
                return False
            else:
                return True

        def _check_auth(self):
            if self.path.startswith('/auth'):
                authorization = self.headers.get('authorization', None)
                if authorization is not None:
                    auth_type, credentials = authorization.split(None, 1)
                    if auth_type.lower() == 'basic':
                        auth_user, auth_pass = credentials.decode('base64').split(':', 1)
                        if username == auth_user and password == auth_pass:
                            return True

                self.send_response(401)
                self.send_header('WWW-Authenticate', 'Basic realm="Fake HTTP Server"')
                self.end_headers()
                self.wfile.close()
                return False

            return True

        def _check_errors(self):
            if self.path.startswith('/badrequest'):
                self.send_response(400)
                self.end_headers()
                self.wfile.close()
                return False
            elif self.path.startswith('/notfound'):
                self.send_response(404)
                self.end_headers()
                self.wfile.close()
                return False
            elif self.path.startswith('/invaliderror'):
                self.send_response(444)
                self.end_headers()
                self.wfile.close()
                return False

            return True

        def do_POST(self):
            if not self._checks():
                return

            input_data = self.rfile.read(int(self.headers.get('content-length')))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(input_data.encode('rot13'))
            self.wfile.close()

        def do_PUT(self):
            if not self._checks():
                return

            input_data = self.rfile.read(int(self.headers.get('content-length')))
            storage[self.path] = input_data
            self.send_response(200)
            self.end_headers()
            self.wfile.write('PUT OK')
            self.wfile.close()

        def do_GET(self):
            if not self._checks():
                return

            self.send_response(200)
            self.end_headers()
            if self.path in storage:
                self.wfile.write(storage[self.path])
            else:
                self.wfile.write(response)
            self.wfile.close()

        def log_request(*args):
            pass

    BaseHTTPServer.HTTPServer(('127.0.0.1', port), Handler).serve_forever()

class Test_HttpClient(unittest.TestCase):
    USERNAME = 'john'
    PASSWORD = 'secret'
    PORT = 9876
    URI_BASE = 'http://localhost:%(PORT)d' % locals()
    RESPONSE = 'Test_GET-HTTP-Response-Content'
    DUMMYDATA = 'fq28cnyp3ya8ltcy;ny2t8ay;iweuycowtc'

    def setUp(self):
        self.server_process = multiprocessing.Process(target=http_server,
                args=(self.PORT, self.USERNAME, self.PASSWORD, self.RESPONSE))
        self.server_process.start()

    def tearDown(self):
        self.server_process.terminate()
        import time
        time.sleep(.1)

    def test_UnknownResponse(self):
        client = http.HttpClient()
        path = self.URI_BASE+'/invaliderror'
        self.assertRaises(http.UnknownResponse, client.GET, path)

    def test_NotFound(self):
        client = http.HttpClient()
        path = self.URI_BASE+'/notfound'
        self.assertRaises(http.NotFound, client.GET, path)

    def test_Unauthorized(self):
        client = http.HttpClient('invalid-username', 'invalid-password')
        path = self.URI_BASE+'/auth'
        self.assertRaises(http.Unauthorized, client.GET, path)

    def test_BadRequest(self):
        client = http.HttpClient()
        path = self.URI_BASE+'/badrequest'
        self.assertRaises(http.BadRequest, client.GET, path)

    def test_GET(self):
        client = http.HttpClient()
        path = self.URI_BASE+'/noauth'
        self.assertEquals(client.GET(path), self.RESPONSE)

    def test_authenticated_GET(self):
        client = http.HttpClient(self.USERNAME, self.PASSWORD)
        path = self.URI_BASE+'/auth'
        self.assertEquals(client.GET(path), self.RESPONSE)

    def test_unauthenticated_GET(self):
        client = http.HttpClient()
        path = self.URI_BASE+'/auth'
        self.assertRaises(http.Unauthorized, client.GET, path)

    def test_POST(self):
        client = http.HttpClient()
        path = self.URI_BASE+'/noauth'
        self.assertEquals(client.POST(path, self.DUMMYDATA), self.DUMMYDATA.encode('rot13'))

    def test_authenticated_POST(self):
        client = http.HttpClient(self.USERNAME, self.PASSWORD)
        path = self.URI_BASE+'/auth'
        self.assertEquals(client.POST(path, self.DUMMYDATA), self.DUMMYDATA.encode('rot13'))

    def test_unauthenticated_POST(self):
        client = http.HttpClient()
        path = self.URI_BASE+'/auth'
        self.assertRaises(http.Unauthorized, client.POST, path, self.DUMMYDATA)

    def test_PUT(self):
        client = http.HttpClient()
        path = self.URI_BASE+'/noauth'
        self.assertEquals(client.PUT(path, self.DUMMYDATA), 'PUT OK')

    def test_GET_after_PUT(self):
        client = http.HttpClient()
        for i in range(10):
            path = self.URI_BASE + '/file.%(i)d.txt' % locals()
            client.PUT(path, self.RESPONSE + str(i))
            self.assertEquals(client.GET(path), self.RESPONSE + str(i))


