# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2010 Thomas Perl and the gPodder Team
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
                self.__dict__['_'+key] = kwargs.get(key, val())

        def __repr__(self):
            values = ('%s=%r' % (key, self.__dict__['_'+key]) \
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
                    self.__dict__['_'+key] = value
                    self.__dict__['_nfy_'+key].emit()
                return f

            set = locals()['_set_'+key] = _set(key)
            get = locals()['_get_'+key] = _get(key)

            locals()[key] = QtCore.Property(value, get, set, notify=nfy)

    return Object

