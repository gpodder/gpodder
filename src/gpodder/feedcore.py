# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2018 The gPodder Team
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

#
# Generic feed fetching module for aggregators
# Thomas Perl <thp@gpodder.org>; 2009-06-11
#

import logging
import urllib.parse
from html.parser import HTMLParser

import podcastparser
from requests.exceptions import RequestException

from gpodder import util

logger = logging.getLogger(__name__)


try:
    # Python 2
    from rfc822 import mktime_tz
    from StringIO import StringIO
except ImportError:
    # Python 3
    from email.utils import mktime_tz
    from io import StringIO


class ExceptionWithData(Exception):
    """Base exception with additional payload"""
    def __init__(self, data):
        Exception.__init__(self)
        self.data = data

    def __str__(self):
        return '%s: %s' % (self.__class__.__name__, str(self.data))


# Temporary errors
class BadRequest(Exception): pass


class InternalServerError(Exception): pass


class WifiLogin(ExceptionWithData): pass


# Fatal errors
class Unsubscribe(Exception): pass


class NotFound(Exception): pass


class InvalidFeed(Exception): pass


class UnknownStatusCode(ExceptionWithData): pass


# Authentication error
class AuthenticationRequired(Exception):
    def __init__(self, msg, url=None):
        super().__init__(msg)
        self.url = url


# Successful status codes
UPDATED_FEED, NEW_LOCATION, NOT_MODIFIED = list(range(3))


class Result:
    def __init__(self, status, feed=None):
        self.status = status
        self.feed = feed


class FeedAutodiscovery(HTMLParser):
    def __init__(self, base):
        HTMLParser.__init__(self)
        self._base = base
        self._resolved_url = None

    def handle_starttag(self, tag, attrs):
        if tag == 'link':
            attrs = dict(attrs)

            is_feed = attrs.get('type', '') in Fetcher.FEED_TYPES
            is_alternate = attrs.get('rel', '') == 'alternate'
            url = attrs.get('href', None)
            url = urllib.parse.urljoin(self._base, url)

            if is_feed and is_alternate and url:
                logger.info('Feed autodiscovery: %s', url)
                self._resolved_url = url


class Fetcher(object):
    # Supported types, see http://feedvalidator.org/docs/warning/EncodingMismatch.html
    FEED_TYPES = ('application/rss+xml',
                  'application/atom+xml',
                  'application/rdf+xml',
                  'application/xml',
                  'text/xml')

    def _resolve_url(self, url):
        """Provide additional ways of resolving an URL

        Subclasses can override this method to provide more
        ways of resolving a given URL to a feed URL. If the
        Fetcher is in "autodiscovery" mode, it will try this
        method as a last resort for coming up with a feed URL.
        """
        return None

    @staticmethod
    def _check_statuscode(status, url):
        if status >= 200 and status < 300:
            return UPDATED_FEED
        elif status == 304:
            return NOT_MODIFIED
        # redirects are handled by requests directly
        # => the status should never be 301, 302, 303, 307, 308

        if status == 401:
            raise AuthenticationRequired('authentication required', url)
        elif status == 403:
            raise Unsubscribe('forbidden')
        elif status == 404:
            raise NotFound('not found')
        elif status == 410:
            raise Unsubscribe('resource is gone')
        elif status >= 400 and status < 500:
            raise BadRequest('bad request')
        elif status >= 500 and status < 600:
            raise InternalServerError('internal server error')
        else:
            raise UnknownStatusCode(status)

    @staticmethod
    def _podcastparse_feed(url, data_stream):
        try:
            feed = podcastparser.parse(url, data_stream)
            feed['url'] = url
            return feed
        except ValueError as e:
            raise InvalidFeed('Could not parse feed: {msg}'.format(msg=e))

    def _parse_feed(self, url, etag, modified, autodiscovery=True, max_episodes=0):
        # handle local file first
        if url.startswith('file://'):
            url = url[len('file://'):]
            stream = open(url)
            feed = self._podcastparse_feed(url, stream)
            feed['headers'] = {}
            return Result(UPDATED_FEED, feed)

        # remote feed
        headers = {}
        if modified is not None:
            headers['If-Modified-Since'] = modified
        if etag is not None:
            headers['If-None-Match'] = etag

        stream = util.urlopen(url, headers)

        responses = stream.history + [stream]
        for i, resp in enumerate(responses):
            if resp.is_permanent_redirect:
                # there should always be a next response when a redirect is encountered
                # If max redirects is reached, TooManyRedirects is raised
                # TODO: since we've got the end contents anyway, modify model.py to accept contents on NEW_LOCATION
                return Result(NEW_LOCATION, responses[i+1].url)
        res = self._check_statuscode(stream.status_code, stream.url)
        if res == NOT_MODIFIED:
            return Result(res, stream.url)

        if autodiscovery and stream.headers.get('content-type', '').startswith('text/html'):
            ad = FeedAutodiscovery(url)
            ad.feed(stream.text)  # uses headers, then apparent encoding
            if ad._resolved_url:
                try:
                    self._parse_feed(ad._resolved_url, None, None, False)
                    return Result(NEW_LOCATION, ad._resolved_url)
                except Exception as e:
                    logger.warn('Feed autodiscovery failed', exc_info=True)

                # Second, try to resolve the URL
                url = self._resolve_url(url)
                if url:
                    return Result(NEW_LOCATION, url)
        feed = self._podcastparse_feed(url, StringIO(stream.text))
        feed['headers'] = stream.headers
        return Result(UPDATED_FEED, feed)

    def fetch(self, url, etag=None, modified=None, max_episodes=0):
        return self._parse_feed(url, etag, modified, max_episodes)
