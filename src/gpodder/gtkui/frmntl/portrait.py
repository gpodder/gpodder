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

class FremantleRotation(object):
    """thp's screen rotation for Maemo 5

    Simply instantiate an object of this class and let it auto-rotate
    your StackableWindows depending on the device orientation.

    If you need to relayout a window, connect to its "configure-event"
    signal and measure the ratio of width/height and relayout for that.

    You can set the mode for rotation to AUTOMATIC (default), NEVER or
    ALWAYS with the set_mode() method.
    """
    AUTOMATIC, NEVER, ALWAYS = range(3)

    # Privately-used constants
    _PORTRAIT, _LANDSCAPE = ('portrait', 'landscape')

    def __init__(self, main_window=None):
        self._orientation = None
        self._main_window = main_window
        self._stack = hildon.WindowStack.get_default()
        self._mode = self.AUTOMATIC
        self._last_dbus_orientation = None
        system_bus = dbus.Bus.get_system()
        system_bus.add_signal_receiver(self._on_orientation_signal, \
                signal_name='sig_device_orientation_ind', \
                dbus_interface='com.nokia.mce.signal', \
                path='/com/nokia/mce/signal')

    def get_mode(self):
        """Get the currently-set rotation mode

        This will return one of three values: AUTOMATIC, ALWAYS or NEVER.
        """
        return self._mode

    def set_mode(self, new_mode):
        """Set the rotation mode

        You can set the rotation mode to AUTOMATIC (use hardware rotation
        info), ALWAYS (force portrait) and NEVER (force landscape).
        """
        if new_mode not in (self.AUTOMATIC, self.ALWAYS, self.NEVER):
            raise ValueError('Unknown rotation mode')

        if self._mode != new_mode:
            if self._mode == self.AUTOMATIC:
                # Remember the current "automatic" orientation for later
                self._last_dbus_orientation = self._orientation
                if new_mode == self.NEVER:
                    self._orientation_changed(self._LANDSCAPE)
                elif new_mode == self.ALWAYS:
                    self._orientation_changed(self._PORTRAIT)
            elif new_mode == self.AUTOMATIC:
                # Restore the last-known "automatic" orientation
                self._orientation_changed(self._last_dbus_orientation)

            self._mode = new_mode

    def _get_main_window(self):
        if self._main_window:
            # If we have gotten the main window as parameter, return it and
            # don't try "harder" to find another window using the stack
            return self._main_window
        else:
            # The main window is at the "bottom" of the window stack, and as
            # the list we get with get_windows() is sorted "topmost first", we
            # simply take the last item of the list to get our main window
            windows = self._stack.get_windows()
            if windows:
                return windows[-1]
            else:
                return None

    def _orientation_changed(self, orientation):
        if self._orientation == orientation:
            # Ignore repeated requests
            return

        flags = hildon.PORTRAIT_MODE_SUPPORT
        if orientation == self._PORTRAIT:
            flags |= hildon.PORTRAIT_MODE_REQUEST

        window = self._get_main_window()
        if window is not None:
            hildon.hildon_gtk_window_set_portrait_flags(window, flags)

        self._orientation = orientation

    def _on_orientation_signal(self, orientation, stand, face, x, y, z):
        if orientation in (self._PORTRAIT, self._LANDSCAPE):
            if self._mode == self.AUTOMATIC:
                # Automatically set the rotation based on hardware orientation
                self._orientation_changed(orientation)
            else:
                # Ignore orientation changes for non-automatic modes, but save
                # the current orientation for "automatic" mode later on
                self._last_dbus_orientation = orientation

