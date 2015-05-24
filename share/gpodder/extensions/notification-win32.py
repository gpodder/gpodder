# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2015 Thomas Perl and the gPodder Team
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

# Notification implementation for Windows
# Sean Munkel; 2012-12-29

__title__ = 'Notification Bubbles for Windows'
__description__ = 'Display notification bubbles for different events.'
__authors__ = 'Sean Munkel <SeanMunkel@gmail.com>'
__category__ = 'desktop-integration'
__mandatory_in__ = 'win32'
__only_for__ = 'win32'

import functools
import os
import os.path
import gpodder
import pywintypes
import win32gui

import logging

logger = logging.getLogger(__name__)

IDI_APPLICATION = 32512
WM_TASKBARCREATED = win32gui.RegisterWindowMessage('TaskbarCreated')
WM_TRAYMESSAGE = 1044

# based on http://code.activestate.com/recipes/334779/
class NotifyIcon(object):
    def __init__(self, hwnd):
        self._hwnd = hwnd
        self._id = 0
        self._flags = win32gui.NIF_MESSAGE | win32gui.NIF_ICON
        self._callbackmessage = WM_TRAYMESSAGE
        path = os.path.join(os.path.dirname(__file__), '..', '..',
                'icons', 'hicolor', '16x16', 'apps', 'gpodder.ico')
        icon_path = os.path.abspath(path)

        try:
            self._hicon = win32gui.LoadImage(None, icon_path, 1, 0, 0, 0x50)
        except pywintypes.error as e:
            logger.warn("Couldn't load gpodder icon for tray")
            self._hicon = win32gui.LoadIcon(0, IDI_APPLICATION)

        self._tip = ''
        self._info = ''
        self._timeout = 0
        self._infotitle = ''
        self._infoflags = win32gui.NIIF_NONE
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, self.notify_config_data)

    @property
    def notify_config_data(self):
        """ Function to retrieve the NOTIFYICONDATA Structure. """
        return (self._hwnd, self._id, self._flags, self._callbackmessage,
                self._hicon, self._tip, self._info, self._timeout,
                self._infotitle, self._infoflags)

    def remove(self):
        """ Removes the tray icon. """
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE,
                self.notify_config_data)

    def set_tooltip(self, tooltip):
        """ Sets the tray icon tooltip. """
        self._flags = self._flags | win32gui.NIF_TIP
        self._tip = tooltip.encode("mbcs")
        win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY,
                self.notify_config_data)

    def show_balloon(self, title, text, timeout=10,
            icon=win32gui.NIIF_NONE):
        """ Shows a balloon tooltip from the tray icon. """
        self._flags = self._flags | win32gui.NIF_INFO
        self._infotitle = title.encode("mbcs")
        self._info = text.encode("mbcs")
        self._timeout = timeout * 1000
        self._infoflags = icon
        win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY,
                self.notify_config_data)


class gPodderExtension(object):
    def __init__(self, *args):
        self.notifier = None

    def on_ui_object_available(self, name, ui_object):
        def callback(self, window, *args):
            self.notifier = NotifyIcon(window.window.handle)

        if name == 'gpodder-gtk':
            ui_object.main_window.connect('realize',
                    functools.partial(callback, self))

    def on_notification_show(self, title, message):
        if self.notifier is not None:
            self.notifier.show_balloon(title, message)

    def on_unload(self):
        if self.notifier is not None:
            self.notifier.remove()

