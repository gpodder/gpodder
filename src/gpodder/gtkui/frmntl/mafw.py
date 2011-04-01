#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
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
# Maemo 5 Media Player / MAFW Playback Monitor
# Send playback status information to gPodder using D-Bus
# Thomas Perl <thp@gpodder.org>; 2010-08-16 / 2010-08-17
#

# The code below is based on experimentation with MAFW and real files,
# so it might not work in the general case. It worked fine for me with
# local and streaming files (audio/video), though. Blame missing docs!

import gtk
import gobject
import dbus
import dbus.mainloop
import dbus.service
import dbus.glib
import urllib
import time

import gpodder

class gPodderPlayer(dbus.service.Object):
    # Empty class with method definitions to send D-Bus signals

    def __init__(self, path, name):
        dbus.service.Object.__init__(self, object_path=path, bus_name=name)

    # Signals for gPodder's media player integration
    @dbus.service.signal(dbus_interface='org.gpodder.player', signature='us')
    def PlaybackStarted(self, position, file_uri):
        pass

    @dbus.service.signal(dbus_interface='org.gpodder.player', signature='uuus')
    def PlaybackStopped(self, start_position, end_position, total_time, \
            file_uri):
        pass

class MafwResumeHandler(object):
    # Simple state machine for handling resume with MAFW
    #
    # NoResume ... No desire to resume / error state ("do nothing")
    # Init ....... Want to resume, filename and position set
    # Loaded ..... The correct filename has been loaded
    # Seekable ... The media is seekable (metadata "is-seekable" is True)
    # Playing .... The media is being played back (state_changed with 1)
    # Done ....... The "resume" action has been carried out
    NoResume, Init, Loaded, Seekable, Playing, Done = range(6)

    def __init__(self, playback_monitor):
        self.playback_monitor = playback_monitor
        self.state = MafwResumeHandler.NoResume
        self.filename = None
        self.position = None

    def set_resume_point(self, filename, position):
        self.filename = filename
        self.position = position
        if self.position:
            self.state = MafwResumeHandler.Init
        else:
            self.state = MafwResumeHandler.NoResume

    def on_media_changed(self, filename):
        if self.state == MafwResumeHandler.Init:
            if filename.startswith('file://'):
                filename = urllib.unquote(filename[len('file://'):])
            if self.filename == filename:
                self.state = MafwResumeHandler.Loaded

    def on_metadata_changed(self, key, value):
        if self.state == MafwResumeHandler.Loaded:
            if key == 'is-seekable' and value == True:
                self.state = MafwResumeHandler.Seekable

    def on_state_changed(self, new_state):
        if self.state == MafwResumeHandler.Seekable:
            if new_state == 1:
                self.state = MafwResumeHandler.Playing
                self.playback_monitor.set_position(self.position)
                self.state = MafwResumeHandler.Done


class MafwPlaybackMonitor(object):
    MAFW_RENDERER_OBJECT = 'com.nokia.mafw.renderer.Mafw-Gst-Renderer-Plugin.gstrenderer'
    MAFW_RENDERER_PATH = '/com/nokia/mafw/renderer/gstrenderer'
    MAFW_RENDERER_INTERFACE = 'com.nokia.mafw.renderer'
    MAFW_RENDERER_SIGNAL_MEDIA = 'media_changed'
    MAFW_RENDERER_SIGNAL_STATE = 'state_changed'
    MAFW_RENDERER_SIGNAL_METADATA = 'metadata_changed'

    MAFW_SENDER_PATH = '/org/gpodder/maemo/mafw'

    class MafwPlayState(object):
        Stopped = 0
        Playing = 1
        Paused = 2
        Transitioning = 3

    def __init__(self, bus):
        self.bus = bus
        self._filename = None
        self._is_playing = False
        self._start_time = time.time()
        self._start_position = 0
        self._duration = 0

        self._resume_handler = MafwResumeHandler(self)

        self._player = gPodderPlayer(self.MAFW_SENDER_PATH, \
            dbus.service.BusName(gpodder.dbus_bus_name, self.bus))

        state, object_id = self.get_status()

        self.on_media_changed(0, object_id)
        self.on_state_changed(state)

        self.bus.add_signal_receiver(self.on_media_changed, \
                self.MAFW_RENDERER_SIGNAL_MEDIA, \
                self.MAFW_RENDERER_INTERFACE, \
                None, \
                self.MAFW_RENDERER_PATH)

        self.bus.add_signal_receiver(self.on_state_changed, \
                self.MAFW_RENDERER_SIGNAL_STATE, \
                self.MAFW_RENDERER_INTERFACE, \
                None, \
                self.MAFW_RENDERER_PATH)

        self.bus.add_signal_receiver(self.on_metadata_changed, \
                self.MAFW_RENDERER_SIGNAL_METADATA, \
                self.MAFW_RENDERER_INTERFACE, \
                None, \
                self.MAFW_RENDERER_PATH)

        # Capture requests to the renderer where the position is to be set to
        # something else because we don't get normal signals in these cases
        bus.add_match_string("type='method_call',destination='com.nokia.mafw.renderer.Mafw-Gst-Renderer-Plugin.gstrenderer',path='/com/nokia/mafw/renderer/gstrenderer',interface='com.nokia.mafw.renderer',member='set_position'")
        bus.add_message_filter(self._message_filter)

    def set_resume_point(self, filename, position):
        self._resume_handler.set_resume_point(filename, position)

    def _message_filter(self, bus, message):
        try:
            # message type 1 = dbus.lowlevel.MESSAGE_TYPE_METHOD_CALL
            if message.get_path() == self.MAFW_RENDERER_PATH and \
                    message.get_interface() == self.MAFW_RENDERER_INTERFACE and \
                    message.get_destination() == self.MAFW_RENDERER_OBJECT and \
                    message.get_type() == 1 and \
                    message.get_member() == 'set_position' and \
                    self._is_playing:
                # Fake stop-of-old / start-of-new
                self.on_state_changed(-1)
                self.on_state_changed(self.MafwPlayState.Playing)
        finally:
            return 1 # = dbus.lowlevel.HANDLER_RESULT_NOT_YET_HANDLED

    def object_id_to_filename(self, object_id):
        # Naive, but works for now...
        if object_id.startswith('localtagfs::'):
            if isinstance(object_id, unicode):
                object_id = object_id.encode('utf-8')
            return 'file://'+urllib.quote(urllib.unquote(object_id[object_id.index('%2F'):]))
        elif object_id.startswith('urisource::'):
            return object_id[len('urisource::'):]
        else:
            # This is pretty bad, actually (can happen with other
            # sources, but should not happen for gPodder episodes)
            return object_id

    @property
    def renderer(self):
        o = self.bus.get_object(self.MAFW_RENDERER_OBJECT, \
                self.MAFW_RENDERER_PATH)
        return dbus.Interface(o, self.MAFW_RENDERER_INTERFACE)

    def get_position(self):
        return self.renderer.get_position()

    def set_position(self, position):
        self.renderer.set_position(0, position)
        self._start_position = position
        self._start_time = time.time()
        return False

    def get_status(self):
        """Returns playing status and updates filename"""
        playlist, index, state, object_id = self.renderer.get_status()
        return (state, object_id)

    def on_media_changed(self, position, object_id):
        # We don't know the duration for newly-loaded files at first
        self._duration = 0

        if self._is_playing:
            # Fake stop-of-old / start-of-new
            self.on_state_changed(-1) # (see below where we catch the "-1")
            self._filename = self.object_id_to_filename(object_id)
            self.on_state_changed(self.MafwPlayState.Playing)
        else:
            self._filename = self.object_id_to_filename(object_id)

        self._resume_handler.on_media_changed(self._filename)

    def on_state_changed(self, state):
        if state == self.MafwPlayState.Playing:
            self._is_playing = True
            try:
                self._start_position = self.get_position()
            except:
                # XXX: WTF?
                pass
            self._start_time = time.time()
            self._player.PlaybackStarted(self._start_position, self._filename.decode('utf-8'))
        else:
            if self._is_playing:
                try:
                    # Lame: if state is -1 (a faked "stop" event), don't try to
                    # get the "current" position, but use the wall time method
                    # from below to calculate the stop time
                    assert state != -1

                    position = self.get_position()
                except:
                    # Happens if the assertion fails or if the position cannot
                    # be determined for whatever reason. Use wall time and
                    # assume that the media file has advanced the same amount.
                    position = self._start_position + (time.time()-self._start_time)
                if self._start_position != position:
                    self._player.PlaybackStopped(self._start_position, \
                            position, self._duration, self._filename.decode('utf-8'))
                self._is_playing = False

        self._resume_handler.on_state_changed(state)

    def on_metadata_changed(self, key, count, value):
        if key == 'duration':
            # Remember the duration of the media - right now, we don't care
            # if this is for the right file, as we re-set the internally-saved
            # duration when the media is changed (see on_media_changed above)
            self._duration = int(value)
        elif key == 'is-seekable':
            self._resume_handler.on_metadata_changed(key, value)
