# -*- coding: utf-8 -*-
#
# podcastparser - Simplified, fast RSS parser (2012-12-29)
# Copyright (c) 2012, 2013, Thomas Perl <m@thp.io>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.
#

from xml import sax

import re
import os
import time
import urllib.parse
from email.utils import mktime_tz, parsedate_tz

import logging
logger = logging.getLogger(__name__)

class Target:
    WANT_TEXT = False

    def __init__(self, key=None, filter_func=lambda x: x.strip()):
        self.key = key
        self.filter_func = filter_func

    def start(self, handler, attrs): pass
    def end(self, handler, text): pass

class RSS(Target):
    def start(self, handler, attrs):
        handler.set_base(attrs.get('xml:base'))

class PodcastItem(Target):
    def end(self, handler, text):
        handler.data['episodes'].sort(key=lambda entry: entry.get('published'), reverse=True)
        if handler.max_episodes:
            handler.data['episodes'] = handler.data['episodes'][:handler.max_episodes]

class PodcastAttr(Target):
    WANT_TEXT = True

    def end(self, handler, text):
        handler.set_podcast_attr(self.key, self.filter_func(text))

class PodcastAttrFromHref(Target):
    def start(self, handler, attrs):
        value = attrs.get('href')
        if value:
            handler.set_podcast_attr(self.key, self.filter_func(value))

class PodcastAttrFromPaymentHref(PodcastAttrFromHref):
    def start(self, handler, attrs):
        if attrs.get('rel') == 'payment':
            PodcastAttrFromHref.start(self, handler, attrs)

class EpisodeItem(Target):
    def start(self, handler, attrs):
        handler.add_episode()

    def end(self, handler, text):
        handler.validate_episode()

class EpisodeAttr(Target):
    WANT_TEXT = True

    def end(self, handler, text):
        handler.set_episode_attr(self.key, self.filter_func(text))

class EpisodeGuid(EpisodeAttr):
    def start(self, handler, attrs):
        if attrs.get('isPermaLink', 'true').lower() == 'true':
            handler.set_episode_attr('_guid_is_permalink', True)
        else:
            handler.set_episode_attr('_guid_is_permalink', False)

    def end(self, handler, text):
        def filter_func(guid):
            guid = guid.strip()
            if handler.base is not None:
                return urllib.parse.urljoin(handler.base, guid)
            return guid

        self.filter_func = filter_func
        EpisodeAttr.end(self, handler, text)

class EpisodeAttrFromHref(Target):
    def start(self, handler, attrs):
        value = attrs.get('href')
        if value:
            handler.set_episode_attr(self.key, self.filter_func(value))

class EpisodeAttrFromPaymentHref(EpisodeAttrFromHref):
    def start(self, handler, attrs):
        if attrs.get('rel') == 'payment':
            EpisodeAttrFromHref.start(self, handler, attrs)

class Enclosure(Target):
    def __init__(self, file_size_attribute):
        Target.__init__(self)
        self.file_size_attribute = file_size_attribute

    def start(self, handler, attrs):
        url = attrs.get('url')
        if url is None:
            return

        url = parse_url(urllib.parse.urljoin(handler.url, url))
        file_size = parse_length(attrs.get(self.file_size_attribute))
        mime_type = parse_type(attrs.get('type'))

        handler.add_enclosure(url, file_size, mime_type)

class Namespace():
    # Mapping of XML namespaces to prefixes as used in MAPPING below
    NAMESPACES = {
        # iTunes Podcasting, http://www.apple.com/itunes/podcasts/specs.html
        'http://www.itunes.com/dtds/podcast-1.0.dtd': 'itunes',
        'http://www.itunes.com/DTDs/Podcast-1.0.dtd': 'itunes',

        # Atom Syndication Format, http://tools.ietf.org/html/rfc4287
        'http://www.w3.org/2005/Atom': 'atom',
        'http://www.w3.org/2005/Atom/': 'atom',

        # Media RSS, http://www.rssboard.org/media-rss
        'http://search.yahoo.com/mrss/': 'media',

        # From http://www.rssboard.org/media-rss#namespace-declaration:
        #   "Note: There is a trailing slash in the namespace, although
        #    there has been confusion around this in earlier versions."
        'http://search.yahoo.com/mrss': 'media',
    }

    def __init__(self, attrs, parent=None):
        self.namespaces = self.parse_namespaces(attrs)
        self.parent = parent

    @staticmethod
    def parse_namespaces(attrs):
        """Parse namespace definitions from XML attributes

        >>> expected = {'': 'example'}
        >>> Namespace.parse_namespaces({'xmlns': 'example'}) == expected
        True

        >>> expected = {'foo': 'http://example.com/bar'}
        >>> Namespace.parse_namespaces({'xmlns:foo':
        ...     'http://example.com/bar'}) == expected
        True

        >>> expected = {'': 'foo', 'a': 'bar', 'b': 'bla'}
        >>> Namespace.parse_namespaces({'xmlns': 'foo',
        ...     'xmlns:a': 'bar', 'xmlns:b': 'bla'}) == expected
        True
        """
        result = {}

        for key in list(attrs.keys()):
            if key == 'xmlns':
                result[''] = attrs[key]
            elif key.startswith('xmlns:'):
                result[key[6:]] = attrs[key]

        return result

    def lookup(self, prefix):
        """Look up a namespace URI based on the prefix"""
        current = self
        while current is not None:
            result = current.namespaces.get(prefix, None)
            if result is not None:
                return result
            current = current.parent

        return None

    def map(self, name):
        """Apply namespace prefixes for a given tag

        >>> namespace = Namespace({'xmlns:it':
        ...    'http://www.itunes.com/dtds/podcast-1.0.dtd'}, None)
        >>> namespace.map('it:duration')
        'itunes:duration'
        >>> parent = Namespace({'xmlns:m': 'http://search.yahoo.com/mrss/',
        ...                     'xmlns:x': 'http://example.com/'}, None)
        >>> child = Namespace({}, parent)
        >>> child.map('m:content')
        'media:content'
        >>> child.map('x:y') # Unknown namespace URI
        '!x:y'
        >>> child.map('atom:link') # Undefined prefix
        'atom:link'
        """
        if ':' not in name:
            # <duration xmlns="http://..."/>
            namespace = ''
            namespace_uri = self.lookup(namespace)
        else:
            # <itunes:duration/>
            namespace, name = name.split(':', 1)
            namespace_uri = self.lookup(namespace)
            if namespace_uri is None:
                # Use of "itunes:duration" without xmlns:itunes="..."
                logger.warn('No namespace defined for "%s:%s"', namespace, name)
                return '%s:%s' % (namespace, name)

        if namespace_uri is not None:
            prefix = self.NAMESPACES.get(namespace_uri)
            if prefix is None and namespace:
                # Proper use of namespaces, but unknown namespace
                #logger.warn('Unknown namespace: %s', namespace_uri)
                # We prefix the tag name here to make sure that it does not
                # match any other tag below if we can't recognize the namespace
                name = '!%s:%s' % (namespace, name)
            else:
                name = '%s:%s' % (prefix, name)

        return name

def parse_time(value):
    """Parse a time string into seconds

    >>> parse_time('0')
    0
    >>> parse_time('128')
    128
    >>> parse_time('00:00')
    0
    >>> parse_time('00:00:00')
    0
    >>> parse_time('00:20')
    20
    >>> parse_time('00:00:20')
    20
    >>> parse_time('01:00:00')
    3600
    >>> parse_time('03:02:01')
    10921
    >>> parse_time('61:08')
    3668
    >>> parse_time('25:03:30')
    90210
    >>> parse_time('25:3:30')
    90210
    >>> parse_time('61.08')
    3668
    """
    if value == '':
        return 0

    if not value:
        raise ValueError('Invalid value: %s' % (str(value),))

    m = re.match(r'(\d+)[:.](\d\d?)[:.](\d\d?)', value)
    if m:
        hours, minutes, seconds = m.groups()
        return (int(hours) * 60 + int(minutes)) * 60 + int(seconds)

    m = re.match(r'(\d+)[:.](\d\d?)', value)
    if m:
        minutes, seconds = m.groups()
        return int(minutes) * 60 + int(seconds)

    return int(value)

def parse_date(value):
    """Parse a date string into a Unix timestamp

    >>> parse_date('Sat Dec 29 18:23:19 CET 2012')
    1356801799

    >>> parse_date('')
    0
    """
    if not value:
        return 0

    parsed = parsedate_tz(value)
    if parsed is not None:
        return int(mktime_tz(parsed))

    logger.error('Cannot parse date: %s', repr(value))
    return 0

def file_basename_no_extension(filename):
    base = os.path.basename(filename)
    name, extension = os.path.splitext(base)
    return name

def squash_whitespace(text):
    return re.sub('\s+', ' ', text.strip())

def parse_duration(text):
    return parse_time(text.strip())

def parse_url(text):
    return text.strip() # XXX util.normalize_feed_url

def parse_length(text):
    if text is None:
        return -1

    try:
        return int(text.strip()) or -1
    except ValueError:
        return -1

def parse_type(text):
    if not text or '/' not in text:
        # Maemo bug 10036
        return 'application/octet-stream'

    return text

def parse_pubdate(text):
    return parse_date(text)


MAPPING = {
    'rss': RSS(),
    'rss/channel': PodcastItem(),
    'rss/channel/title': PodcastAttr('title', squash_whitespace),
    'rss/channel/link': PodcastAttr('link'),
    'rss/channel/description': PodcastAttr('description', squash_whitespace),
    'rss/channel/image/url': PodcastAttr('cover_url'),
    'rss/channel/itunes:image': PodcastAttrFromHref('cover_url'),
    'rss/channel/atom:link': PodcastAttrFromPaymentHref('payment_url'),

    'rss/channel/item': EpisodeItem(),
    'rss/channel/item/guid': EpisodeGuid('guid'),
    'rss/channel/item/title': EpisodeAttr('title', squash_whitespace),
    'rss/channel/item/link': EpisodeAttr('link'),
    'rss/channel/item/description': EpisodeAttr('description', squash_whitespace),
    # Alternatives for description: itunes:summary, itunes:subtitle, content:encoded
    'rss/channel/item/itunes:duration': EpisodeAttr('total_time', parse_duration),
    'rss/channel/item/pubDate': EpisodeAttr('published', parse_pubdate),
    'rss/channel/item/atom:link': EpisodeAttrFromPaymentHref('payment_url'),

    'rss/channel/item/media:content': Enclosure('fileSize'),
    'rss/channel/item/enclosure': Enclosure('length'),
}

class PodcastHandler(sax.handler.ContentHandler):
    def __init__(self, url, max_episodes):
        self.url = url
        self.max_episodes = max_episodes
        self.base = None
        self.text = None
        self.episodes = []
        self.data = {
            'title': file_basename_no_extension(url),
            'episodes': self.episodes
        }
        self.path_stack = []
        self.namespace = None

    def set_base(self, base):
        self.base = base

    def set_podcast_attr(self, key, value):
        self.data[key] = value

    def set_episode_attr(self, key, value):
        self.episodes[-1][key] = value

    def add_episode(self):
        self.episodes.append({
            # title
            'description': '',
            # url
            'published': 0,
            # guid
            'link': '',
            'total_time': 0,
            'payment_url': None,
            'enclosures': [],
            '_guid_is_permalink': False,
        })

    def validate_episode(self):
        entry = self.episodes[-1]

        if 'guid' not in entry:
            if entry.get('link'):
                # Link element can serve as GUID
                entry['guid'] = entry['link']
            else:
                if len(entry['enclosures']) != 1:
                    # Multi-enclosure feeds MUST have a GUID
                    self.episodes.pop()
                    return

                # Maemo bug 12073
                entry['guid'] = entry['enclosures'][0]['url']

        if 'title' not in entry:
            if len(entry['enclosures']) != 1:
                self.episodes.pop()
                return

            entry['title'] = file_basename_no_extension(entry['enclosures'][0]['url'])

        if not entry.get('link') and entry.get('_guid_is_permalink'):
            entry['link'] = entry['guid']

        del entry['_guid_is_permalink']

    def add_enclosure(self, url, file_size, mime_type):
        self.episodes[-1]['enclosures'].append({
            'url': url,
            'file_size': file_size,
            'mime_type': mime_type,
        })

    def startElement(self, name, attrs):
        self.namespace = Namespace(attrs, self.namespace)
        self.path_stack.append(self.namespace.map(name))

        target = MAPPING.get('/'.join(self.path_stack))
        if target is not None:
            target.start(self, attrs)
            if target.WANT_TEXT:
                self.text = []

    def characters(self, chars):
        if self.text is not None:
            self.text.append(chars)

    def endElement(self, name):
        target = MAPPING.get('/'.join(self.path_stack))
        if target is not None:
            target.end(self, ''.join(self.text) if self.text is not None else '')
            self.text = None

        if self.namespace is not None:
            self.namespace = self.namespace.parent
        self.path_stack.pop()


def parse(url, stream, max_episodes=0):
    handler = PodcastHandler(url, max_episodes)
    sax.parse(stream, handler)
    return handler.data

