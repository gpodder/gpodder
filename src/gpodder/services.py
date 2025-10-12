# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2018 The gPodder Team
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
import logging

import gpodder
from gpodder import util
from gpodder.registry import Resolver

logger = logging.getLogger(__name__)

_ = gpodder.gettext


class ObservableService(object):
    def __init__(self, signal_names=[]):
        self.observers = {}
        for signal in signal_names:
            self.observers[signal] = []

    def register(self, signal_name, observer):
        if signal_name in self.observers:
            if observer not in self.observers[signal_name]:
                self.observers[signal_name].append(observer)
                return True

        return False

    def unregister(self, signal_name, observer):
        if signal_name in self.observers:
            if observer in self.observers[signal_name]:
                self.observers[signal_name].remove(observer)
                return True

        return False

    def notify(self, signal_name, *args):
        if signal_name in self.observers:
            for observer in self.observers[signal_name]:
                util.idle_add(observer, *args)

            return True

        return False


class AutoRegisterObserver:
    """Utility class to observe a Resolver for implementations of the ObservableService.

    It will register listeners_by_signal into the ObservableService returned by the Resolver.resolve().
    It will unregister listeners_by_signal from the old ObservableService if it existed.
    You can inherit from AutoRegisterObserver or use it as as separate object.
    See registry.py for the Resolver.
    See player.py for an example, where MyGPOClientObserver wants to be notified of
    changes in PlayerInterface implementations. It observes the registry.player_interface Resolver
    for new implementation and (un)registers accordingly.
    """

    def __init__(self, resolver: Resolver, listeners_by_signal, *, label):
        """Instantiate and add self as observer to resolver.

        listeners_by_signal is a mapping of signal_name to callable, so
        that the AutoRegisterObserver can call `ObservableService.register(signal_name, callable)`
        for each of them.
        label is a str included in debug messages to identify the AutoRegisterObserver instance.
        """
        self._resolver = resolver
        self._listeners_by_signal = listeners_by_signal
        self._label = f"{label} "
        self._service = None
        self._resolver.add_observer(self._resolver_observer)
        self._resolver_observer()  # if an implementation of the service already exists in the resolver

    def _resolver_observer(self):
        # Internal method to be notified of PlayerInterface implementation changes
        service = self._resolver.resolve(None, None)
        if self._service is not None and service == self._service:
            logger.debug("%sStill using %s service impl = %r", self._label, self._resolver.name, self._service)
            return
        if self._service is not None and service != self._service:
            # unregister from old ObservableService instance
            for signal, listener in self._listeners_by_signal.items():
                if listener:
                    self._service.unregister(signal, listener)
        self._service = service
        if service:
            logger.debug("%sA %s service impl is active (%s), registering to it", self._label, self._resolver.name, self._service)
            for signal, listener in self._listeners_by_signal.items():
                if listener:
                    self._service.register(signal, listener)
        else:
            logger.debug("%sNo %s service impl is active", self._label, self._resolver.name)
