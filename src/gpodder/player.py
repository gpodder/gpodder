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

#
# gpodder.player - Common code to handle playback
#
# This uses the registry to discover player_control interfaces.
# It then provides common code to get a stateful view from the events
#

import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from abc import ABCMeta, abstractmethod

from gpodder import registry

from .model import episode_object_by_uri
from .services import ObservableService

logger = logging.getLogger(__name__)


class PlayerControl(ObservableService, metaclass=ABCMeta):
    """Example base class and common value definitions for player control implementations.

    They must be a subclass of ObservableService, with following signals."""
    SIGNAL_STARTED = 'PlaybackStarted'  # start_position_seconds, total_seconds, file_uri
    SIGNAL_STOPPED = 'PlaybackStopped'  # start_position_seconds, end_position_seconds, total_seconds, file_uri
    SIGNAL_EXITED = 'PlayerExited'  # file_uri

    def __init__(self):
        signals = [self.SIGNAL_STARTED, self.SIGNAL_STOPPED, self.SIGNAL_EXITED]
        super().__init__(signals)

    @abstractmethod
    def seek(self, file_uri, position):
        """Tell player currently playing the file identified by file_uri to jump to position (float, in seconds)."""
        ...


class PlayerController:
    """Monitors PlayerControl implementations.

    Keeps track of currently playing files and pushes updates to gpodder.net via mygpo_client.
    """
    def __init__(self, model):
        self._player_control = None
        self.model = model
        self._currently_playing = {}
        self.mygpo_client = None
        self.on_episode_status_changed = None
        self._currently_playing = {}
        registry.player_control.add_observer(self._player_control_observer)
        self._player_control_observer()  # if a PlayerControl already exists

    def set_mygpo_client(self, mygpo_client):
        """Register the mypo_client to send events to the gpodder.net server"""
        self.mygpo_client = mygpo_client

    def set_on_episode_status_changed(self, on_episode_status_changed):
        """Register the `callback(episode)` to be notified once an episode has been updated.

        This is only used by gtkui/main.py."""
        self.on_episode_status_changed = on_episode_status_changed

    def _player_control_observer(self):
        """Internal method to be notified of PlayerControl implementation changes."""
        player_control = registry.player_control.resolve(None, None)
        if self._player_control is not None and player_control == self._player_control:
            logger.debug("Still using PlayerControl=%r", self._player_control)
            return
        if self._player_control is not None and player_control != self._player_control:
            # unregister from old player_control
            self._player_control.unregister(PlayerControl.SIGNAL_STARTED, self._on_playback_started)
            self._player_control.unregister(PlayerControl.SIGNAL_STOPPED, self._on_playback_stopped)
            self._player_control.unregister(PlayerControl.SIGNAL_EXITED, self._on_player_exited)
        if player_control:
            self._player_control = player_control
            logger.debug("A PlayerControl implementation is active (%s), registering to it", self._player_control)
            self._player_control.register(PlayerControl.SIGNAL_STARTED, self._on_playback_started)
            self._player_control.register(PlayerControl.SIGNAL_STOPPED, self._on_playback_stopped)
            self._player_control.register(PlayerControl.SIGNAL_EXITED, self._on_player_exited)
        else:
            logger.debug("No PlayerControl implementation is active")
        self._currently_playing = {}

    def currently_playing(self):
        # FIXME: copy? property?
        return self._currently_playing

    def _on_playback_started(self, start, total, file_uri):
        if file_uri.startswith('/'):
            file_uri = 'file://' + urllib.parse.quote(file_uri)
        if file_uri in self._currently_playing:
            # FIXME: implement _currently_playing as a list, or use the player id?
            logger.warning("Overriding currently playing %s", file_uri)
        self._currently_playing[file_uri] = {
            "position": start,
            "total": total,
            "episode": None,
        }
        self._save(-1000, start, total, file_uri)

    def _on_playback_stopped(self, start, end, total, file_uri):
        logger.debug("Player.on_playback_stopped(%s, %s, %s, %s)", start, end, total, file_uri)
        if file_uri.startswith('/'):
            file_uri = 'file://' + urllib.parse.quote(file_uri)
        if (start == 0 and end == 0 and total == 0):
            # Ignore bogus play event
            return
        self._save(start, end, total, file_uri)

    def _on_player_exited(self, file_uri):
        if file_uri.startswith('/'):
            file_uri = 'file://' + urllib.parse.quote(file_uri)
        if file_uri in self._currently_playing:
            del self._currently_playing[file_uri]
        logger.debug('Received player exited: %s', file_uri)

    def _save(self, start, end, total, file_uri):
        if end < start + 5:
            # Ignore "less than five seconds" segments,
            # as they can happen with seeking, etc...
            return
        logger.debug('Received play action: %s (%d, %d, %d)', file_uri, start, end, total)
        episode = self._currently_playing.get(file_uri, {}).get("episode")
        if not episode:
            episode = episode_object_by_uri(self.model.get_podcasts(), file_uri)
            self._currently_playing[file_uri]["episode"] = episode

        if episode is None:
            logger.info("Unable to find episode for file_uri=%s", file_uri)
        else:
            now = time.time()
            if total > 0:
                episode.total_time = total
            elif total == 0:
                # Assume the episode's total time for the action
                total = episode.total_time
            self._currently_playing[file_uri]["position"] = end
            self._currently_playing[file_uri]["total"] = total
            assert (episode.current_position_updated is None
                    or now >= episode.current_position_updated)
            episode.current_position = end
            episode.current_position_updated = now
            episode.mark(is_played=True)
            episode.save()
            if self.on_episode_status_changed:
                self.on_episode_status_changed(episode)

            # Submit this action to the webservice
            if start >= 0 and self.mygpo_client:
                # Submit this action to the webservice
                self.mygpo_client.on_playback_full(episode, start, end, total)
