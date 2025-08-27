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

# gpodder.dbusproxy - Expose Podcasts over D-Bus
# Based on a patch by Iwan van der Kleijn <iwanvanderkleyn@gmail.com>
# See also: http://gpodder.org/bug/699
import logging

from gi.repository import Gio, GLib

import gpodder
from gpodder import util

logger = logging.getLogger(__name__)


def first_line(txt):
    lines = util.remove_html_tags(txt).strip().splitlines()
    if not lines or lines[0] == '':
        return ''
    else:
        return lines[0]


def or_empty_str(txt):
    """Can't marshal the None value as a string, so use this wrapper to be safe."""
    return txt or ''


xml = f"""
<node>
  <interface name='{gpodder.dbus_podcasts}'>
      <method name='check_for_updates'>
      </method>
      <method name='get_episode_title'>
          <arg name='episode_url_or_filename' type='s' direction='in'/>
          <arg name='episode_title' type='s' direction='out'/>
          <arg name='channel_title' type='s' direction='out'/>
      </method>
      <method name='get_episodes'>
          <arg name='channel_url' type='s' direction='in'/>
          <arg name='episodes' type='a(sssssbbb)' direction='out'/>
      </method>
      <method name='get_podcasts'>
          <arg name='podcasts' type='a(ssss)' direction='out'/>
      </method>
      <method name='play_or_download_episode'>
          <arg name='episode_urls' type='as' direction='in'/>
          <arg name='success' type='b' direction='out'/>
          <arg name='message' type='s' direction='out'/>
      </method>
  </interface>
  <interface name='{gpodder.dbus_interface}'>
      <method name='show_gui_window'>
      </method>
      <method name='offer_new_episodes'>
          <arg name='channel_urls' type='as' direction='in'/>
          <arg name='new_episodes' type='b' direction='out'/>
      </method>
      <method name='subscribe_to_url'>
          <arg name='url' type='s' direction='in'/>
      </method>
      <method name='mark_episode_played'>
          <arg name='filename' type='s' direction='in'/>
          <arg name='success' type='b' direction='out'/>
      </method>
  </interface>
</node>
"""


class DBusPodcastsProxy:
    """Implements API accessible through D-Bus.

    Methods on DBusPodcastsProxy can be called by D-Bus clients. They implement
    safe-guards to work safely over D-Bus while having type signatures applied
    for parameter and return values.
    """

    def __init__(self, get_podcast_list,
            check_for_updates, playback_episodes,
            download_episodes, episode_from_uri,
            show_gui_window,
            offer_new_episodes,
            subscribe_to_url,
            mark_episode_played,
            gdbus_conn):
        self._get_podcasts = get_podcast_list
        self._on_check_for_updates = check_for_updates
        self._playback_episodes = playback_episodes
        self._download_episodes = download_episodes
        self._episode_from_uri = episode_from_uri
        self._show_gui_window = show_gui_window
        self._offer_new_episodes = offer_new_episodes
        self._subscribe_to_url = subscribe_to_url
        self._mark_episode_played = mark_episode_played

        self._node = Gio.DBusNodeInfo.new_for_xml(xml)

        gdbus_conn.register_object(
            # Set the object path:
            gpodder.dbus_default_object_path,
            # Specify the interface via index
            # (as defined above in the XML):
            self._node.interfaces[0],
            self.on_handle_method_call,  # method_call
            None,  # get_property unused
            None,  # set_property unused
        )
        gdbus_conn.register_object(
            # Set the object path:
            gpodder.dbus_default_object_path,
            # Specify the interface via index
            # (as defined above in the XML):
            self._node.interfaces[1],
            self.on_handle_method_call,  # method_call
            None,  # get_property unused
            None,  # set_property unused
        )

    def _get_episode_refs(self, urls):
        """Get Episode instances associated with URLs."""
        episodes = []
        for p in self._get_podcasts():
            for e in p.get_all_episodes():
                if e.url in urls:
                    episodes.append(e)
        return episodes

    def get_podcasts(self):
        """Get all podcasts in gPodder's subscription list."""
        def podcast_to_tuple(podcast):
            title = podcast.title
            url = podcast.url
            description = first_line(podcast.description)
            cover_file = ''

            return (title, url, description, cover_file)

        res = [podcast_to_tuple(p) for p in self._get_podcasts()]
        return GLib.Variant('(a(ssss))', (res,))

    def get_episode_title(self, url):
        episode = self._episode_from_uri(url)

        title, channel_title = ('', '')
        if episode is not None:
            title, channel_title = episode.title, episode.channel.title

        return GLib.Variant('(ss)', (title, channel_title))

    def get_episodes(self, url):
        """Return all episodes of the podcast with the given URL."""
        def episode_to_tuple(episode):
            title = episode.title
            url = episode.url
            description = first_line(episode._text_description)
            filename = or_empty_str(episode.local_filename(False, check_only=True))  # None when not downloaded
            file_type = episode.file_type()
            is_new = (episode.state == gpodder.STATE_NORMAL and episode.is_new)
            is_downloaded = episode.was_downloaded(and_exists=True)
            is_deleted = (episode.state == gpodder.STATE_DELETED)

            return (title, url, description, filename, file_type, is_new, is_downloaded, is_deleted)

        res = []
        for channel in self._get_podcasts():
            if channel.url == url:
                res = [episode_to_tuple(e) for e in channel.get_all_episodes()]
                break

        return GLib.Variant('(a(sssssbbb))', (res,))

    def play_or_download_episode(self, urls):
        """Play (or download) a list of episodes given by URL."""
        episodes = self._get_episode_refs(urls)
        if not episodes:
            return (0, 'No episodes found')

        to_playback = [e for e in episodes if e.was_downloaded(and_exists=True)]
        to_download = [e for e in episodes if e not in to_playback]

        if to_playback:
            self._playback_episodes(to_playback)

        if to_download:
            self._download_episodes(to_download)

        return GLib.Variant('(bs)', (True, 'Success'))

    def mark_episode_played(self, filename):
        res = False
        for p in self._get_podcasts():
            for e in p.get_all_episodes():
                if e.local_filename(create=False, check_only=True) == filename:
                    res = self._mark_episode_played(e)
                    break
        return GLib.Variant('(b)', (res,))

    def on_handle_method_call(self, conn, sender, path, iname, method, params, invo):
        if method == 'check_for_updates':
            return invo.return_value(self._on_check_for_updates())
        elif method == 'get_episode_title':
            return invo.return_value(self.get_episode_title(params[0]))
        elif method == 'get_episodes':
            return invo.return_value(self.get_episodes(params[0]))
        elif method == 'get_podcasts':
            return invo.return_value(self.get_podcasts())
        elif method == 'play_or_download_episode':
            return invo.return_value(self.play_or_download_episode(params[0]))
        elif method == 'show_gui_window':
            return invo.return_value(self._show_gui_window())
        elif method == 'offer_new_episodes':
            return invo.return_value(GLib.Variant('(b)', (self._offer_new_episodes(params[0]), )))
        elif method == 'subscribe_to_url':
            return invo.return_value(self._subscribe_to_url(params[0]))
        elif method == 'mark_episode_played':
            return invo.return_value(self.mark_episode_played(params[0]))
        logger.warning("NOT HANDLING %s(%r) %r", method, params, invo)
