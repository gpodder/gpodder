#!/usr/bin/python
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

# Faster Podcast Parser module for gPodder
# Thomas Perl <thp@gpodder.org>; 2012-12-29

import gpodder

_ = gpodder.gettext

from gpodder import model
from gpodder import util
from gpodder import podcastparser

import urllib2

import logging

logger = logging.getLogger(__name__)

def format_modified(modified):
    short_weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    return '%s, %02d %s %04d %02d:%02d:%02d GMT' % (short_weekdays[modified[6]],
            modified[2], months[modified[1] - 1], modified[0], modified[3], modified[4], modified[5])

class PodcastParserFeed(object):
    @classmethod
    def handle_url(cls, url, etag, modified, max_episodes):
        return cls(url, etag, modified, max_episodes)

    def __init__(self, url, etag, modified, max_episodes):
        self.url = url
        logger.info('Parsing via podcastparser: %s', url)
        headers = {}
        if etag:
            headers['If-None-Match'] = etag
        if modified:
            headers['If-Modified-Since'] = format_modified(modified)

        try:
            stream = util.urlopen(url, headers)
            self.status = 200
            info = stream.info()
            self.etag = info.get('etag')
            self.modified = info.get('last-modified')
            self.parsed = podcastparser.parse(url, stream, max_episodes)
        except urllib2.HTTPError, error:
            self.status = error.code
            if error.code == 304:
                logger.info('Not modified')
            else:
                logger.warn('Feed update failed: %s', error)
                raise error

            self.etag = None
            self.modified = None
            self.parsed = None

    def was_updated(self):
        return (self.status == 200)

    def get_etag(self, default):
        return self.etag or default

    def get_modified(self, default):
        return self.modified or default

    def get_title(self):
        return self.parsed['title']

    def get_image(self):
        return self.parsed['cover_url']

    def get_link(self):
        return self.parsed['link']

    def get_description(self):
        return self.parsed['description']

    def get_new_episodes(self, channel, existing_guids):
        seen_guids = [entry['guid'] for entry in self.parsed['entries']]
        episodes = []

        for entry in self.parsed['entries']:
            if entry['guid'] not in existing_guids:
                episode = channel.episode_factory(entry)
                episode.save()
                episodes.append(episode)

        return episodes, seen_guids

# Register our URL handler
model.register_custom_handler(PodcastParserFeed)

