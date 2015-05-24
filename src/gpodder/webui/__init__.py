# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2015 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# gpodder.webui - The basis for a gPodder Web UI
# Thomas Perl <thp@gpodder.org>; 2011-02-12


import gpodder

from gpodder import core
from gpodder import model
from gpodder import util


import BaseHTTPServer

try:
    # For Python < 2.6, we use the "simplejson" add-on module
    import simplejson as json
except ImportError:
    # Python 2.6 already ships with a nice "json" module
    import json

import os
import re
import sys

def to_json(o):
    return dict((key, getattr(o, key)) for key in o.__slots__ + ('id',))

def json_response(path_parts):
    core = WebUI.core

    if path_parts == ['podcasts.json']:
        return map(to_json, core.model.get_podcasts())
    elif (len(path_parts) == 3 and path_parts[0] == 'podcast' and
            path_parts[2] == 'episodes.json'):
        podcast_id = int(path_parts[1])
        for podcast in core.model.get_podcasts():
            if podcast.id == podcast_id:
                return map(to_json, podcast.get_all_episodes())

    return None

class WebUI(BaseHTTPServer.BaseHTTPRequestHandler):
    STATIC_PATH = os.path.join(gpodder.prefix, 'share', 'gpodder', 'ui', 'web')
    DEFAULT_PORT = 8086

    core = None

    @classmethod
    def run(cls, only_localhost=True, server_class=BaseHTTPServer.HTTPServer):
        if only_localhost:
            server_address = ('localhost', cls.DEFAULT_PORT)
        else:
            server_address = ('', cls.DEFAULT_PORT)
        print >>sys.stderr, """
    Server running. Point your web browser to:
    http://localhost:%s/

    Press Ctrl+C to stop the web server.
        """ % (cls.DEFAULT_PORT,)
        httpd = server_class(server_address, cls)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            del httpd

    def do_GET(self):
        if self.path == '/':
            self.path = '/static/index.html'

        path_parts = filter(None, self.path.split('/'))[1:]
        if '..' not in path_parts:
            if self.path.startswith('/static/'):
                filename = os.path.join(self.STATIC_PATH, *path_parts)
                _, extension = os.path.splitext(filename)
                mimetype = util.mimetype_from_extension(extension)

                self.send_response(200)
                self.send_header('Content-type', mimetype)
                self.end_headers()
                self.wfile.write(open(filename).read())
                self.wfile.close()
                return
            elif self.path.startswith('/json/'):
                data = json_response(path_parts)
                if data is not None:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(data))
                    self.wfile.close()
                    return

        self.send_response(400)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write('<p>Invalid request</p>')
        self.wfile.close()


def main(only_localhost=True, core=None):
    WebUI.core = core
    return WebUI.run(only_localhost)

