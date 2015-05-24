#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2015 Thomas Perl and the gPodder Team
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

# gpodder.dbusproxy - Expose Podcasts over D-Bus
# Based on a patch by Iwan van der Kleijn <iwanvanderkleyn@gmail.com>
# See also: http://gpodder.org/bug/699

import gpodder

from gpodder import util

import dbus
import dbus.service

def safe_str(txt):
    if txt:
        return txt.encode()
    else:
        return ''

def safe_first_line(txt):
    txt = safe_str(txt)
    lines = util.remove_html_tags(txt).strip().splitlines()
    if not lines or lines[0] == '':
        return ''
    else:
        return lines[0]

class DBusPodcastsProxy(dbus.service.Object):
    """ Implements API accessible through D-Bus

    Methods on DBusPodcastsProxy can be called by D-Bus clients. They implement
    safe-guards to work safely over D-Bus while having type signatures applied
    for parameter and return values.
    """

    #DBusPodcastsProxy(lambda: self.channels, self.on_itemUpdate_activate(), self.playback_episodes, self.download_episode_list, bus_name)
    def __init__(self, get_podcast_list, \
            check_for_updates, playback_episodes, \
            download_episodes, episode_from_uri, \
            bus_name):
        self._get_podcasts = get_podcast_list
        self._on_check_for_updates = check_for_updates
        self._playback_episodes = playback_episodes
        self._download_episodes = download_episodes
        self._episode_from_uri = episode_from_uri
        dbus.service.Object.__init__(self, \
                object_path=gpodder.dbus_podcasts_object_path, \
                bus_name=bus_name)

    def _get_episode_refs(self, urls):
        """Get Episode instances associated with URLs"""
        episodes = []
        for p in self._get_podcasts():
            for e in p.get_all_episodes():
                if e.url in urls:
                    episodes.append(e)
        return episodes

    @dbus.service.method(dbus_interface=gpodder.dbus_podcasts, in_signature='', out_signature='a(ssss)')
    def get_podcasts(self):
        """Get all podcasts in gPodder's subscription list"""
        def podcast_to_tuple(podcast):
            title = safe_str(podcast.title)
            url = safe_str(podcast.url)
            description = safe_first_line(podcast.description)
            cover_file = ''

            return (title, url, description, cover_file)

        return [podcast_to_tuple(p) for p in self._get_podcasts()]

    @dbus.service.method(dbus_interface=gpodder.dbus_podcasts, in_signature='s', out_signature='ss')
    def get_episode_title(self, url):
        episode = self._episode_from_uri(url)

        if episode is not None:
            return episode.title, episode.channel.title

        return ('', '')

    @dbus.service.method(dbus_interface=gpodder.dbus_podcasts, in_signature='s', out_signature='a(sssssbbb)')
    def get_episodes(self, url):
        """Return all episodes of the podcast with the given URL"""
        podcast = None
        for channel in self._get_podcasts():
            if channel.url == url:
                podcast = channel
                break

        if podcast is None:
            return []

        def episode_to_tuple(episode):
            title = safe_str(episode.title)
            url = safe_str(episode.url)
            description = safe_first_line(episode.description)
            filename = safe_str(episode.download_filename)
            file_type = safe_str(episode.file_type())
            is_new = (episode.state == gpodder.STATE_NORMAL and episode.is_new)
            is_downloaded = episode.was_downloaded(and_exists=True)
            is_deleted = (episode.state == gpodder.STATE_DELETED)

            return (title, url, description, filename, file_type, is_new, is_downloaded, is_deleted)

        return [episode_to_tuple(e) for e in podcast.get_all_episodes()]

    @dbus.service.method(dbus_interface=gpodder.dbus_podcasts, in_signature='as', out_signature='(bs)')
    def play_or_download_episode(self, urls):
        """Play (or download) a list of episodes given by URL"""
        episodes = self._get_episode_refs(urls)
        if not episodes:
            return (0, 'No episodes found')

        to_playback = [e for e in episodes if e.was_downloaded(and_exists=True)]
        to_download = [e for e in episodes if e not in to_playback]

        if to_playback:
            self._playback_episodes(to_playback)

        if to_download:
            self._download_episodes(to_download)

        return (1, 'Success')

    @dbus.service.method(dbus_interface=gpodder.dbus_podcasts, in_signature='', out_signature='')
    def check_for_updates(self):
        """Check for new episodes or offer subscriptions"""
        self._on_check_for_updates()

