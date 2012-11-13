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

# Bernd Schlapsi <brot@gmx.info>; 2011-11-20

__title__ = 'Gtk+ Desktop Notifications'
__description__ = 'Display notification bubbles for different events.'
__only_for__ = 'gtk'

import gpodder
from functools import partial
import logging
logger = logging.getLogger(__name__)

try:
    import pynotify
except ImportError:
    pynotify = None
    try:
        import win32gui
    except ImportError:
        win32gui = None


if pynotify is not None:
    class gPodderExtension(object):
        def __init__(self, container):
            self.container = container

        def on_load(self):
            pynotify.init('gPodder')

        def on_unload(self):
            pynotify.uninit()

        def on_notification_show(self, title, message):
            if not message and not title:
                return

            notify = pynotify.Notification(title or '', message or '',
                    gpodder.icon_file)

            try:
                notify.show()
            except:
                # See http://gpodder.org/bug/966
                pass
elif pynotify is None and win32gui is not None:
    import os
    import pywintypes

    IDI_APPLICATION = 32512
    WM_TASKBARCREATED = win32gui.RegisterWindowMessage('TaskbarCreated')
    WM_TRAYMESSAGE = 1044

    #based on http://code.activestate.com/recipes/334779/
    class NotifyIcon(object):
        def __init__(self, hwnd):
            self._hwnd = hwnd
            self._id = 0
            self._flags = win32gui.NIF_MESSAGE | win32gui.NIF_ICON
            self._callbackmessage = WM_TRAYMESSAGE
            icon_path = os.path.abspath(r'share\gpodder\images\gpodder.ico')
            print(icon_path)
            try:
                self._hicon = win32gui.LoadImage(None, icon_path, 1, 0, 0, 0x50)
            except pywintypes.error as e:
                logger.warn("Couldn't load gpodder icon for tray")
                self._hicon = win32gui.LoadIcon(0, IDI_APPLICATION)
            print self._hicon
            self._tip = ''
            self._info = ''
            self._timeout = 0
            self._infotitle = ''
            self._infoflags = win32gui.NIIF_NONE
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, self.notify_config_data)
            
            
        @property
        def notify_config_data(self):
            """ Function to retrieve the NOTIFYICONDATA Structure. """
            return  (self._hwnd, self._id, self._flags, self._callbackmessage,
                     self._hicon, self._tip, self._info, self._timeout,
                     self._infotitle, self._infoflags)

    
        def remove(self):
            """ Removes the tray icon. """
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, 
                                      self.notify_config_data)


        def set_tooltip(self, tooltip):
            """ Sets the tray icon tooltip. """
            self._flags = self._flags | win32gui.NIF_TIP
            self._tip = tooltip
            win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, 
                                      self.notify_config_data)
        
        
        def show_balloon(self, title, text, timeout=10, 
                         icon=win32gui.NIIF_NONE):
            """ Shows a balloon tooltip from the tray icon. """
            self._flags = self._flags | win32gui.NIF_INFO
            self._infotitle = title
            self._info = text
            self._timeout = timeout * 1000
            self._infoflags = icon
            win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY,
                                      self.notify_config_data)

    
    class gPodderExtension(object):
        def __init__(self, *args):
            self.notifier = None

        def on_ui_object_available(self, name, ui_object):
            def callback(self, window, *args):
                print window.get_icon()
                self.notifier = NotifyIcon(window.window.handle)

            if name == 'gpodder-gtk':
                ui_object.main_window.connect('realize', 
                                              partial(callback, self))

        def on_notification_show(self, title, message):
            if self.notifier is not None:
                self.notifier.show_balloon(title, message)

        def on_unload(self):
            if self.notifier is not None:
                self.notifier.remove()
            
else:
    class gPodderExtension(object):
        def __init__(self, container):
            logger.info('Could not find PyNotify.')

