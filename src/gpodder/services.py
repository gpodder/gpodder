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


#
#  services.py -- Core Services for gPodder
#  Thomas Perl <thp@perli.net>   2007-08-24
#
#

import gpodder
from gpodder.liblogger import log

from gpodder import util

_ = gpodder.gettext

class ObservableService(object):
    def __init__(self, signal_names=[]):
        self.observers = {}
        for signal in signal_names:
            self.observers[signal] = []

    def register(self, signal_name, observer):
        if signal_name in self.observers:
            if not observer in self.observers[signal_name]:
                self.observers[signal_name].append(observer)
            else:
                log('Observer already added to signal "%s".', signal_name, sender=self)
        else:
            log('Signal "%s" is not available for registration.', signal_name, sender=self)

    def unregister(self, signal_name, observer):
        if signal_name in self.observers:
            if observer in self.observers[signal_name]:
                self.observers[signal_name].remove(observer)
            else:
                log('Observer could not be removed from signal "%s".', signal_name, sender=self)
        else:
            log('Signal "%s" is not available for un-registration.', signal_name, sender=self)

    def notify(self, signal_name, *args):
        if signal_name in self.observers:
            for observer in self.observers[signal_name]:
                util.idle_add(observer, *args)
        else:
            log('Signal "%s" is not available for notification.', signal_name, sender=self)


class DependencyManager(object):
    def __init__(self):
        self.dependencies = []

    def depend_on(self, feature_name, description, modules, tools):
        self.dependencies.append([feature_name, description, modules, tools])

    def modules_available(self, modules):
        """
        Receives a list of modules and checks if each
        of them is available. Returns a tuple with the
        first item being a boolean variable that is True
        when all required modules are available and False
        otherwise. The second item is a dictionary that
        lists every module as key with the available as
        boolean value.
        """
        result = {}
        all_available = True
        for module in modules:
            try:
                __import__(module)
                result[module] = True
            except:
                result[module] = False
                all_available = False

        return (all_available, result)

    def tools_available(self, tools):
        """
        See modules_available.
        """
        result = {}
        all_available = True
        for tool in tools:
            if util.find_command(tool):
                result[tool] = True
            else:
                result[tool] = False
                all_available = False

        return (all_available, result)


dependency_manager = DependencyManager()


# Register non-module-specific dependencies here
dependency_manager.depend_on(_('Bluetooth file transfer'), _('Send podcast episodes to Bluetooth devices. Needs the bluetooth-sendto command from gnome-bluetooth.'), [], ['bluetooth-sendto'])
dependency_manager.depend_on(_('HTML episode shownotes'), _('Display episode shownotes in HTML format using WebKit.'), ['webkit'], [])

