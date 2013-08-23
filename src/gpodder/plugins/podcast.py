# -*- coding: utf-8 -*-
#
# gpodder.plugins.podcast: Faster Podcast Parser module for gPodder (2012-12-29)
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


import gpodder

from gpodder import model
from gpodder import util

# XXX: Avoid "cross-importing" of plugins
from gpodder.plugins import youtube
from gpodder.plugins import vimeo

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
            del episode_dict['enclosures']

            # XXX: Move special cases to {youtube,vimeo}.py as subclass
            if (youtube.is_video_link(episode_dict['link']) or
                    vimeo.is_video_link(episode_dict['link'])):
                episode_dict['url'] = episode_dict['link']
                return True

            return False

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

