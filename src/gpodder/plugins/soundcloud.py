#!/usr/bin/python
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

# Soundcloud.com API client module for gPodder
# Thomas Perl <thp@gpodder.org>; 2009-11-03
import email
import json
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

import gpodder
from gpodder import feedcore, model, registry, util

_ = gpodder.gettext


# gPodder's client_id for the Soundcloud API
client_id = None

access_token = None
token_expire = datetime.now()

logger = logging.getLogger(__name__)


class SoundcloudException(Exception):
    pass


def get_client_id():
    response = util.urlopen("https://w.soundcloud.com/player/?url=http")
    for result in re.finditer(r"https://widget\.sndcdn\.com/widget-[0-9a-f\-]+\.js", response.text):
        match = re.search(r'client_id.*?\"(.+?)\"', util.urlopen(result.group(0)).text)
        if match:
            return match.group(1)


def soundcloud_url_from_permalink(url):
    return urlopen_with_token(url).json()["url"]


def urlopen_with_token(url):
    global access_token
    global token_expire
    global client_id
    if client_id is None:
        client_id = get_client_id()
    if "?" in url:
        url_without_id = url + "&client_id="
    else:
        url_without_id = url + "?client_id="
    start = time.time()
    response = util.urlopen(f"{url_without_id}{client_id}")
    logger.debug(f"Opened {url_without_id}{client_id} in {int((time.time() - start) * 1000)} ms")
    if response.status_code == 401:
        # Retry
        client_id = get_client_id()
    response = util.urlopen(f"{url_without_id}{client_id}")
    if response.status_code == 401:
        # Client ID doesn't work
        raise SoundcloudException("Client ID does not seem to work")
    return response


def soundcloud_parsedate(s):
    """Parse a string into a unix timestamp

    Only strings provided by Soundcloud's API are
    parsed with this function (2009/11/03 13:37:00).
    """
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z', s)
    return time.mktime(tuple([int(x) for x in m.groups()] + [0, 0, -1]))


def get_metadata(url):
    """Get file download metadata

    Returns a (size, type, name) from the given download
    URL. Will use the network connection to determine the
    metadata via the HTTP header fields.
    """
    track_response = util.urlopen(url, method="HEAD")
    filesize = int(track_response.headers['content-length']) or 0
    filetype = track_response.headers['content-type'] or 'application/octet-stream'
    headers_s = '\n'.join('%s:%s' % (k, v) for k, v in list(track_response.headers.items()))
    filename = util.get_header_param(track_response.headers, 'filename', 'content-disposition') \
        or os.path.basename(os.path.dirname(url))
    track_response.close()
    return filesize, filetype, filename


class SoundcloudUser(object):
    def __init__(self, username):
        self.username = username
        self.cache_file = os.path.join(gpodder.home, 'Soundcloud')
        if os.path.exists(self.cache_file):
            try:
                self.cache = json.load(open(self.cache_file, 'r'))
            except:
                self.cache = {}
        else:
            self.cache = {}

    def commit_cache(self):
        json.dump(self.cache, open(self.cache_file, 'w'))

    def get_user_info(self):
        key = ':'.join((self.username, 'user_info'))
        if key in self.cache:
            if self.cache[key].get('code', 200) == 200:
                return self.cache[key]

        try:
            # find user ID in soundcloud page
            url = 'https://soundcloud.com/' + self.username
            r = urlopen_with_token(url)
            if not r.ok:
                raise Exception('Soundcloud "%s": %d %s' % (url, r.status_code, r.reason))
            uid = re.search(r'"https://api.soundcloud.com/users/([0-9]+)"', r.text)
            if not uid:
                raise Exception('Soundcloud user ID not found for "%s"' % url)
            uid = int(uid.group(1))

            # load user info API
            json_url = 'https://api-v2.soundcloud.com/users/%d' % uid
            r = urlopen_with_token(json_url)
            if not r.ok:
                raise Exception('Soundcloud "%s": %d %s' % (json_url, r.status_code, r.reason))
            user_info = json.loads(r.text)
            if user_info.get('code', 200) != 200:
                raise Exception('Soundcloud "%s": %s' % (json_url, user_info.get('message', '')))

            self.cache[key] = user_info
        finally:
            self.commit_cache()

        return user_info

    def get_coverart(self):
        user_info = self.get_user_info()
        return user_info.get('avatar_url', None)

    def get_user_id(self):
        user_info = self.get_user_info()
        return user_info.get('id', None)

    def get_tracks(self, feed):
        """Get a generator of tracks from a SC user

        The generator will give you a dictionary for every
        track it can find for its user."""
        try:
            json_url = ('https://api-v2.soundcloud.com/users/{user}/{feed}'
                        '?limit=200'.format(user=self.get_user_id(), feed=feed))
            logger.debug("loading %s", json_url)

            json_tracks = urlopen_with_token(json_url).json()
            tracks = [track for track in json_tracks["collection"] if track['streamable'] or track['downloadable']]
            total_count = len(json_tracks)

            if len(tracks) == 0 and total_count > 0:
                logger.warn("Download of all %i %s of user %s is disabled" %
                            (total_count, feed, self.username))
            else:
                logger.info("%i/%i downloadable tracks for user %s %s feed" %
                            (len(tracks), total_count, self.username, feed))

            for track in tracks:
                # Try to get Streaming URL (MP3)
                transcodings = track['media']['transcodings']
                url = None
                perma_url = None

                for transcoding in transcodings:
                    if transcoding['format']['protocol'] == "progressive" and transcoding['format']['mime_type'] == "audio/mpeg":
                        perma_url = transcoding['url']
                        url = soundcloud_url_from_permalink(perma_url)
                if not url:
                    logger.warning(f"Didn't find downloadable mp3 for track {track['title']}")
                if url not in self.cache:
                    try:
                        self.cache[url] = get_metadata(url)
                    except:
                        continue

                filesize, _unused, _unused = self.cache[url]

                yield {
                    'title': track.get('title', track.get('permalink')) or _('Unknown track'),
                    'link': track.get('permalink_url') or 'https://soundcloud.com/' + self.username,
                    'description': track.get('description') or _('No description available'),
                    'url': url,
                    'perma_url': perma_url,
                    'file_size': filesize,
                    'mime_type': "audio/mpeg",
                    'guid': str(track.get('permalink', track.get('id'))),
                    'published': soundcloud_parsedate(track.get('created_at', None)),
                }
        finally:
            self.commit_cache()


class SoundcloudFeed(model.Feed):
    URL_REGEX = re.compile(r'https?://([a-z]+\.)?soundcloud\.com/([^/]+)$', re.I)

    @classmethod
    def fetch_channel(cls, channel, max_episodes=0):
        url = channel.authenticate_url(channel.url)
        return cls.handle_url(url, max_episodes)

    @classmethod
    def handle_url(cls, url, max_episodes):
        m = cls.URL_REGEX.match(url)
        if m is not None:
            subdomain, username = m.groups()
            return feedcore.Result(feedcore.UPDATED_FEED, cls(username, max_episodes))

    def __init__(self, username, max_episodes):
        self.username = username
        self.sc_user = SoundcloudUser(username)
        self.max_episodes = max_episodes

    def get_title(self):
        return _('%s on Soundcloud') % self.username

    def get_cover_url(self):
        return self.sc_user.get_coverart()

    def get_link(self):
        return 'https://soundcloud.com/%s' % self.username

    def get_description(self):
        return _('Tracks published by %s on Soundcloud.') % self.username

    def get_new_episodes(self, channel, existing_guids):
        return self._get_new_episodes(channel, existing_guids, 'tracks')

    def get_next_page(self, channel, max_episodes=0):
        # one could return more, but it would consume too many api calls
        # (see PR #184)
        return None

    def _get_new_episodes(self, channel, existing_guids, track_type):
        tracks = list(self.sc_user.get_tracks(track_type))
        if self.max_episodes > 0:
            tracks = tracks[:self.max_episodes]

        seen_guids = set(track['guid'] for track in tracks)
        existing_episode_mappings = {
            x.guid: x for x in channel.get_all_episodes()
        }
        episodes = []

        for track in tracks:
            if track['guid'] not in existing_guids:
                del track['perma_url']
                episode = channel.episode_factory(track)
                episode.save()
                episodes.append(episode)
            else:
                existing_episode_mappings[track['guid']].url = soundcloud_url_from_permalink(track.pop('perma_url'))
        return episodes, seen_guids


class SoundcloudFavFeed(SoundcloudFeed):
    URL_REGEX = re.compile(r'https?://([a-z]+\.)?soundcloud\.com/([^/]+)/favorites', re.I)

    def __init__(self, username):
        super(SoundcloudFavFeed, self).__init__(username)

    def get_title(self):
        return _('%s\'s favorites on Soundcloud') % self.username

    def get_link(self):
        return 'https://soundcloud.com/%s/favorites' % self.username

    def get_description(self):
        return _('Tracks favorited by %s on Soundcloud.') % self.username

    def get_new_episodes(self, channel, existing_guids):
        return self._get_new_episodes(channel, existing_guids, 'favorites')


# Register our URL handlers
registry.feed_handler.register(SoundcloudFeed.fetch_channel)
registry.feed_handler.register(SoundcloudFavFeed.fetch_channel)


def search_for_user(query):
    json_url = 'https://api-v2.soundcloud.com/search/users?q=%s' % (urllib.parse.quote(query))
    return urlopen_with_token(json_url).json()["collection"]
