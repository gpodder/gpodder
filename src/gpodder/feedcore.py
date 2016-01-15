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

import feedparser

import logging
logger = logging.getLogger(__name__)

try:
    # Python 2
    from rfc822 import mktime_tz
except ImportError:
    # Python 3
    from email.utils import mktime_tz


# Version check to avoid bug 1648
feedparser_version = tuple(int(x) if x.isdigit() else x
        for x in feedparser.__version__.split('.'))
feedparser_miniumum_version = (5, 1, 2)
if feedparser_version < feedparser_miniumum_version:
    installed_version = feedparser.__version__
    required_version = '.'.join(str(x) for x in feedparser_miniumum_version)
    logger.warn('Your feedparser is too old. Installed: %s, recommended: %s',
            installed_version, required_version)


def patch_feedparser():
    """Monkey-patch the Universal Feed Parser"""
    # Detect the 'plain' content type as 'text/plain'
    # http://code.google.com/p/feedparser/issues/detail?id=80
    def mapContentType2(self, contentType):
        contentType = contentType.lower()
        if contentType == 'text' or contentType == 'plain':
            contentType = 'text/plain'
        elif contentType == 'html':
            contentType = 'text/html'
        elif contentType == 'xhtml':
            contentType = 'application/xhtml+xml'
        return contentType

    try:
        if feedparser._FeedParserMixin().mapContentType('plain') == 'plain':
            feedparser._FeedParserMixin.mapContentType = mapContentType2
    except:
        pass
    
    # Fix parsing of Media RSS with feedparser, as described here: 
    #   http://code.google.com/p/feedparser/issues/detail?id=100#c4
    def _start_media_content(self, attrsD):
        context = self._getContext()
        context.setdefault('media_content', [])
        context['media_content'].append(attrsD)
        
    try:
        feedparser._FeedParserMixin._start_media_content = _start_media_content
    except:
        pass

    # Fix problem with the EA.com official podcast
    # https://bugs.gpodder.org/show_bug.cgi?id=588
    if '*/*' not in feedparser.ACCEPT_HEADER.split(','):
        feedparser.ACCEPT_HEADER += ',*/*'

    # Fix problem with YouTube feeds and pubDate/atom:modified
    # https://bugs.gpodder.org/show_bug.cgi?id=1492
    # http://code.google.com/p/feedparser/issues/detail?id=310
    def _end_updated(self):
        value = self.pop('updated')
        parsed_value = feedparser._parse_date(value)
        overwrite = ('youtube.com' not in self.baseuri)
        try:
            self._save('updated_parsed', parsed_value, overwrite=overwrite)
        except TypeError, te:
            logger.warn('Your feedparser version is too old: %s', te)

    try:
        feedparser._FeedParserMixin._end_updated = _end_updated
    except:
        pass


patch_feedparser()


class ExceptionWithData(Exception):
    """Base exception with additional payload"""
    def __init__(self, data):
        Exception.__init__(self)
        self.data = data

    def __str__(self):
        return '%s: %s' % (self.__class__.__name__, str(self.data))

# Temporary errors
class Offline(Exception): pass
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


class Fetcher(object):
    # Supported types, see http://feedvalidator.org/docs/warning/EncodingMismatch.html
    FEED_TYPES = ('application/rss+xml',
                  'application/atom+xml',
                  'application/rdf+xml',
                  'application/xml',
                  'text/xml')

    def __init__(self, user_agent):
        self.user_agent = user_agent

    def _resolve_url(self, url):
        """Provide additional ways of resolving an URL

        Subclasses can override this method to provide more
        ways of resolving a given URL to a feed URL. If the
        Fetcher is in "autodiscovery" mode, it will try this
        method as a last resort for coming up with a feed URL.
        """
        return None

    def _autodiscover_feed(self, feed):
        # First, try all <link> elements if available
        for link in feed.feed.get('links', ()):
            is_feed = link.get('type', '') in self.FEED_TYPES
            is_alternate = link.get('rel', '') == 'alternate'
            url = link.get('href', None)

            if url and is_feed and is_alternate:
                try:
                    return self._parse_feed(url, None, None, False)
                except Exception, e:
                    pass

        # Second, try to resolve the URL
        url = self._resolve_url(feed.href)
        if url:
            result = self._parse_feed(url, None, None, False)
            result.status = NEW_LOCATION
            return result

    def _check_offline(self, feed):
        if not hasattr(feed, 'headers'):
            raise Offline()

    def _check_wifi_login_page(self, feed):
        html_page = 'text/html' in feed.headers.get('content-type', '')
        if not feed.version and feed.status == 302 and html_page:
            raise WifiLogin(feed.href)

    def _check_valid_feed(self, feed):
        if feed is None:
            raise InvalidFeed('feed is None')

        if not hasattr(feed, 'status'):
            raise InvalidFeed('feed has no status code')

        if not feed.version and feed.status != 304 and feed.status != 401:
            raise InvalidFeed('unknown feed type')

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

    def _check_rss_redirect(self, feed):
        new_location = feed.feed.get('newlocation', None)
        if new_location:
            feed.href = feed.feed.newlocation
            return Result(NEW_LOCATION, feed)

        return None

    def _check_statuscode(self, feed):
        status = self._normalize_status(feed.status)
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
        if url.startswith('file://'):
            is_local = True
            url = url[len('file://'):]
        else:
            is_local = False

        feed = feedparser.parse(url,
                agent=self.user_agent,
                modified=modified,
                etag=etag)

        if is_local:
            if feed.version:
                feed.headers = {}
                return Result(UPDATED_FEED, feed)
            else:
                raise InvalidFeed('Not a valid feed file')
        else:
            self._check_offline(feed)
            self._check_wifi_login_page(feed)

            if feed.status != 304 and not feed.version and autodiscovery:
                feed = self._autodiscover_feed(feed).feed

            self._check_valid_feed(feed)

            redirect = self._check_rss_redirect(feed)
            if redirect is not None:
                return redirect

            return self._check_statuscode(feed)

    def fetch(self, url, etag=None, modified=None):
        return self._parse_feed(url, etag, modified)


def get_pubdate(entry):
    """Try to determine the real pubDate of a feedparser entry

    This basically takes the updated_parsed value, but also uses some more
    advanced techniques to work around various issues with ugly feeds.

    "published" now also takes precedence over "updated" (with updated used as
    a fallback if published is not set/available). RSS' "pubDate" element is
    "updated", and will only be used if published_parsed is not available.
    """

    pubdate = entry.get('published_parsed', None)

    if pubdate is None:
        pubdate = entry.get('updated_parsed', None)

    if pubdate is None:
        # Cannot determine pubdate - party like it's 1970!
        return 0

    return mktime_tz(pubdate + (0,))

