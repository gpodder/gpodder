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

# Mikołaj Milej <mikolajmm@gmail.com>; 2013-01-02

import os

from PySide.QtCore import QUrl
from PySide.QtDeclarative import QDeclarativeComponent

import gpodder
from gpodder import gettext, ngettext

_ = gettext
N_ = ngettext

EPISODE_LIST_FILTERS = [
    # (UI label, EQL expression)
    (_('All'), None),
    (_('Hide deleted'), 'not deleted'),
    (_('New'), 'new or downloading'),
    (_('Downloaded'), 'downloaded or downloading'),
    (_('Deleted'), 'deleted'),
    (_('Finished'), 'finished'),
    (_('Archived'), 'downloaded and archive'),
    (_('Videos'), 'video'),
    (_('Partially played'), 'downloaded and played and not finished'),
    (_('Unplayed downloads'), 'downloaded and not played'),
]

EPISODE_LIST_LIMIT = 200


def QML(filename):
    for folder in gpodder.ui_folders:
        filename = os.path.join(folder, filename)
        if os.path.exists(filename):
            return filename


class QObjectProxy(object):
    """Proxy for accessing properties and slots as attributes

    This class acts as a proxy for the qmlObject for which it is
    created, and makes property access more Pythonic while
    still allowing access to slots (as member functions).

    Attribute names starting with '_' are not proxied.
    """

    def __init__(self, root_object):
        self._root_object = root_object
        m = self._root_object.metaObject()
        self._properties = [m.property(i).name() \
                for i in range(m.propertyCount())]

    def __getattr__(self, key):
        value = self._root_object.property(key)

        # No such property, so assume we call a slot
        if value is None and key not in self._properties:
            return getattr(self._root_object, key)

        return value

    def __setattr__(self, key, value):
        if key.startswith('_'):
            object.__setattr__(self, key, value)
        else:
            self._root_object.setProperty(key, value)


class QmlGuiComponent():
    def __init__(self, qobject, qcomponent):
        self.object = QObjectProxy(qobject)
        self.component = qcomponent

    def setVisible(self, visible):
        self.object.visible = visible


def createQmlComponent(filename, engine, context, parent=None):
    # Load the QML UI (this could take a while...)
    qcomponent = QDeclarativeComponent(
        engine, QUrl.fromLocalFile(QML(filename)), parent
    )
    qobject = qcomponent.create(context)

    error = qcomponent.errorString()

    if len(error) > 0:
        print('Error while loading QML file: ' + error)

    return QmlGuiComponent(qobject, qcomponent)
