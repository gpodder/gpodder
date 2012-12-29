# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2012 Thomas Perl and the gPodder Team
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

# gpodder.podcastparser - Simplified, fast RSS parser
# Thomas Perl <thp@gpodder.org>; 2012-12-29

from xml import sax

from gpodder import util
from gpodder import youtube
from gpodder import vimeo

import re
import os
import time
import rfc822
import urlparse

try:
    # Python 2
    from rfc822 import mktime_tz
except ImportError:
    # Python 3
    from email.utils import mktime_tz

from feedparser import _parse_date

class Target:
    WANT_TEXT = False

    def __init__(self, key=None, filter_func=lambda x: x.strip()):
        self.key = key
        self.filter_func = filter_func

    def start(self, handler, attrs): pass
    def end(self, handler, text): pass

class RSS(Target):
    def start(self, handler, attrs):
        handler.base = attrs.get('xml:base')

class PodcastItem(Target):
    def end(self, handler, text):
        handler.data['episodes'].sort(key=lambda entry: entry.get('published'), reverse=True)
        if handler.max_episodes:
            handler.data['episodes'] = handler.data['episodes'][:handler.max_episodes]

class Podcast(Target):
    WANT_TEXT = True

    def end(self, handler, text):
        handler.data[self.key] = self.filter_func(text)

class PodcastFromHref(Target):
    def start(self, handler, attrs):
        value = self.filter_func(attrs.get('href', ''))
        if value:
            handler.data[self.key] = value

class PodcastFromPaymentHref(PodcastFromHref):
    def start(self, handler, attrs):
        if attrs.get('rel') == 'payment':
            PodcastFromHref.start(self, handler, attrs)

class EpisodeItem(Target):
    def start(self, handler, attrs):
        handler.episodes.append({
            # title
            'description': '',
            # url
            'published': 0,
            # guid
            'link': '',
            'file_size': -1,
            'mime_type': 'application/octet-stream',
            'total_time': 0,
            'payment_url': None,
            'enclosures': [],
        })

    def end(self, handler, text):
        entry = handler.episodes[-1]

        # No enclosures for this item
        if len(entry['enclosures']) == 0:
            if (youtube.is_video_link(entry['link']) or
                    vimeo.is_video_link(entry['link'])):
                entry['enclosures'].append({
                    'url': entry['link'],
                    'file_size': -1,
                    'mime_type': 'video/mp4',
                })
            else:
                handler.episodes.pop()
                return

        # Here we could pick a good enclosure
        entry.update(entry['enclosures'][0])
        del entry['enclosures']

        if 'guid' not in entry:
            # Maemo bug 12073
            entry['guid'] = entry['url']

        if 'title' not in entry:
            entry['title'] = entry['url']

        if not entry.get('link') and entry.get('_guid_is_permalink'):
            entry['link'] = entry['guid']

        if '_guid_is_permalink' in entry:
            del entry['_guid_is_permalink']

class Episode(Target):
    WANT_TEXT = True

    def end(self, handler, text):
        handler.episodes[-1][self.key] = self.filter_func(text)

class EpisodeGuid(Episode):
    def start(self, handler, attrs):
        if attrs.get('isPermaLink', 'true').lower() == 'true':
            handler.episodes[-1]['_guid_is_permalink'] = True
        else:
            handler.episodes[-1]['_guid_is_permalink'] = False

        Episode.start(self, handler, attrs)

    def end(self, handler, text):
        def filter_func(guid):
            guid = guid.strip()
            if handler.base is not None:
                return urlparse.urljoin(handler.base, guid)
            return guid

        self.filter_func = filter_func
        Episode.end(self, handler, text)

class EpisodeFromHref(Target):
    def start(self, handler, attrs):
        value = self.filter_func(attrs.get('href', ''))
        if value:
            handler.episodes[-1][self.key] = value

class EpisodeFromPaymentHref(EpisodeFromHref):
    def start(self, handler, attrs):
        if attrs.get('rel') == 'payment':
            EpisodeFromHref.start(self, handler, attrs)

class Enclosure(Target):
    def start(self, handler, attrs):
        url_target, length_target, type_target = self.key
        url_filter, length_filter, type_filter = self.filter_func

        handler.episodes[-1]['enclosures'].append({
            url_target: url_filter(attrs.get('url')),
            length_target: length_filter(attrs.get('length', '')),
            type_target: type_filter(attrs.get('type')),
        })


def squash_whitespace(text):
    return re.sub('\s+', ' ', text.strip())

def parse_duration(text):
    return util.parse_time(text.strip())

def parse_url(text):
    return util.normalize_feed_url(text.strip())

def parse_length(text):
    try:
        return long(text.strip()) or -1
    except ValueError:
        return -1

def parse_type(text):
    if not text or '/' not in text:
        # Maemo bug 10036
        return 'application/octet-stream'

    return text

def parse_pubdate(text):
    parsed = rfc822.parsedate(text)
    if parsed is None:
        print 'WARNING DATE:', repr(text)
        parsed = _parse_date(text)
    return mktime_tz(parsed + (0,))


MAPPING = {
    'rss': RSS(),
    'rss/channel': PodcastItem(),
    'rss/channel/title': Podcast('title', squash_whitespace),
    'rss/channel/link': Podcast('link'),
    'rss/channel/description': Podcast('description', squash_whitespace),
    'rss/channel/image/url': Podcast('cover_url'),
    'rss/channel/itunes:image': PodcastFromHref('cover_url'),
    'rss/channel/atom:link': PodcastFromPaymentHref('payment_url'),

    'rss/channel/item': EpisodeItem(),
    'rss/channel/item/guid': EpisodeGuid('guid'),
    'rss/channel/item/title': Episode('title', squash_whitespace),
    'rss/channel/item/link': Episode('link'),
    'rss/channel/item/description': Episode('description', squash_whitespace),
    # Alternatives for description: itunes:summary, itunes:subtitle, content:encoded
    'rss/channel/item/itunes:duration': Episode('total_time', parse_duration),
    'rss/channel/item/pubDate': Episode('published', parse_pubdate),
    'rss/channel/item/atom:link': EpisodeFromPaymentHref('payment_url'),

    'rss/channel/item/enclosure': Enclosure(
        ('url', 'file_size', 'mime_type'),
        (parse_url, parse_length, parse_type),
    ),
}

class PodcastHandler(sax.handler.ContentHandler):
    def __init__(self, url, max_episodes):
        self.url = url
        self.max_episodes = max_episodes
        self.base = None
        self.text = None
        self.episodes = []
        self.data = {
            'title': '',
            'episodes': self.episodes
        }
        self.target_stack = []
        self.path_stack = []

    def startElement(self, name, attrs):
        self.path_stack.append(name)

        path = '/'.join(self.path_stack)
        target = MAPPING.get(path)
        if target is not None:
            target.start(self, attrs)
            if target.WANT_TEXT:
                self.text = []
            self.target_stack.append((path, target))

    def characters(self, chars):
        if self.text is not None:
            self.text.append(chars)

    def endElement(self, name):
        if self.target_stack:
            path, target = self.target_stack[-1]
            if path == '/'.join(self.path_stack):
                self.target_stack.pop()
                target.end(self, ''.join(self.text) if self.text is not None else '')
                self.text = None

        self.path_stack.pop()


def parse(url, stream, max_episodes=0):
    handler = PodcastHandler(url, max_episodes)
    sax.parse(stream, handler)
    return handler.data

