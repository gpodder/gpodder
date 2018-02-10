#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Simple HTTP web server for testing HTTP Authentication (see bug 1539)
# from our crappy-but-does-the-job department
# Thomas Perl <thp.io/about>; 2012-01-20

import http.server
import sys
import re
import hashlib
import datetime

USERNAME = 'user@example.com'    # Username used for HTTP Authentication
PASSWORD = 'secret'              # Password used for HTTP Authentication

HOST, PORT = 'localhost', 8000   # Hostname and port for the HTTP server

# When the script contents change, the feed's episodes each get a new GUID
GUID = hashlib.sha1(open(__file__).read()).hexdigest()

URL = 'http://%(HOST)s:%(PORT)s' % locals()

FEEDNAME = sys.argv[0]       # The title of the RSS feed
FEEDFILE = 'feed.rss'        # The "filename" of the feed on the server
EPISODES = 'episode'         # Base name for the episode files
EPISODES_EXT = '.mp3'        # Extension for the episode files
EPISODES_MIME = 'audio/mpeg' # Mime type for the episode files
EP_COUNT = 7                 # Number of episodes in the feed
SIZE = 500000                # Size (in bytes) of the episode downloads)


def mkpubdates(items):
    """Generate fake pubDates (one each day, recently)"""
    current = datetime.datetime.now() - datetime.timedelta(days=items+3)
    for i in range(items):
        yield current.ctime()
        current += datetime.timedelta(days=1)


def mkrss(items=EP_COUNT):
    """Generate a dumm RSS feed with a given number of items"""
    ITEMS = '\n'.join("""
    <item>
        <title>Episode %(INDEX)s</title>
        <guid>tag:test.gpodder.org,2012:%(GUID)s,%(URL)s,%(INDEX)s</guid>
        <pubDate>%(PUBDATE)s</pubDate>
        <enclosure
          url="%(URL)s/%(EPISODES)s%(INDEX)s%(EPISODES_EXT)s"
          type="%(EPISODES_MIME)s"
          length="%(SIZE)s"/>
    </item>
    """ % dict(list(locals().items())+list(globals().items()))
        for INDEX, PUBDATE in enumerate(mkpubdates(items)))

    return """
    <rss>
    <channel><title>%(FEEDNAME)s</title><link>%(URL)s</link>
    %(ITEMS)s
    </channel>
    </rss>
    """ % dict(list(locals().items())+list(globals().items()))


def mkdata(size=SIZE):
    """Generate dummy data of a given size (in bytes)"""
    return ''.join(chr(32+(i%(127-32))) for i in range(size))


class AuthRequestHandler(http.server.BaseHTTPRequestHandler):
    FEEDFILE_PATH = '/%s' % FEEDFILE
    EPISODES_PATH = '/%s' % EPISODES

    def do_GET(self):
        authorized = False
        is_feed = False
        is_episode = False

        auth_header = self.headers.get('authorization', '')
        m = re.match(r'^Basic (.*)$', auth_header)
        if m is not None:
            auth_data = m.group(1).decode('base64').split(':', 1)
            if len(auth_data) == 2:
                username, password = auth_data
                print('Got username:', username)
                print('Got password:', password)
                if (username, password) == (USERNAME, PASSWORD):
                    print('Valid credentials provided.')
                    authorized = True

        if self.path == self.FEEDFILE_PATH:
            print('Feed request.')
            is_feed = True
        elif self.path.startswith(self.EPISODES_PATH):
            print('Episode request.')
            is_episode = True

        if not authorized:
            print('Not authorized - sending WWW-Authenticate header.')
            self.send_response(401)
            self.send_header('WWW-Authenticate',
                    'Basic realm="%s"' % sys.argv[0])
            self.end_headers()
            self.wfile.close()
            return

        self.send_response(200)
        self.send_header('Content-type',
                'application/xml' if is_feed else 'audio/mpeg')
        self.end_headers()
        self.wfile.write(mkrss() if is_feed else mkdata())
        self.wfile.close()


if __name__ == '__main__':
    httpd = http.server.HTTPServer((HOST, PORT), AuthRequestHandler)
    print("""
    Feed URL: %(URL)s/%(FEEDFILE)s
    Username: %(USERNAME)s
    Password: %(PASSWORD)s
    """ % locals())
    while True:
        httpd.handle_request()

