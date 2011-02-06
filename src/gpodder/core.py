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

# gpodder.core - Common functionality used by all UIs
# Thomas Perl <thp@gpodder.org>; 2011-02-06


import gpodder

from gpodder import util
from gpodder import config
from gpodder import dbsqlite
from gpodder import hooks


class Core(object):
    def __init__(self, \
            config_class=config.Config, \
            database_class=dbsqlite.Database):
        # Initialize the gPodder home directory
        util.make_directory(gpodder.home)

        # Load installed/configured plugins
        gpodder.load_plugins()

        # Load hook modules and install the hook manager
        user_hooks = hooks.HookManager()
        if user_hooks.has_modules():
            gpodder.user_hooks = user_hooks

        # Open the database and configuration file
        self.db = database_class(gpodder.database_file)
        self.config = config_class(gpodder.config_file)

        # Update the current device in the configuration
        self.config.mygpo_device_type = util.detect_device_type()

    def shutdown(self):
        # Close the database and store outstanding changes
        self.db.close()

