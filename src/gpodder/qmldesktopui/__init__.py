# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2012 Thomas Perl and the gPodder Team
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

# gpodder.qmldesktopui - gPodder's QML Desktop interface
# Thomas Perl <thp@gpodder.org>; 2011-02-06
# Mikołaj Milej <mikolajmm@gmail.com>; 2012-12-24

import logging
logger = logging.getLogger("qmldesktopui")

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

import gpodder
from gpodder import core

from gpodder.qmldesktopui.controller import qtPodder


def main(args):
    try:
        dbus_main_loop = DBusGMainLoop(set_as_default=True)
        gpodder.dbus_session_bus = dbus.SessionBus(dbus_main_loop)

        bus_name = dbus.service.BusName(gpodder.dbus_bus_name,
                bus=gpodder.dbus_session_bus)
    except dbus.exceptions.DBusException, dbe:
        logger.warn('Cannot get "on the bus".', exc_info=True)
        bus_name = None

    gui = qtPodder(args, core.Core(), bus_name)
    return gui.run()
