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


# gpodder.gtkui.frmntl.network - Network connection manager
# Thomas Perl <thp@gpodder.org>; 2011-02-19


import dbus
import conic


class NetworkManager(object):
    ICD_NAME = 'com.nokia.icd'
    ICD_PATH = '/com/nokia/icd'
    ICD_INTF = 'com.nokia.icd'

    def __init__(self):
        self.system_bus = dbus.Bus.get_system()
        self.icd_obj = self.system_bus.get_object(self.ICD_NAME, \
                self.ICD_PATH)
        self.icd = dbus.Interface(self.icd_obj, self.ICD_INTF)
        self.conic = conic.Connection()

    def get_current_iap(self):
        try:
            iap_id, _, _, _, _, _, _ = self.icd.get_statistics()
        except Exception, e:
            return None
        return self.conic.get_iap(iap_id)

    def get_bearer_type(self):
        iap = self.get_current_iap()
        if iap is None:
            return None
        return iap.get_bearer_type()

    def connection_is_wlan(self):
        return self.get_bearer_type() in (conic.BEARER_WLAN_INFRA, \
                conic.BEARER_WLAN_ADHOC)

