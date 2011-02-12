# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2010 Thomas Perl and the gPodder Team
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

import BaseHTTPServer


class WebUI(BaseHTTPServer.BaseHTTPRequestHandler):
    core = None

    @classmethod
    def run(cls, server_class=BaseHTTPServer.HTTPServer):
        server_address = ('', 8086)
        httpd = server_class(server_address, cls)
        httpd.serve_forever()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        if self.path == '/podcasts':
            print >>self.wfile, '<h1>Podcasts</h1>'
            for podcast in model.Model.get_podcasts(self.core.db):
                print >>self.wfile, '<li>', podcast.title, '<code>', \
                        podcast.get_statistics(), '</code></li>'
        else:
            self.wfile.write('<a href="/podcasts">Podcasts</a>')


def main():
    WebUI.core = core.Core()
    return WebUI.run()

