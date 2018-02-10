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

import gpodder

_ = gpodder.gettext

from gpodder import model
from gpodder import util

import json

import logging
import os
import time

import re
import email
import urllib.request, urllib.parse, urllib.error


# gPodder's consumer key for the Soundcloud API
CONSUMER_KEY = 'zrweghtEtnZLpXf3mlm8mQ'


logger = logging.getLogger(__name__)


def soundcloud_parsedate(s):
    """Parse a string into a unix timestamp

    Only strings provided by Soundcloud's API are
    parsed with this function (2009/11/03 13:37:00).
    """
    m = re.match(r'(\d{4})/(\d{2})/(\d{2}) (\d{2}):(\d{2}):(\d{2})', s)
    return time.mktime(tuple([int(x) for x in m.groups()]+[0, 0, -1]))

def get_param(s, param='filename', header='content-disposition'):
    """Get a parameter from a string of headers

    By default, this gets the "filename" parameter of
    the content-disposition header. This works fine
    for downloads from Soundcloud.
    """
    msg = email.message_from_string(s)
    if header in msg:
        value = msg.get_param(param, header=header)
        decoded_list = email.header.decode_header(value)
        value = []
        for part, encoding in decoded_list:
            if encoding:
                value.append(part.decode(encoding))
            else:
                value.append(str(part))
        return ''.join(value)

    return None

def get_metadata(url):
    """Get file download metadata

    Returns a (size, type, name) from the given download
    URL. Will use the network connection to determine the
    metadata via the HTTP header fields.
    """
    track_fp = util.urlopen(url)
    headers = track_fp.info()
    filesize = headers['content-length'] or '0'
    filetype = headers['content-type'] or 'application/octet-stream'
    headers_s = '\n'.join('%s:%s'%(k,v) for k, v in list(headers.items()))
    filename = get_param(headers_s) or os.path.basename(os.path.dirname(url))
    track_fp.close()
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
        global CONSUMER_KEY
        key = ':'.join((self.username, 'user_info'))
        if key in self.cache:
            return self.cache[key]

        try:
            json_url = 'https://api.soundcloud.com/users/%s.json?consumer_key=%s' % (self.username, CONSUMER_KEY)
            user_info = json.loads(util.urlopen(json_url).read().decode('utf-8'))
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
        global CONSUMER_KEY
        try:
            json_url = 'https://api.soundcloud.com/users/%(user)s/%(feed)s.json?filter=downloadable&consumer_key=%(consumer_key)s&limit=200' \
                    % { "user":self.get_user_id(), "feed":feed, "consumer_key": CONSUMER_KEY }
            logger.debug("loading %s", json_url)

            json_tracks = json.loads(util.urlopen(json_url).read().decode('utf-8'))
            tracks = [track for track in json_tracks if track['downloadable']]
            total_count = len(tracks) + len([track for track in json_tracks
                                              if not track['downloadable']])

            if len(tracks) == 0 and total_count > 0:
                logger.warn("Download of all %i %s of user %s is disabled" %
                            (total_count, feed, self.username))
            else:
                logger.info("%i/%i downloadable tracks for user %s %s feed" %
                            (len(tracks), total_count, self.username, feed))

            for track in tracks:
                # Prefer stream URL (MP3), fallback to download URL
                url = track.get('stream_url', track['download_url']) + \
                    '?consumer_key=%(consumer_key)s' \
                    % { 'consumer_key': CONSUMER_KEY }
                if url not in self.cache:
                    try:
                        self.cache[url] = get_metadata(url)
                    except:
                        continue
                filesize, filetype, filename = self.cache[url]

                yield {
                    'title': track.get('title', track.get('permalink')) or _('Unknown track'),
                    'link': track.get('permalink_url') or 'https://soundcloud.com/'+self.username,
                    'description': track.get('description') or _('No description available'),
                    'url': url,
                    'file_size': int(filesize),
                    'mime_type': filetype,
                    'guid': track.get('permalink', track.get('id')),
                    'published': soundcloud_parsedate(track.get('created_at', None)),
                }
        finally:
            self.commit_cache()

class SoundcloudFeed(object):
    URL_REGEX = re.compile('https?://([a-z]+\.)?soundcloud\.com/([^/]+)$', re.I)

    @classmethod
    def handle_url(cls, url):
        m = cls.URL_REGEX.match(url)
        if m is not None:
            subdomain, username = m.groups()
            return cls(username)

    def __init__(self, username):
        self.username = username
        self.sc_user = SoundcloudUser(username)

    def get_title(self):
        return _('%s on Soundcloud') % self.username

    def get_image(self):
        return self.sc_user.get_coverart()

    def get_link(self):
        return 'https://soundcloud.com/%s' % self.username

    def get_description(self):
        return _('Tracks published by %s on Soundcloud.') % self.username

    def get_new_episodes(self, channel, existing_guids):
        return self._get_new_episodes(channel, existing_guids, 'tracks')

    def _get_new_episodes(self, channel, existing_guids, track_type):
        tracks = [t for t in self.sc_user.get_tracks(track_type)]

        seen_guids = [track['guid'] for track in tracks]
        episodes = []

        for track in tracks:
            if track['guid'] not in existing_guids:
                episode = channel.episode_factory(track)
                episode.save()
                episodes.append(episode)

        return episodes, seen_guids

class SoundcloudFavFeed(SoundcloudFeed):
    URL_REGEX = re.compile('https?://([a-z]+\.)?soundcloud\.com/([^/]+)/favorites', re.I)


    def __init__(self, username):
        super(SoundcloudFavFeed,self).__init__(username)

    def get_title(self):
        return _('%s\'s favorites on Soundcloud') % self.username

    def get_link(self):
        return 'https://soundcloud.com/%s/favorites' % self.username

    def get_description(self):
        return _('Tracks favorited by %s on Soundcloud.') % self.username

    def get_new_episodes(self, channel, existing_guids):
        return self._get_new_episodes(channel, existing_guids, 'favorites')


# Register our URL handlers
model.register_custom_handler(SoundcloudFeed)
model.register_custom_handler(SoundcloudFavFeed)

def search_for_user(query):
    json_url = 'https://api.soundcloud.com/users.json?q=%s&consumer_key=%s' % (urllib.parse.quote(query), CONSUMER_KEY)
    return json.loads(util.urlopen(json_url).read().decode('utf-8'))

