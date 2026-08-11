#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Simple HTTP web server for testing HTTP Authentication (see bug 1539)
# from our crappy-but-does-the-job department
# Thomas Perl <thp.io/about>; 2012-01-20

import hashlib
import http.server
import sys
import threading
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

USERNAME = 'user@example.com'    # Username used for HTTP Authentication
PASSWORD = 'secret'              # Password used for HTTP Authentication

HOST, PORT, RPORT = 'localhost', 8000, 8001   # Hostname and port for the HTTP server

# When the script contents change, the feed's episodes each get a new GUID
GUID = hashlib.sha1(open(__file__, mode='rb').read()).hexdigest()

URL = 'http://%(HOST)s:%(PORT)s' % locals()

FEEDNAME = sys.argv[0]        # The title of the RSS feed
# reject with TooManyRequests for 10s, then accept once, setting expires header to 30s
RATE_LIMIT = 'rate-limit-10s'
# reject with ServiceUnavailable 3 times then accept once, not setting expires header
UNRELIABLE = 'fail-3-out-of-4'
FEEDFILE = 'feed.rss'         # The "filename" of the feed on the server
EPISODES = 'episode'          # Base name for the episode files
EPISODES_EXT = '.mp3'         # Extension for the episode files
EPISODES_MIME = 'audio/mpeg'  # Mime type for the episode files
EP_COUNT = 7                  # Number of episodes in the feed
SIZE = 500000                 # Size (in bytes) of the episode downloads)


def mkpubdates(items):
    """Generate fake pubDates (one each day, recently)."""
    current = datetime.now() - timedelta(days=items + 3)
    for i in range(items):
        yield current.ctime()
        current += timedelta(days=1)


def mkrss(path, items=EP_COUNT):
    """Generate a dummy RSS feed with a given number of items."""
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
        <title>Rate limited first fails</title>
        <guid>tag:test.gpodder.org,2026:ratelimit</guid>
        <pubDate>Sun, 15 Feb 2026 10:28:03 +0000</pubDate>
        <enclosure
          url="%(URL)s/%(EPISODES)s/%(RATE_LIMIT)s"
          type="%(EPISODES_MIME)s"
          length="%(SIZE)s"/>
    </item>""" % dict(list(locals().items()) + list(globals().items()))
    ITEMS += """
    <item>
        <title>Unreliable 3 in 4 fails</title>
        <guid>tag:test.gpodder.org,2026:unreliable</guid>
        <pubDate>Sun, 15 Feb 2026 10:28:03 +0000</pubDate>
        <enclosure
          url="%(URL)s/%(EPISODES)s/%(UNRELIABLE)s"
          type="%(EPISODES_MIME)s"
          length="%(SIZE)s"/>
    </item>""" % dict(list(locals().items()) + list(globals().items()))

    return """
    <rss>
    <channel><title>%(FEEDNAME)s %(path)s</title><link>%(URL)s</link>
    %(ITEMS)s
    </channel>
    </rss>
    """ % dict(list(locals().items()) + list(globals().items()))


def mkdata(size=SIZE):
    """Generate dummy data of a given size (in bytes)."""
    return bytes([32 + (i % (127 - 32)) for i in range(size)])


class MyRequestHandler(http.server.BaseHTTPRequestHandler):
    EPISODES_PATH = f"/{EPISODES}"

    rate_limit_succeed_after = None
    unreliable_last_failed = 0

    def do_GET(self):
        is_feed = False
        is_episode = False
        expires = None

        if self.path.endswith('.rss'):
            print('Feed request.')
            is_feed = True
        elif self.path.startswith(self.EPISODES_PATH):
            print('Episode request.')
            is_episode = True
        if not is_feed and not is_episode:
            print('Not there episode - sending 404.')
            self.send_response(404)
            self.end_headers()
            return
        if RATE_LIMIT in self.path:
            if not MyRequestHandler.rate_limit_succeed_after:
                MyRequestHandler.rate_limit_succeed_after = datetime.now(timezone.utc) + timedelta(seconds=10)
            if MyRequestHandler.rate_limit_succeed_after > datetime.now(timezone.utc):
                print('Rate limit, wait some more')
                self.send_response(429)
                self.send_header('retry-after', format_datetime(MyRequestHandler.rate_limit_succeed_after, usegmt=True))
                self.end_headers()
                return
            MyRequestHandler.rate_limit_succeed_after = None
            expires = datetime.now(timezone.utc) + timedelta(seconds=30)
        if UNRELIABLE in self.path:
            if MyRequestHandler.unreliable_last_failed < 3:
                print('Unreliable, fail')
                self.send_response(503)
                self.send_header('retry-after', format_datetime(datetime.now(timezone.utc) + timedelta(seconds=10), usegmt=True))
                self.end_headers()
                MyRequestHandler.unreliable_last_failed += 1
                return
            MyRequestHandler.unreliable_last_failed = 0

        self.send_response(200)
        self.send_header('Content-type',
                         'application/xml' if is_feed else 'audio/mpeg')
        if expires:
            self.send_header('expires', format_datetime(expires, usegmt=True))
        self.end_headers()
        self.wfile.write(mkrss(self.path).encode('utf-8') if is_feed else mkdata())


def run(httpd):
    while True:
        httpd.handle_request()


if __name__ == '__main__':
    httpd = http.server.HTTPServer((HOST, PORT), MyRequestHandler)
    print("""
    Feed URL: %(URL)s/%(FEEDFILE)s
    Rate-limitted Feed: %(URL)s/%(RATE_LIMIT)s.rss
    Unreliable Feed: %(URL)s/%(UNRELIABLE)s.rss
    """ % locals())
    t1 = threading.Thread(name='http', target=run, args=(httpd,), daemon=True)
    t1.start()
    try:
        t1.join()
    except KeyboardInterrupt:
        pass
