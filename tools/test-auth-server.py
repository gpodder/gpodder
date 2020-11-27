#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Simple HTTP web server for testing HTTP Authentication (see bug 1539)
# from our crappy-but-does-the-job department
# Thomas Perl <thp.io/about>; 2012-01-20

import base64
import datetime
import hashlib
import http.server
import re
import sys
import threading
import time

USERNAME = 'user@example.com'    # Username used for HTTP Authentication
PASSWORD = 'secret'              # Password used for HTTP Authentication

HOST, PORT, RPORT = 'localhost', 8000, 8001   # Hostname and port for the HTTP server

# When the script contents change, the feed's episodes each get a new GUID
GUID = hashlib.sha1(open(__file__, mode='rb').read()).hexdigest()

URL = 'http://%(HOST)s:%(PORT)s' % locals()

FEEDNAME = sys.argv[0]        # The title of the RSS feed
REDIRECT = 'redirect.rss'     # The path for a redirection
REDIRECT_TO_BAD_HOST = 'redirect_bad'     # The path for a redirection
FEEDFILE = 'feed.rss'         # The "filename" of the feed on the server
EPISODES = 'episode'          # Base name for the episode files
TIMEOUT = 'timeout'           # The path to never return
EPISODES_EXT = '.mp3'         # Extension for the episode files
EPISODES_MIME = 'audio/mpeg'  # Mime type for the episode files
EP_COUNT = 7                  # Number of episodes in the feed
SIZE = 500000                 # Size (in bytes) of the episode downloads)


def mkpubdates(items):
    """Generate fake pubDates (one each day, recently)"""
    current = datetime.datetime.now() - datetime.timedelta(days=items + 3)
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
    """ % dict(list(locals().items()) + list(globals().items()))
        for INDEX, PUBDATE in enumerate(mkpubdates(items)))
    ITEMS += """
    <item>
        <title>Missing Episode</title>
        <guid>tag:test.gpodder.org,2012:missing</guid>
        <pubDate>Sun, 25 Nov 2018 17:28:03 +0000</pubDate>
        <enclosure
          url="%(URL)s/not_there%(EPISODES_EXT)s"
          type="%(EPISODES_MIME)s"
          length="%(SIZE)s"/>
    </item>""" % dict(list(locals().items()) + list(globals().items()))
    ITEMS += """
    <item>
        <title>Server Timeout Episode</title>
        <guid>tag:test.gpodder.org,2012:timeout</guid>
        <pubDate>Sun, 25 Nov 2018 17:28:03 +0000</pubDate>
        <enclosure
          url="%(URL)s/%(TIMEOUT)s"
          type="%(EPISODES_MIME)s"
          length="%(SIZE)s"/>
    </item>""" % dict(list(locals().items()) + list(globals().items()))
    ITEMS += """
    <item>
        <title>Bad Host Episode</title>
        <guid>tag:test.gpodder.org,2012:timeout</guid>
        <pubDate>Sun, 25 Nov 2018 17:28:03 +0000</pubDate>
        <enclosure
          url="%(URL)s/%(REDIRECT_TO_BAD_HOST)s"
          type="%(EPISODES_MIME)s"
          length="%(SIZE)s"/>
    </item>""" % dict(list(locals().items()) + list(globals().items()))
    ITEMS += """
    <item>
        <title>Space in url Episode</title>
        <guid>tag:test.gpodder.org,2012:timeout</guid>
        <pubDate>Sun, 25 Nov 2018 17:28:03 +0000</pubDate>
        <enclosure
          url="%(URL)s/%(EPISODES)s with space%(EPISODES_EXT)s"
          type="%(EPISODES_MIME)s"
          length="%(SIZE)s"/>
    </item>""" % dict(list(locals().items()) + list(globals().items()))

    return """
    <rss>
    <channel><title>%(FEEDNAME)s</title><link>%(URL)s</link>
    %(ITEMS)s
    </channel>
    </rss>
    """ % dict(list(locals().items()) + list(globals().items()))


def mkdata(size=SIZE):
    """Generate dummy data of a given size (in bytes)"""
    return bytes([32 + (i % (127 - 32)) for i in range(size)])


class AuthRequestHandler(http.server.BaseHTTPRequestHandler):
    FEEDFILE_PATH = '/%s' % FEEDFILE
    EPISODES_PATH = '/%s' % EPISODES
    REDIRECT_PATH = '/%s' % REDIRECT
    REDIRECT_TO_BAD_HOST_PATH = '/%s' % REDIRECT_TO_BAD_HOST
    TIMEOUT_PATH = '/%s' % TIMEOUT

    def do_GET(self):
        authorized = False
        is_feed = False
        is_episode = False

        auth_header = self.headers.get('authorization', '')
        m = re.match(r'^Basic (.*)$', auth_header)
        if m is not None:
            auth_data = base64.b64decode(m.group(1)).decode().split(':', 1)
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
        elif self.path == self.REDIRECT_PATH:
            print('Redirect request.')
            self.send_response(302)
            self.send_header('Location', '%s/%s' % (URL, FEEDFILE))
            self.end_headers()
            return
        elif self.path.startswith(self.REDIRECT_TO_BAD_HOST_PATH):
            print('Redirect request => bad host.')
            self.send_response(302)
            self.send_header('Location', '//notthere.gpodder.io/%s' % (FEEDFILE))
            self.end_headers()
            return
        elif self.path == self.TIMEOUT_PATH:
            # will need to restart the server or wait 80s before next request
            time.sleep(80)
            return

        if not authorized:
            print('Not authorized - sending WWW-Authenticate header.')
            self.send_response(401)
            self.send_header('WWW-Authenticate',
                             'Basic realm="%s"' % sys.argv[0])
            self.end_headers()
            return
        if not is_feed and not is_episode:
            print('Not there episode - sending 404.')
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header('Content-type',
                         'application/xml' if is_feed else 'audio/mpeg')
        self.end_headers()
        self.wfile.write(mkrss().encode('utf-8') if is_feed else mkdata())


def run(httpd):
    while True:
        httpd.handle_request()


if __name__ == '__main__':
    httpd = http.server.HTTPServer((HOST, PORT), AuthRequestHandler)
    print("""
    Feed URL: %(URL)s/%(FEEDFILE)s
    Redirect URL: http://%(HOST)s:%(RPORT)d/%(REDIRECT)s
    Timeout URL: %(URL)s/%(TIMEOUT)s
    Username: %(USERNAME)s
    Password: %(PASSWORD)s
    """ % locals())
    httpdr = http.server.HTTPServer((HOST, RPORT), AuthRequestHandler)
    t1 = threading.Thread(name='http', target=run, args=(httpd,), daemon=True)
    t1.start()
    t2 = threading.Thread(name='http redirect', target=run, args=(httpdr,), daemon=True)
    t2.start()
    try:
        t1.join()
        t2.join()
    except KeyboardInterrupt:
        pass
