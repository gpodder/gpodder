# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
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

import dbus
import dbus.glib

import hildon

class FremantleAutoRotation(object):
    """thp's automatic screen rotation for Maemo 5

    Simply instantiate an object of this class and let it auto-rotate
    your StackableWindows depending on the device orientation.

    If you need to relayout a window, connect to its "configure-event"
    signal and measure the ratio of width/height and relayout for that.
    """
    def __init__(self):
        self._orientation = None
        self._stack = hildon.WindowStack.get_default()
        system_bus = dbus.Bus.get_system()
        system_bus.add_signal_receiver(self.on_orientation_signal, \
                signal_name='sig_device_orientation_ind', \
                dbus_interface='com.nokia.mce.signal', \
                path='/com/nokia/mce/signal')

    def orientation_changed(self, orientation):
        flags = hildon.PORTRAIT_MODE_SUPPORT
        if orientation == 'portrait':
            flags |= hildon.PORTRAIT_MODE_REQUEST
        for window in self._stack.get_windows():
            hildon.hildon_gtk_window_set_portrait_flags(window, flags)

    def on_orientation_signal(self, orientation, stand, face, x, y, z):
        if orientation in ('portrait', 'landscape'):
            if orientation != self._orientation:
                self.orientation_changed(orientation)
                self._orientation = orientation

