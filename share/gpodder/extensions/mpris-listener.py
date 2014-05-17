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
import dbus
import dbus.service
import gpodder
import logging
import time
import urllib
import urlparse

logger = logging.getLogger(__name__)
_ = gpodder.gettext

__title__ = _('MPRIS Listener')
__description__ = _('Convert MPRIS notifications to gPodder Media Player D-Bus API')
__authors__ = 'Dov Feldstern <dovdevel@gmail.com>'
__doc__ = 'http://wiki.gpodder.org/wiki/Extensions/MprisListener'
__category__ = 'desktop-integration'

USECS_IN_SEC = 1000000

TrackInfo = collections.namedtuple('TrackInfo',
                        ['uri', 'length', 'status', 'pos', 'rate'])

def subsecond_difference(usec1, usec2):
    return abs(usec1 - usec2) < USECS_IN_SEC
    
class CurrentTrackTracker(object):
    '''An instance of this class is responsible for tracking the state of the
    currently playing track -- it's playback status, playing position, etc.
    '''
    def __init__(self, notifier):
        self.uri = None
        self.length = None
        self.pos = None
        self.rate = None
        self.status = None
        self._notifier = notifier
        self._prev_notif = ()

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

        # check if there is any new info here -- if not, no need to update!

        cur = self.getinfo()._asdict()
        if not self.update_needed(cur, kwargs):
            return

        # there *is* new info, go ahead and update...

        uri = kwargs.pop('uri', None)
        if uri is not None:
            length = kwargs.pop('length') # don't know how to handle uri with no length
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

        if 'pos' in kwargs:
            # If the position is being updated, and the current status was Playing
            # If the status *is* playing, and *was* playing, but the position
            # has changed discontinuously, notify a stop for the old position
            if (    cur['status'] == 'Playing'
                and (not kwargs.has_key('status') or kwargs['status'] == 'Playing')
                and not subsecond_difference(cur['pos'], kwargs['pos'])
            ):
                logger.debug('notify Stopped: playback discontinuity:' + 
                              'calc: %f observed: %f', cur['pos'], kwargs['pos'])
                self.notify_stop()

            if (    (kwargs['pos']) == 0
                and self.pos > (self.length - USECS_IN_SEC)
                and self.pos < (self.length + 2 * USECS_IN_SEC)
            ):
                logger.debug('fixing for position 0 (calculated pos: %f/%f [%f])',
                             self.pos / USECS_IN_SEC, self.length / USECS_IN_SEC,
                             (self.pos/USECS_IN_SEC)-(self.length/USECS_IN_SEC))
                self.pos = self.length
                kwargs.pop('pos') # remove 'pos' even though we're not using it
            else:
                if self.pos is not None:
                    logger.debug("%r %r", self.pos, self.length)
                    logger.debug('not fixing for position 0 (calculated pos: %f/%f [%f])',
                                 self.pos / USECS_IN_SEC, self.length / USECS_IN_SEC,
                                 (self.pos/USECS_IN_SEC)-(self.length/USECS_IN_SEC))
                self.pos = kwargs.pop('pos')

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
            logger.debug('notify Stopped: status %s', self.status)
            self.notify_stop()

    def getinfo(self):
        self._calc_update()
        return TrackInfo(self.uri, self.length, self.status, self.pos, self.rate)

    def notify_stop(self):
        self.notify('Stopped')

    def notify_playing(self):
        self.notify('Playing')

    def notify(self, status):
        if (   self.uri is None
            or self.pos is None
            or self.status is None
            or self.length is None
            or self.length <= 0
        ):
            return
        pos = self.pos // USECS_IN_SEC
        file_uri = urllib.url2pathname(urlparse.urlparse(self.uri).path).encode('utf-8')
        total_time = self.length // USECS_IN_SEC
        
        if status == 'Stopped':
            end_position = pos
            start_position = self._notifier.start_position
            if self._prev_notif != (start_position, end_position, total_time, file_uri):
                self._notifier.PlaybackStopped(start_position, end_position,
                                               total_time, file_uri)
                self._prev_notif = (start_position, end_position, total_time, file_uri)

        elif status == 'Playing':
            start_position = pos
            if self._prev_notif != (start_position, file_uri):
                self._notifier.PlaybackStarted(start_position, file_uri)
                self._prev_notif = (start_position, file_uri)
            self._notifier.start_position = start_position

        logger.info('CurrentTrackTracker: %s: %r', status, self)

    def __repr__(self):
        return '%s: %s at %d/%d (@%f)' % (
            self.uri or 'None',
            self.status or 'None',
            (self.pos or 0) / USECS_IN_SEC,
            (self.length or 0) / USECS_IN_SEC,
            self.rate or 0)
            
class MPRISDBusReceiver(object):
    INTERFACE_PROPS = 'org.freedesktop.DBus.Properties'
    SIGNAL_PROP_CHANGE = 'PropertiesChanged'
    PATH_MPRIS = '/org/mpris/MediaPlayer2'
    INTERFACE_MPRIS = 'org.mpris.MediaPlayer2.Player'
    SIGNAL_SEEKED = 'Seeked'
    OBJECT_VLC = 'org.mpris.MediaPlayer2.vlc'

    def __init__(self, bus, notifier):
        self.bus = bus
        self.cur = CurrentTrackTracker(notifier)
        self.bus.add_signal_receiver(self.on_prop_change,
                                     self.SIGNAL_PROP_CHANGE,
                                     self.INTERFACE_PROPS,
                                     None,
                                     self.PATH_MPRIS)
        self.bus.add_signal_receiver(self.on_seeked,
                                     self.SIGNAL_SEEKED,
                                     self.INTERFACE_MPRIS,
                                     None,
                                     None)

    def stop_receiving(self):
        self.bus.remove_signal_receiver(self.on_prop_change,
                                        self.SIGNAL_PROP_CHANGE,
                                        self.INTERFACE_PROPS,
                                        None,
                                        self.PATH_MPRIS)
        self.bus.remove_signal_receiver(self.on_seeked,
                                        self.SIGNAL_SEEKED,
                                        self.INTERFACE_MPRIS,
                                        None,
                                        None)

    def on_prop_change(self, interface_name, changed_properties,
                       invalidated_properties, path=None):
        if interface_name != self.INTERFACE_MPRIS:
            logger.warn('unexpected interface: %s', interface_name)
            return
        
        collected_info = {}

        if changed_properties.has_key('PlaybackStatus'):
            collected_info['status'] = str(changed_properties['PlaybackStatus'])
        if changed_properties.has_key('Metadata'):
            collected_info['uri'] = changed_properties['Metadata']['xesam:url']
            collected_info['length'] = changed_properties['Metadata']['mpris:length']
        if changed_properties.has_key('Rate'):
            collected_info['rate'] = changed_properties['Rate']
        collected_info['pos'] = self.query_position()

        if not collected_info.has_key('status'):
            collected_info['status'] = str(self.query_status())
        logger.debug('collected info: %r', collected_info)

        self.cur.update(**collected_info)

    def on_seeked(self, position):
        logger.debug('seeked to pos: %f', position)
        self.cur.update(pos=position)

    def query_position(self):
        proxy = self.bus.get_object(self.OBJECT_VLC,self.PATH_MPRIS)
        props = dbus.Interface(proxy, self.INTERFACE_PROPS)
        return props.Get(self.INTERFACE_MPRIS, 'Position')

    def query_status(self):
        proxy = self.bus.get_object(self.OBJECT_VLC,self.PATH_MPRIS)
        props = dbus.Interface(proxy, self.INTERFACE_PROPS)
        return props.Get(self.INTERFACE_MPRIS, 'PlaybackStatus')

class gPodderNotifier(dbus.service.Object):
    def __init__(self, bus, path):
        dbus.service.Object.__init__(self, bus, path)

    @dbus.service.signal(dbus_interface='org.gpodder.player', signature='us')
    def PlaybackStarted(self, start_position, file_uri):
        logger.info('PlaybackStarted: %s: %d', file_uri, start_position)

    @dbus.service.signal(dbus_interface='org.gpodder.player', signature='uuus')
    def PlaybackStopped(self, start_position, end_position, total_time, file_uri):
        logger.info('PlaybackStopped: %s: %d--%d/%d',
            file_uri, start_position, end_position, total_time)
         
# Finally, this is the extension, which just pulls this all together
class gPodderExtension:

    def __init__(self, container):
        self.container = container
        self.path = '/org/gpodder/player/notifier'

    def on_load(self):
        self.session_bus = gpodder.dbus_session_bus
        self.notifier = gPodderNotifier(self.session_bus, self.path)
        self.rcvr = MPRISDBusReceiver(self.session_bus, self.notifier)

    def on_unload(self):
        self.notifier.remove_from_connection(self.session_bus, self.path)
        self.rcvr.stop_receiving()

