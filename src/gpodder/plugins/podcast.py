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

import podcastparser

import urllib.request, urllib.error, urllib.parse

import logging

logger = logging.getLogger(__name__)

class PodcastParserFeed(object):
    def __init__(self, channel, max_episodes):
        url = channel.authenticate_url(channel.url)

        logger.info('Parsing via podcastparser: %s', url)

        headers = {}
        if channel.http_etag:
            headers['If-None-Match'] = channel.http_etag
        if channel.http_last_modified:
            headers['If-Modified-Since'] = channel.http_last_modified

        try:
            stream = util.urlopen(url, headers)
            self.status = 200
            info = stream.info()
            self.etag = info.get('etag')
            self.modified = info.get('last-modified')
            self.parsed = podcastparser.parse(url, stream, max_episodes)
        except urllib.error.HTTPError as error:
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
        return self.parsed.get('cover_url')

    def get_link(self):
        return self.parsed.get('link', '')

    def get_description(self):
        return self.parsed.get('description', '')

    def get_payment_url(self):
        return self.parsed.get('payment_url')

    def _pick_enclosure(self, episode_dict):
        if not episode_dict['enclosures']:
            return False

        # FIXME: YouTube and Vimeo handling

        # FIXME: Pick the right enclosure from multiple ones
        episode_dict.update(episode_dict['enclosures'][0])
        del episode_dict['enclosures']

        return True

    def get_new_episodes(self, channel):
        existing_guids = dict((episode.guid, episode) for episode in channel.children)
        seen_guids = [entry['guid'] for entry in self.parsed['episodes']]
        new_episodes = []

        for episode_dict in self.parsed['episodes']:
            if not self._pick_enclosure(episode_dict):
                continue

            episode = existing_guids.get(episode_dict['guid'])
            if episode is None:
                episode = channel.episode_factory(episode_dict.items())
                new_episodes.append(episode)
                logger.info('Found new episode: %s', episode.guid)
            else:
                episode.update_from_dict(episode_dict)
                logger.info('Updating existing episode: %s', episode.guid)
            episode.save()

        return new_episodes, seen_guids

@model.register_custom_handler
def podcast_parser_handler(channel, max_episodes):
    return PodcastParserFeed(channel, max_episodes)

