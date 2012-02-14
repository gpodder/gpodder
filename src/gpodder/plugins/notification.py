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

import gpodder
import platform

import logging
logger = logging.getLogger(__name__)


class NotifyInterface(object):
    def __init__(self):
        logger.info('Notifications are not implemented on your platform.')

    def on_notification_show(self, title, message):
        pass


class NotifyPyNotify(object):
    def __init__(self):
        import pynotify
        pynotify.init('gPodder')
        self.pynotify = pynotify
        logger.info('Notification plug-in loaded successfully.')

    def on_notification_show(self, title, message):
        if not self.pynotify.is_initted():
            return

        notify = self.pynotify.Notification(title, message, gpodder.icon_file)
        try:
            notify.show()
        except:
            # See http://gpodder.org/bug/966
            pass


system = platform.system()
if system == 'Linux':
    try:
        notify = NotifyPyNotify()
    except ImportError:
        # TODO: Notification class for harmattan?
        notify = NotifyInterface()

elif system == 'Windows':
    # TODO: Notification class for Windows (growl for windows?)
    notify = NotifyInterface()

elif system == 'Darwin':
    # TODO: Notification class for Mac (growl?)
    notify = NotifyInterface()

gpodder.user_extensions.register_extension(notify)
