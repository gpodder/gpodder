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

# Mikołaj Milej <mikolajmm@gmail.com>; 2013-01-09

from PySide.QtCore import QObject, Signal, Property


class ConfigProxy(QObject):
    def __init__(self, config):
        QObject.__init__(self)
        self._config = config

        config.add_observer(self._on_config_changed)

    def _on_config_changed(self, name, old_value, new_value):
        if name == 'ui.qml_desktop.autorotate':
            self.autorotateChanged.emit()
        elif name == 'flattr.token':
            self.flattrTokenChanged.emit()
        elif name == 'flattr.flattr_on_play':
            self.flattrOnPlayChanged.emit()

    def get_autorotate(self):
        return self._config.ui.qml_desktop.autorotate

    def set_autorotate(self, autorotate):
        self._config.ui.qml_desktop.autorotate = autorotate

    autorotateChanged = Signal()

    autorotate = Property(bool, get_autorotate, set_autorotate,
            notify=autorotateChanged)

    def get_flattr_token(self):
        return self._config.flattr.token

    def set_flattr_token(self, flattr_token):
        self._config.flattr.token = flattr_token

    flattrTokenChanged = Signal()

    flattrToken = Property(unicode, get_flattr_token, set_flattr_token,
            notify=flattrTokenChanged)

    def get_flattr_on_play(self):
        return self._config.flattr.flattr_on_play

    def set_flattr_on_play(self, flattr_on_play):
        self._config.flattr.flattr_on_play = flattr_on_play

    flattrOnPlayChanged = Signal()

    flattrOnPlay = Property(bool, get_flattr_on_play, set_flattr_on_play,
            notify=flattrOnPlayChanged)
