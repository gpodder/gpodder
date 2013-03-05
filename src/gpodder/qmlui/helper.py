# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2013 Thomas Perl and the gPodder Team
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

import gpodder

import os

from gpodder import util

from PySide import QtCore

import logging
logger = logging.getLogger(__name__)

class Action(QtCore.QObject):
    def __init__(self, caption, action, target=None):
        QtCore.QObject.__init__(self)
        self._caption = util.convert_bytes(caption)

        self.action = action
        self.target = target

    changed = QtCore.Signal()

    def _get_caption(self):
        return self._caption

    caption = QtCore.Property(unicode, _get_caption, notify=changed)


class MediaButtonsHandler(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)

        if gpodder.ui.harmattan:
            headset_path = '/org/freedesktop/Hal/devices/computer_logicaldev_input_0'
            headset_path2 = '/org/freedesktop/Hal/devices/computer_logicaldev_input'
        else:
            return

        import dbus
        system_bus = dbus.SystemBus()
        system_bus.add_signal_receiver(self.handle_button, 'Condition',
                'org.freedesktop.Hal.Device', None, headset_path)
        if gpodder.ui.harmattan:
            system_bus.add_signal_receiver(self.handle_button, 'Condition',
                    'org.freedesktop.Hal.Device', None, headset_path2)

    def handle_button(self, signal, button):
        if signal == 'ButtonPressed':
            if button in ('play-cd', 'phone'):
                self.playPressed.emit()
            elif button == 'pause-cd':
                self.pausePressed.emit()
            elif button == 'previous-song':
                self.previousPressed.emit()
            elif button == 'next-song':
                self.nextPressed.emit()

    playPressed = QtCore.Signal()
    pausePressed = QtCore.Signal()
    previousPressed = QtCore.Signal()
    nextPressed = QtCore.Signal()

class TrackerMinerConfig(QtCore.QObject):
    FILENAME = os.path.expanduser('~/.config/tracker/tracker-miner-fs.cfg')
    SECTION = 'IgnoredDirectories'
    ENTRY = '$HOME/MyDocs/gPodder/'

    def __init__(self, filename=None):
        QtCore.QObject.__init__(self)
        self._filename = filename or TrackerMinerConfig.FILENAME
        self._index_podcasts = self.get_index_podcasts()

    @QtCore.Slot(result=bool)
    def get_index_podcasts(self):
        """
        Returns True if the gPodder directory is indexed, False otherwise
        """
        if not os.path.exists(self._filename):
            logger.warn('File does not exist: %s', self._filename)
            return False

        for line in open(self._filename, 'r'):
            if line.startswith(TrackerMinerConfig.SECTION + '='):
                return (TrackerMinerConfig.ENTRY not in line)

    @QtCore.Slot(bool, result=bool)
    def set_index_podcasts(self, index_podcasts):
        """
        If index_podcasts is True, make sure the gPodder directory is indexed
        If index_podcasts is False, ignore the gPodder directory in Tracker
        """
        if not os.path.exists(self._filename):
            logger.warn('File does not exist: %s', self._filename)
            return False

        if self._index_podcasts == index_podcasts:
            # Nothing to do
            return True

        tmp_filename = self._filename + '.gpodder.tmp'

        out = open(tmp_filename, 'w')
        for line in open(self._filename, 'r'):
            if line.startswith(TrackerMinerConfig.SECTION + '='):
                _, rest = line.rstrip('\n').split('=', 1)
                directories = filter(None, rest.split(';'))

                if index_podcasts:
                    if TrackerMinerConfig.ENTRY in directories:
                        directories.remove(TrackerMinerConfig.ENTRY)
                else:
                    if TrackerMinerConfig.ENTRY not in directories:
                        directories.append(TrackerMinerConfig.ENTRY)

                line = '%(section)s=%(value)s;\n' % {
                    'section': TrackerMinerConfig.SECTION,
                    'value': ';'.join(directories),
                }
                logger.info('Writing new config line: %s', line)

            out.write(line)
        out.close()

        os.rename(tmp_filename, self._filename)
        self._index_podcasts = index_podcasts
        return True

