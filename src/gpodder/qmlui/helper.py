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

from PySide import QtCore

def AutoQObject(*class_def, **kwargs):
    class Object(QtCore.QObject):
        def __init__(self, **kwargs):
            QtCore.QObject.__init__(self)
            for key, val in class_def:
                setattr(self, '_'+key, kwargs.get(key, val()))

        def __repr__(self):
            values = ('%s=%r' % (key, getattr(self, '_'+key)) \
                    for key, value in class_def)
            return '<%s (%s)>' % (kwargs.get('name', 'QObject'), \
                    ', '.join(values))

        for key, value in class_def:
            nfy = locals()['_nfy_'+key] = QtCore.Signal()

            def _get(key):
                def f(self):
                    return self.__dict__['_'+key]
                return f

            def _set(key):
                def f(self, value):
                    setattr(self, '_'+key, value)
                    getattr(self, '_nfy_'+key).emit()
                return f

            set = locals()['_set_'+key] = _set(key)
            get = locals()['_get_'+key] = _get(key)

            locals()[key] = QtCore.Property(value, get, set, notify=nfy)

    return Object


class Action(QtCore.QObject):
    def __init__(self, caption, action, target=None):
        QtCore.QObject.__init__(self)
        if isinstance(caption, str):
            caption = caption.decode('utf-8')
        self._caption = caption

        self.action = action
        self.target = target

    changed = QtCore.Signal()

    def _get_caption(self):
        return self._caption

    caption = QtCore.Property(unicode, _get_caption, notify=changed)


class QObjectProxy(object):
    """Proxy for accessing properties and slots as attributes

    This class acts as a proxy for the object for which it is
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

