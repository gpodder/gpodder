# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
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

"""
Loads and executes user extensions.

Extensions are python scripts in ~/.config/gpodder/extensions.  Each script
must define a class named "Extension", otherwise it will be ignored.  For an
example extension see doc/dev/examples/extension.py
"""

import glob
import imp
import os

from gpodder.liblogger import log

class ExtensionManager:
    def __init__(self, gpodder):
        """
        Initializes the dispatcher.  Path is the gPodder dir, usually
        ~/.config/gpodder.  There must be the "excensions" subdir.
        """
        self.extensions = {}
        self.gpodder = gpodder

        for filename in glob.glob(os.path.join(gpodder.home, 'extensions', '*.py')):
          try:
              module = self.load_module(filename)
              if module is not None:
                  self.extensions[filename] = module
                  log('Extension loaded: %s', filename)
          except Exception, e:
              log('Error loading extension %s: %s', filename, e)

    def load_module(self, filepath):
        """
        Loads a module by file path. Looks ugly, there might be other ways to do this.
        """
        ext = os.path.splitext(os.path.basename(filepath))
        module = imp.load_module(ext[0], file(filepath, 'r'), os.path.dirname(filepath), (ext[1], 'r', imp.PY_SOURCE))
        if hasattr(module, 'Extension'):
            return module.Extension()

    def call(self, method, *args, **kwargs):
        """
        Calls the specified function in all user extensions that define it.
        The name is prepended with "on_", arguments are passed as is.

        Returns nothing.
        """
        method = 'on_' + method
        for name in self.extensions:
            module = self.extensions[name]
            if hasattr(module, method):
                try:
                    getattr(module, method)(*args, **kwargs)
                except Exception, e:
                    log('Error in user exception %s, function %s: %s', name, method, e)
