# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (C) 2005-2007 Thomas Perl <thp at perli.net>
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

# dumbshelve.py - Temporary implementation of a shelve replacement
# 2008-02-27 Thomas Perl <thpinfo.com>

from gpodder.liblogger import log

import UserDict
import cPickle
import os.path

class DumbShelve(UserDict.UserDict):
    """
    Simply tries to act like a "shelve" object..
    """
    def __init__(self, filename=None):
        UserDict.UserDict.__init__(self)
        self.__filename = filename
        self.__dirty = False

    def sync(self, filename=None):
        if not self.__dirty:
            return True

        if filename is not None:
            self.__filename = filename
        try:
            self.__dirty = False
            cPickle.dump(self, open(self.__filename, 'w'))
            return True
        except:
            log('Cannot pickle me to %s', self.__filename, sender=self, traceback=True)
            return False

    def __setitem__(self, key, item):
        self.__dirty = True
        UserDict.UserDict.__setitem__(self, key, item)

    def __delitem__(self, key):
        self.__dirty = True
        UserDict.UserDict.__delitem__(self, key)

def open_shelve(filename):
    if not os.path.exists(filename):
        return DumbShelve(filename)
    else:
        try:
            return cPickle.load(open(filename, 'r'))
        except:
            log('Error loading %s. Creating new DumbShelve.', filename, traceback=True)
            return DumbShelve(filename)

