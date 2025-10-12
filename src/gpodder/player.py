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
# This provides a base class for player monitoring and control: PlayerInterface.
# See mpris-listener.py for the concrete implementation
#

import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from abc import ABCMeta, abstractmethod

from gpodder import registry

from .model import episode_object_by_uri
from .services import AutoRegisterObserver, ObservableService

logger = logging.getLogger(__name__)


class PlayerInterface(ObservableService, metaclass=ABCMeta):
    """Example base class and common value definitions for player control implementations.

    They must be a subclass of ObservableService, with following signals.
    """

    SIGNAL_STARTED = 'PlaybackStarted'  # start_position_seconds, total_seconds, episode
    SIGNAL_STOPPED = 'PlaybackStopped'  # start_position_seconds, end_position_seconds, total_seconds, episode
    SIGNAL_EXITED = 'PlayerExited'  # episode

    def __init__(self, model):
        signals = [self.SIGNAL_STARTED, self.SIGNAL_STOPPED, self.SIGNAL_EXITED]
        super().__init__(signals)
        self.model = model
        self._currently_playing = {}

    @abstractmethod
    def seek(self, episode, position):
        """Tell player currently playing the file identified by episode to jump to position (float, in seconds)."""
        ...

    def _on_playback_started(self, start, total, file_uri):
        """Call from subclasses to update currently playing and notify observers."""
        if file_uri.startswith('/'):
            file_uri = 'file://' + urllib.parse.quote(file_uri)
        logger.info('_on_playback_started: %s: %d/%d', file_uri, start, total)
        episode = self.__save(-1000, start, total, file_uri)
        if episode:
            self.notify(self.SIGNAL_STARTED, start, total, episode)

    def _on_playback_stopped(self, start, end, total, file_uri):
        """Call from subclasses to update currently playing and notify observers."""
        if file_uri.startswith('/'):
            file_uri = 'file://' + urllib.parse.quote(file_uri)
        if (start == 0 and end == 0 and total == 0):
            # Ignore bogus play event
            return
        if end < start + 5:
            # Ignore "less than five seconds" segments,
            # as they can happen with seeking, etc...
            return None
        logger.info('_on_playback_stopped: %s: %d--%d/%d',
            file_uri, start, end, total)
        episode = self.__save(start, end, total, file_uri)
        if episode:
            self.notify(self.SIGNAL_STOPPED, start, end, total, episode)

    def _on_player_exited(self, file_uri):
        """Call from subclasses to update currently playing and notify observers."""
        if file_uri.startswith('/'):
            file_uri = 'file://' + urllib.parse.quote(file_uri)
        logger.info('PlayerExited: %s', file_uri)
        episode = self.__episode_by_uri(file_uri)
        if file_uri in self._currently_playing:
            del self._currently_playing[file_uri]
        if episode:
            self.notify(self.SIGNAL_EXITED, episode)

    def __episode_by_uri(self, file_uri):
        episode = self._currently_playing.get(file_uri, {}).get("episode")
        if not episode:
            episode = episode_object_by_uri(self.model.get_podcasts(), file_uri)
        return episode

    def __save(self, start, end, total, file_uri):
        episode = self.__episode_by_uri(file_uri)
        if file_uri not in self._currently_playing:
            self._currently_playing[file_uri] = {}
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
        return episode


class MyGPOClientObserver(AutoRegisterObserver):
    """Listen to PlayerInterface and send events to gpodder.net."""

    def __init__(self, mygpoclient):
        super().__init__(registry.player_interface, {
            PlayerInterface.SIGNAL_STOPPED: self._save_stopped_to_mygpo
        }, label="MyGPOClientObserver")
        self.mygpoclient = mygpoclient

    def _save_stopped_to_mygpo(self, start, end, total, episode):
        # Submit this action to the webservice
        if start >= 0:
            # Submit this action to the webservice
            self.mygpoclient.on_playback_full(episode, start, end, total)
