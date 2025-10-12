# -*- coding: utf-8 -*-
#
# gPodder extension for listening to notifications from MPRIS-capable
# players and translating them to gPodder's Media Player D-Bus API
#
# Copyright (c) 2013-2014 Dov Feldstern <dovdevel@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import collections
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

import gpodder
from gpodder import registry
from gpodder.player import PlayerInterface

import gi  # isort:skip
gi.require_version('Gio', '2.0')
gi.require_version('GLib', '2.0')
from gi.repository import Gio, GLib  # isort:skip

logger = logging.getLogger(__name__)
_ = gpodder.gettext

__title__ = _('MPRIS Listener')
__description__ = _('Convert MPRIS notifications to gPodder Media Player D-Bus API')
__authors__ = 'Dov Feldstern <dovdevel@gmail.com>'
__doc__ = 'https://gpodder.github.io/docs/extensions/mprislistener.html'
__category__ = 'desktop-integration'
__only_for__ = 'freedesktop'

USECS_IN_SEC = 1000000

TrackInfo = collections.namedtuple('TrackInfo',
                        ['uri', 'length', 'status', 'pos', 'rate', 'player_id', 'track_id'])


def subsecond_difference(usec1, usec2):
    return usec1 is not None and usec2 is not None and abs(usec1 - usec2) < USECS_IN_SEC


class CurrentTrackTracker(object):
    """An instance of this class tracks the state of the currently playing track.

    Playback status, playing position, etc.
    of a single MPRIS-enabled player (an running instance of vlc, ...).
    player_id is the identity of the MPRIS-enable player on d-bus.
    """

    def __init__(self, notifier, player_id):
        self.uri = None
        self.length = None
        self.pos = None
        self.rate = None
        self.status = None
        self.player_id = player_id
        self._notifier = notifier
        self._prev_notif = ()
        self._start_position = 0
        self.track_id = None

    def _calc_update(self):

        now = time.time()

        logger.debug('CurrentTrackTracker: calculating at %d (status: %r)',
                     now, self.status)

        try:
            if self.status != 'Playing':
                logger.debug('CurrentTrackTracker: not currently playing, no change')
                return
            if self.pos is None or self.rate is None:
                logger.debug('CurrentTrackTracker: unknown pos/rate, no change')
                return
            logger.debug('CurrentTrackTracker: %f @%f (diff: %f)',
                         self.pos, self.rate, now - self._last_time)
            self.pos = self.pos + self.rate * (now - self._last_time) * USECS_IN_SEC
        finally:
            self._last_time = now

    def update_needed(self, current, updated):
        for field in updated:
            if field == 'pos':
                if not subsecond_difference(updated['pos'], current['pos']):
                    return True
            elif updated[field] != current[field]:
                return True
        # no unequal field was found, no new info here!
        return False

    def update(self, **kwargs):
        """Call this from MPRISDBusReceiver on events."""
        player_id = kwargs.pop('player_id', self.player_id)
        if self.player_id != player_id:
            raise Exception("CurrentTrackTracker[%s] received update for %s" % (self.player_id, player_id))

        # check if there is any new info here -- if not, no need to update!

        cur = self.getinfo()._asdict()
        if not self.update_needed(cur, kwargs):
            return

        # there *is* new info, go ahead and update...
        uri = kwargs.pop('uri', None)
        if uri is not None:
            length = kwargs.pop('length')  # don't know how to handle uri with no length
            if uri != cur['uri']:
                # if this is a new uri, and the previous state was 'Playing',
                # notify that the previous track has stopped before updating to
                # the new track.
                if cur['status'] == 'Playing':
                    logger.debug('notify Stopped: new uri: old %s new %s',
                                 cur['uri'], uri)
                    self.notify_stop()
            self.uri = uri
            self.length = float(length)

        track_id = kwargs.pop('track_id', None)
        if track_id is not None:
            self.track_id = track_id

        if 'pos' in kwargs:
            newpos = kwargs.pop('pos')
            # If the position is being updated, and the current status was Playing
            # If the status *is* playing, and *was* playing, but the position
            # has changed discontinuously, notify a stop for the old position
            if (cur['status'] == 'Playing'
                    and ('status' not in kwargs or kwargs['status'] == 'Playing') and not
                    subsecond_difference(cur['pos'], newpos)):
                logger.debug('notify Stopped: playback discontinuity:'
                             + 'calc: %r observed: %r', cur['pos'], newpos)
                self.notify_stop()

            if (newpos <= 0
                    and self.pos is not None
                    and self.length is not None
                    and (self.length - USECS_IN_SEC) < self.pos
                    and self.pos < (self.length + 2 * USECS_IN_SEC)):
                logger.debug('pos=0 end of stream (calculated pos: %f/%f [%f])',
                             self.pos / USECS_IN_SEC, self.length / USECS_IN_SEC,
                             (self.pos / USECS_IN_SEC) - (self.length / USECS_IN_SEC))
                self.pos = self.length
            elif self.pos is not None and self.length is not None:
                logger.debug("%r %r", self.pos, self.length)
                logger.debug('pos!=0 not end of stream (calculated pos: %f/%f [%f])',
                             self.pos / USECS_IN_SEC, self.length / USECS_IN_SEC,
                             (self.pos / USECS_IN_SEC) - (self.length / USECS_IN_SEC))
            self.pos = newpos if newpos >= 0 else 0

        if 'status' in kwargs:
            self.status = kwargs.pop('status')

        if 'rate' in kwargs:
            self.rate = kwargs.pop('rate')

        if kwargs:
            logger.error('unexpected update fields %r', kwargs)

        # notify about the current state
        if self.status == 'Playing':
            self.notify_playing()
        else:
            logger.debug('notify Stopped: status %r', self.status)
            self.notify_stop()

    def getinfo(self):
        self._calc_update()
        return TrackInfo(
            self.uri, self.length, self.status, self.pos, self.rate,
            self.player_id, self.track_id)

    def notify_stop(self):
        self.notify('Stopped')

    def notify_playing(self):
        self.notify('Playing')

    def notify(self, status):
        if (self.uri is None
                or self.pos is None
                or self.status is None
                or self.length is None
                or self.length <= 0):
            logger.debug("Skip notify %r %r %r %r",
                self.uri, self.pos, self.status, self.length)
            return
        pos_seconds = self.pos // USECS_IN_SEC
        parsed_url = urllib.parse.urlparse(self.uri)
        if (not parsed_url.scheme) or parsed_url.scheme == 'file':
            file_uri = urllib.request.url2pathname(urllib.parse.urlparse(self.uri).path)
        else:
            file_uri = self.uri
        total_time = self.length // USECS_IN_SEC
        logger.debug("MPRISDBusReceiver.notify %s/%s %i%% %s", pos_seconds, total_time, int(100 * pos_seconds / total_time), status)

        if status == 'Stopped':
            end_position = pos_seconds
            start_position = self._start_position
            if self._prev_notif != (start_position, end_position, total_time, file_uri):
                self._notifier._on_playback_stopped(start_position, end_position,
                                               total_time, file_uri)
                self._prev_notif = (start_position, end_position, total_time, file_uri)

        elif status == 'Playing':
            start_position = pos_seconds
            if self._prev_notif != (start_position, total_time, file_uri):
                self._notifier._on_playback_started(start_position, total_time, file_uri)
                self._prev_notif = (start_position, total_time, file_uri)
            self._start_position = start_position

    def on_player_exited(self):
        """Call this method from MPRISDBusReceiver on player exited message."""
        if self.uri:
            self._notifier._on_player_exited(self.uri)

    def __repr__(self):
        return '[%s] %s: %s at %d/%d (@%f)' % (
            self.player_id or 'No Id',
            self.uri or 'None',
            self.status or 'None',
            (self.pos or 0) // USECS_IN_SEC,
            (self.length or 0) // USECS_IN_SEC,
            self.rate or 0)


class MPRISDBusReceiver(PlayerInterface):
    """This class listens to d-bus events from any MPRIS-enabled player."""

    INTERFACE_PROPS = 'org.freedesktop.DBus.Properties'
    SIGNAL_PROP_CHANGE = 'PropertiesChanged'
    PATH_MPRIS = '/org/mpris/MediaPlayer2'
    INTERFACE_MPRIS = 'org.mpris.MediaPlayer2.Player'
    SIGNAL_SEEKED = 'Seeked'
    OTHER_MPRIS_INTERFACES = ['org.mpris.MediaPlayer2',
                              'org.mpris.MediaPlayer2.TrackList',
                              'org.mpris.MediaPlayer2.Playlists']
    INTERFACE_DBUS = 'org.freedesktop.DBus'
    SIGNAL_NAME_OWNER_CHANGED = 'NameOwnerChanged'

    def __init__(self, bus, model):
        super().__init__(model)
        self.bus = bus
        self.current_trackers = {}  # one per player dbus id
        self.prop_change_listener_id = self.bus.signal_subscribe(
            None,
            self.INTERFACE_PROPS,
            self.SIGNAL_PROP_CHANGE,
            self.PATH_MPRIS,
            None, Gio.DBusSignalFlags.NONE,
            self.on_prop_change, None)
        self.seeked_listener_id = self.bus.signal_subscribe(
            None,
            self.INTERFACE_MPRIS,
            self.SIGNAL_SEEKED,
            self.PATH_MPRIS,
            None, Gio.DBusSignalFlags.NONE,
            self.on_seeked, None)
        self.name_listener_id = self.bus.signal_subscribe(
            None,
            self.INTERFACE_DBUS,
            self.SIGNAL_NAME_OWNER_CHANGED,
            None,
            None, Gio.DBusSignalFlags.NONE,
            self.on_name_owner_changed, None)

    def stop_receiving(self):
        self.bus.signal_unsubscribe(self.prop_change_listener_id)
        self.bus.signal_unsubscribe(self.seeked_listener_id)
        self.bus.signal_unsubscribe(self.name_listener_id)

    def on_prop_change(self, connection, sender, path, interface, signal, props, user_data):
        interface_name, changed_properties, _unused = props.unpack() if props else ("", {}, [])
        if interface_name != self.INTERFACE_MPRIS:
            if interface_name not in self.OTHER_MPRIS_INTERFACES:
                logger.warning('unexpected interface: %s, props=%r', interface_name, list(changed_properties.keys()))
            return
        if sender is None:
            logger.warning('No sender associated to D-Bus signal, please report a bug')
            return

        collected_info = {"player_id": sender}
        logger.debug("on_prop_change from %s %s", sender, ", ".join(changed_properties.keys()))
        if 'PlaybackStatus' in changed_properties:
            collected_info['status'] = changed_properties['PlaybackStatus']
        if 'Metadata' in changed_properties:
            logger.debug("Metadata %s", ", ".join(changed_properties['Metadata'].keys()))
            # on stop there is no xesam:url
            if 'xesam:url' in changed_properties['Metadata']:
                collected_info['uri'] = changed_properties['Metadata']['xesam:url']
                collected_info['length'] = changed_properties['Metadata'].get('mpris:length', 0.0)
            if 'mpris:trackid' in changed_properties['Metadata']:
                collected_info['track_id'] = changed_properties['Metadata']['mpris:trackid']
        if 'Rate' in changed_properties:
            collected_info['rate'] = changed_properties['Rate']
        # Collect extra info if not provided:
        if changed_properties.get('PlaybackStatus') != 'Stopped':
            # Fix #788 pos=0 when Stopped resulting in not saving position on VLC quit
            try:
                collected_info['pos'] = self.query_property(sender, 'Position')
            except GLib.Error:
                pass
        if 'status' not in collected_info:
            try:
                collected_info['status'] = self.query_property(
                    sender, 'PlaybackStatus')
            except GLib.Error:
                pass
        # DeaDBeeF doesn't emit rate, grab it
        if 'rate' not in collected_info and collected_info['status'] != 'Stopped':
            try:
                collected_info['rate'] = self.query_property(
                    sender, 'Rate')
            except GLib.Error:
                pass
        # TODO: re-emit CanPause, CanSeek for the UI

        logger.debug('collected info: %r', collected_info)
        self._update_tracker(sender, **collected_info)

    def _update_tracker(self, sender, **collected_info):
        cur = self.current_trackers.get(sender)
        if not cur:
            logger.debug("tracking new player %r", sender)
            cur = CurrentTrackTracker(self, sender)
            self.current_trackers[sender] = cur
        cur.update(**collected_info)

    def on_seeked(self, connection, sender, path, interface, signal, params_variant, user_data):
        if sender is None:
            logger.warning('No sender associated to %s D-Bus signal, please report a bug', self.SIGNAL_SEEKED)
            return
        if params_variant is not None:
            position = params_variant.unpack()[0]
            logger.debug('%s seeked to pos: %f', sender, position)
            self._update_tracker(sender, pos=position)

    def query_property(self, sender, prop):
        variant = self.bus.call_sync(
            sender, self.PATH_MPRIS, self.INTERFACE_PROPS,
            'Get', GLib.Variant('(ss)', (self.INTERFACE_MPRIS, prop)),
            None, Gio.DBusCallFlags.NONE, -1, None)
        return variant.unpack()[0]

    def on_name_owner_changed(self, connection, sender, path, interface, signal, params_variant, user_data):
        # we don't care about the new name owner at the moment.
        # We might receive events from it later and then register it in self.current_trackers.
        _name, old_owner, _new_owner = params_variant.unpack()
        if old_owner in self.current_trackers:
            self.current_trackers[old_owner].on_player_exited()
            del self.current_trackers[old_owner]

    def seek(self, file_uri, position):
        logger.info('Seek: %s: %d', file_uri, position)
        target_tracker = None
        for player_id, tracker in self.current_trackers.items():
            if tracker.uri == file_uri:
                if tracker.status == 'Playing' or tracker.status == 'Paused':
                    target_tracker = tracker
                    break
        if target_tracker:
            pos_us = int(position * USECS_IN_SEC)
            variant = self.bus.call_sync(
                target_tracker.player_id, self.PATH_MPRIS, self.INTERFACE_MPRIS,
                'SetPosition', GLib.Variant('(si)', (target_tracker.track_id, pos_us)),
                None, Gio.DBusCallFlags.NONE, -1, None)
            logger.debug("Called player.SetPosition(%s, %s, %s, %d) => %r",
                target_tracker.player_id, file_uri, target_tracker.track_id, pos_us, variant)


# Finally, this is the extension, which just pulls this all together
class gPodderExtension:

    def __init__(self, container):
        self.container = container
        self.rcvr = None

    def on_ui_initialized(self, model, update_podcast_callback,
            download_episode_callback):
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        if bus is None:
            logger.debug("dbus session bus not available, not loading")
            return

        self.rcvr = MPRISDBusReceiver(bus, model)
        registry.player_interface.register(self.get_rcvr)

    def get_rcvr(self, _item):
        return self.rcvr

    def on_unload(self):
        if self.rcvr is not None:
            self.rcvr.stop_receiving()
            registry.player_interface.unregister(self.get_rcvr)
