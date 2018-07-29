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
__category__ = 'desktop-integration'
__only_for__ = 'gtk'
__mandatory_in__ = 'gtk'
__disable_in__ = 'win32'

import logging

import gpodder

logger = logging.getLogger(__name__)

try:
    import gi
    gi.require_version('Notify', '0.7')
    from gi.repository import Notify
    pynotify = True
except ImportError:
    pynotify = None
except ValueError:
    pynotify = None


if pynotify is None:
    class gPodderExtension(object):
        def __init__(self, container):
            logger.info('Could not find PyNotify.')
else:
    class gPodderExtension(object):
        def __init__(self, container):
            self.container = container

        def on_load(self):
            Notify.init('gPodder')

        def on_unload(self):
            Notify.uninit()

        def on_notification_show(self, title, message):
            if not message and not title:
                return

            notify = Notify.Notification.new(title or '', message or '',
                    gpodder.icon_file)

            try:
                notify.show()
            except:
                # See http://gpodder.org/bug/966
                pass
