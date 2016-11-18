# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2016 Thomas Perl and the gPodder Team
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

import podcastparser

from gpodder import util

import logging
logger = logging.getLogger(__name__)

from urllib2 import HTTPError
from HTMLParser import HTMLParser
import urlparse

try:
    # Python 2
    from rfc822 import mktime_tz
except ImportError:
    # Python 3
    from email.utils import mktime_tz


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
class AuthenticationRequired(Exception): pass

# Successful status codes
UPDATED_FEED, NEW_LOCATION, NOT_MODIFIED, CUSTOM_FEED = range(4)

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
            url = urlparse.urljoin(self._base, url)

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

    def _normalize_status(self, status):
        # Based on Mark Pilgrim's "Atom aggregator behaviour" article
        if status in (200, 301, 302, 304, 400, 401, 403, 404, 410, 500):
            return status
        elif status >= 200 and status < 300:
            return 200
        elif status >= 300 and status < 400:
            return 302
        elif status >= 400 and status < 500:
            return 400
        elif status >= 500 and status < 600:
            return 500
        else:
            return status

    def _check_statuscode(self, response, feed):
        status = self._normalize_status(response.getcode())

        if status == 200:
            return Result(UPDATED_FEED, feed)
        elif status == 301:
            return Result(NEW_LOCATION, feed)
        elif status == 302:
            return Result(UPDATED_FEED, feed)
        elif status == 304:
            return Result(NOT_MODIFIED, feed)

        if status == 400:
            raise BadRequest('bad request')
        elif status == 401:
            raise AuthenticationRequired('authentication required')
        elif status == 403:
            raise Unsubscribe('forbidden')
        elif status == 404:
            raise NotFound('not found')
        elif status == 410:
            raise Unsubscribe('resource is gone')
        elif status == 500:
            raise InternalServerError('internal server error')
        else:
            raise UnknownStatusCode(status)

    def _parse_feed(self, url, etag, modified, autodiscovery=True):
        headers = {}
        if modified is not None:
            headers['If-Modified-Since'] = modified
        if etag is not None:
            headers['If-None-Match'] = etag

        if url.startswith('file://'):
            is_local = True
            url = url[len('file://'):]
            stream = open(url)
        else:
            is_local = False
            try:
                stream = util.urlopen(url, headers)
            except HTTPError as e:
                return self._check_statuscode(e, e.geturl())

        if stream.headers.get('content-type', '').startswith('text/html'):
            if autodiscovery:
                ad = FeedAutodiscovery(url)
                ad.feed(stream.read())
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

            raise InvalidFeed('Got HTML document instead')

        feed = podcastparser.parse(url, stream)
        return self._check_statuscode(stream, feed)

    def fetch(self, url, etag=None, modified=None):
        return self._parse_feed(url, etag, modified)
