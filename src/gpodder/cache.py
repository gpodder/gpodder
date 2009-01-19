# -*- coding: utf-8 -*-
# 
# python-feedcache (customized by Thomas Perl for use in gPodder)
#
# Copyright 2007 Doug Hellmann.
#
#
#                         All Rights Reserved
#
# Permission to use, copy, modify, and distribute this software and
# its documentation for any purpose and without fee is hereby
# granted, provided that the above copyright notice appear in all
# copies and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of Doug
# Hellmann not be used in advertising or publicity pertaining to
# distribution of the software without specific, written prior
# permission.
#
# DOUG HELLMANN DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
# INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS, IN
# NO EVENT SHALL DOUG HELLMANN BE LIABLE FOR ANY SPECIAL, INDIRECT OR
# CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
# OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
# NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#


import feedparser

import string
import re
import time
import urllib, urlparse

import gpodder
from gpodder import resolver
from gpodder.liblogger import log


def patch_feedparser():
    """Fix a bug in feedparser 4.1
    This replaces the mapContentType method of the
    _FeedParserMixin class to correctly detect the
    "plain" content type as "text/plain".

    See also:
    http://code.google.com/p/feedparser/issues/detail?id=80

    Added by Thomas Perl for gPodder 2007-12-29
    """
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
            log('Patching feedparser module... (mapContentType bugfix)')
            feedparser._FeedParserMixin.mapContentType = mapContentType2
    except:
        log('Warning: feedparser unpatched - might be broken!')

patch_feedparser()


class Cache:
    """A class to wrap Mark Pilgrim's Universal Feed Parser module
    (http://www.feedparser.org) so that parameters can be used to
    cache the feed results locally instead of fetching the feed every
    time it is requested. Uses both etag and modified times for
    caching.
    """

    # Supported types, see http://feedvalidator.org/docs/warning/EncodingMismatch.html
    SUPPORTED_FEED_TYPES = ('application/rss+xml', 'application/atom+xml',
            'application/rdf+xml', 'application/xml', 'text/xml')

    def __init__(self, timeToLiveSeconds=3600):
        """
        Arguments:

          storage -- Backing store for the cache.  It should follow
          the dictionary API, with URLs used as keys.  It should
          persist data.

          timeToLiveSeconds=300 -- The length of time content should
          live in the cache before an update is attempted.
        """
        self.time_to_live = timeToLiveSeconds
        self.user_agent = gpodder.user_agent
        return

    def fetch(self, url, old_channel=None):
        """
        Returns an (updated, feed) tuple for the feed at the specified
        URL. If the feed hasn't updated since the last run, updated
        will be False. If it has been updated, updated will be True.

        If updated is False, the feed value is None and you have to use
        the old channel which you passed to this function.
        """

        if old_channel is not None:
            etag = old_channel.etag
            modified = feedparser._parse_date(old_channel.last_modified)
        else:
            etag = None
            modified = None

        original_url = url
        # If we have a username or password, rebuild the url with them included
        # Note: using a HTTPBasicAuthHandler would be pain because we need to
        # know the realm. It can be done, but I think this method will work fine
        if old_channel is not None and (
                old_channel.username or old_channel.password ):
            username = urllib.quote(old_channel.username)
            password = urllib.quote(old_channel.password)
            auth_string = string.join( [username, password], ':' )
            url_parts = list(urlparse.urlsplit(url))
            url_parts[1] = string.join( [auth_string, url_parts[1]], '@' )
            url = urlparse.urlunsplit(url_parts)

        # We know we need to fetch, so go ahead and do it.
        parsed_result = feedparser.parse(url,
                                         agent=self.user_agent,
                                         modified=modified,
                                         etag=etag,
                                         )

        # Sometimes, the status code is not set (ugly feed?)
        status = parsed_result.get('status', None)

        # 304: Not Modified
        if status == 304:
            log('Not Modified: %s', url, sender=self)
            return (False, None)

        if status == 401:
            log('HTTP authentication required: %s', original_url, sender=self)
            return (False, parsed_result)
        if not hasattr(parsed_result, 'headers'):
            log('The requested object does not have a "headers" attribute.', sender=self)
            return (False, None)
        content_type = parsed_result.headers.get('content-type', '').lower()
        # TODO: Also detect OPML feeds and other content types here
        if parsed_result.version == '':
            log('%s looks like a webpage - trying feed autodiscovery.', url, sender=self)
            if not hasattr(parsed_result.feed, 'links'):
                return (False, None)
            try:
                found_alternate_feed = False
                for link in parsed_result.feed.links:
                    if hasattr(link, 'type') and hasattr(link, 'href') and hasattr(link, 'rel'):
                        if link.type in self.SUPPORTED_FEED_TYPES and link.rel == 'alternate':
                            log('Found alternate feed link: %s', link.href, sender=self)
                            parsed_result = feedparser.parse(link.href,
                                                             agent=self.user_agent,
                                                             modified=modified,
                                                             etag=etag,
                                                             )
                            found_alternate_feed = True
                            break

                # YouTube etc feed lookup (after the normal link lookup in case
                # they provide a standard feed discovery mechanism in the future).
                if not found_alternate_feed:
                    next = resolver.get_real_channel_url(url)

                    if next is not None:
                        parsed_result = feedparser.parse(next, agent=self.user_agent, modified=modified, etag=etag)
                        found_alternate_feed = True

                # We have not found a valid feed - abort here!
                if not found_alternate_feed:
                    return (False, None)
            except:
                log('Error while trying to get feed URL from webpage', sender=self, traceback=True)

        updated = False
        status = parsed_result.get('status', None)

        if status == 304:
            # No new data, based on the etag or modified values.
            # We need to update the modified time in the
            # storage, though, so we know that what we have
            # stored is up to date.
            log('Using cached feed: %s', url, sender=self)
        elif status in (200, 301, 302, 307):
            # log('===============')
            # log('[%s]', url)
            # log('LM old: %s', old_channel.last_modified)
            # log('LM new: %s', parsed_result.headers.get('last-modified'))
            # log('=======')
            # log('ET old: %s', old_channel.etag)
            # log('ET new: %s', parsed_result.headers.get('etag'))
            # log('===============')
            updated = True
            # There is new content, so store it unless there was an error.
            # Store it regardless of errors when we don't have anything yet
            error = parsed_result.get('bozo_exception')
            if error:
                log('Warning: %s (%s)', url, str(error), sender=self)
                parsed_result['bozo_exception'] = str(error)
        else:
            log('Strange status code: %s (%s)', url, status, sender=self)

        return (updated, parsed_result)

