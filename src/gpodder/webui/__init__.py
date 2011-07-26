# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
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

import os
import re
import sys

class WebUI(BaseHTTPServer.BaseHTTPRequestHandler):
    DEFAULT_PORT = 8086

    core = None
    player = None

    @classmethod
    def run(cls, server_class=BaseHTTPServer.HTTPServer):
        server_address = ('', cls.DEFAULT_PORT)
        print >>sys.stderr, 'Listening on port %d...' % cls.DEFAULT_PORT
        httpd = server_class(server_address, cls)
        httpd.serve_forever()

    def do_GET(self):
        self.send_response(200)
        if re.match('/coverart/\d+', self.path):
            self.send_header('Content-type', 'image/jpeg')
        elif self.path == '/logo':
            self.send_header('Content-type', 'image/png')
        else:
            self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()

        if re.match('/coverart/\d+', self.path):
            id = int(self.path[10:])
            for podcast in model.Model.get_podcasts(self.core.db):
                if podcast.id == id:
                    self.wfile.write(open(podcast.cover_file).read())
                    break
            return
        elif self.path == '/logo':
            fn = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'gpodder.png')
            self.wfile.write(open(fn).read())
            return

        print >>self.wfile, """
        <html><head><title>gPodder WebUI</title>
        <style type="text/css">
          body {
              font-family: sans-serif;
              background-image: url(/logo);
              background-repeat: no-repeat;
          }
          h1 {
              margin: 0px;
              padding: 0px;
              padding-bottom: 30px;
              padding-left: 60px;
              font-size: 12pt;
          }
          ul {
              margin: 0px;
              padding: 0px;
              list-style: none;
          }
          li {
              padding-top: 1px;
          }
          li a {
              display: block;
              padding: 7px;
              background-color: #ccc;
          }
          a {
              color: black;
              text-decoration: none;
          }
          img {
              border: 0px;
              width: 30px;
              height: 30px;
              vertical-align: middle;
          }
        </style>
        </head>
        <body>
        """
        if self.path == '/podcast':
            print >>self.wfile, '<h1>Podcasts</h1><ul>'
            for podcast in model.Model.get_podcasts(self.core.db):
                print >>self.wfile, \
                        '<li><a href="/podcast/%d"><img src="/coverart/%d"> %s</a></li>' % \
                        (podcast.id, podcast.id, podcast.title + ' DLs:' + str(podcast.get_statistics()[3]))
        elif re.match('/podcast/\d+$', self.path):
            id = int(self.path[9:])
            for podcast in model.Model.get_podcasts(self.core.db):
                if podcast.id != id:
                    continue

                print >>self.wfile, '<h1><a href="/podcast">back</a> | %s</h1><ul>' % \
                        podcast.title

                for episode in podcast.get_all_episodes():
                    print >>self.wfile, '<li>'
                    if episode.was_downloaded(and_exists=True):
                        print >>self.wfile, '<strong>'
                    print >>self.wfile, '<a href="/podcast/%d/%d">%s</a>' % \
                            (podcast.id, episode.id, episode.title)
                    if episode.was_downloaded(and_exists=True):
                        print >>self.wfile, '</strong>'
                    print >>self.wfile, '</li>'
        elif re.match('/podcast/\d+/\d+', self.path):
            podcast_id, id= [int(x) for x in self.path[9:].split('/')]

            for podcast in model.Model.get_podcasts(self.core.db):
                if podcast.id != podcast_id:
                    continue

                for episode in podcast.get_all_episodes():
                    if episode.id == id:
                        print >>self.wfile, '<h1><a href="/podcast/%d">back</a> | %s</h1><ul>' % \
                                (podcast.id, episode.title)
                        print 'playing:', episode.local_filename(create=False)
                        if self.player is not None:
                            self.player.mediaPlay(episode.local_filename(create=False))
                            print >>self.wfile, repr(self.player.mediaPlayInfo()).replace('<', '&lt;')
                        print >>self.wfile, '<p>',episode.description,'</p>'
        else:
            self.wfile.write('<a href="/podcast">Podcasts</a>')


def main():
    WebUI.core = core.Core()
    try:
        import android
        WebUI.player = android.Android()
    except:
        pass
    return WebUI.run()

