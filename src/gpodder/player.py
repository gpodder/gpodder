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
# gpodder.player - Podcatcher implementation of the Media Player D-Bus API
# Thomas Perl <thp@gpodder.org>; 2010-04-25
#

#
# This API specification aims at providing a documented, easy-to-use API for
# getting and setting the media player position via D-Bus. This should allow
# media players (such as Panucci) and podcast aggregators (such as gPodder) to
# work together and synchronize the playback position of media files.
#
# == Interface: org.gpodder.player ==
#
# - PlaybackStarted(uint32 position, string file_uri)
#
#   Emitted when the media player starts playback of a given file at file_uri
#   at the position position.
#
#
# - PlaybackStopped(uint32 start_position, uint32 end_position,
#                   uint32 total_time, string file_uri)
#
#   Emitted when the user stops/pauses playback, when the playback ends or the
#   player is closed. The file URI is in file_uri, the start time of the
#   segment that has just been played is in start_position, the stop time in
#   end_position and the (detected) total time of the file is in total_time.
#
#   Seeking in the file should also emit a PlaybackStopped signal (at the
#   position where the seek is initialized) and a PlaybackStarted signal (at
#   the position to which the seek jumps).
#


import urllib.error
import urllib.parse
import urllib.request

import gpodder


class MediaPlayerDBusReceiver(object):
    INTERFACE = 'org.gpodder.player'
    SIGNAL_STARTED = 'PlaybackStarted'
    SIGNAL_STOPPED = 'PlaybackStopped'

    def __init__(self, on_play_event):
        self.on_play_event = on_play_event

        self.bus = gpodder.dbus_session_bus
        self.bus.add_signal_receiver(self.on_playback_started,
                                     self.SIGNAL_STARTED,
                                     self.INTERFACE,
                                     None,
                                     None)
        self.bus.add_signal_receiver(self.on_playback_stopped,
                                     self.SIGNAL_STOPPED,
                                     self.INTERFACE,
                                     None,
                                     None)

    def on_playback_started(self, position, file_uri):
        pass

    def on_playback_stopped(self, start, end, total, file_uri):
        if file_uri.startswith('/'):
            file_uri = 'file://' + urllib.parse.quote(file_uri)
        self.on_play_event(start, end, total, file_uri)
