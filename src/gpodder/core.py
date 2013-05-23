# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2013 Thomas Perl and the gPodder Team
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
from gpodder import storage
from gpodder import extensions
from gpodder import coverart
from gpodder import model
from gpodder import log

import os
import gettext
import logging
import socket

class Core(object):
    def __init__(self,
                 config_class=config.Config,
                 database_class=storage.Database,
                 model_class=model.Model,
                 prefix=None,
                 verbose=True):
        self._init_i18n()
        self._set_socket_timeout()

        self.prefix = prefix
        if not self.prefix:
            # XXX
            self.prefix = os.path.abspath('.')

        # Home folder: ~/gPodder or $GPODDER_HOME (if set)
        self.home = os.path.abspath(os.environ.get('GPODDER_HOME',
                os.path.expanduser(os.path.join('~', 'gPodder'))))

        # Setup logging
        log.setup(self.home, verbose)
        self.logger = logging.getLogger(__name__)

        config_file = os.path.join(self.home, 'Settings.json')
        database_file = os.path.join(self.home, 'Database')
        # Downloads folder: <home>/Downloads or $GPODDER_DOWNLOAD_DIR (if set)
        self.downloads = os.environ.get('GPODDER_DOWNLOAD_DIR',
                os.path.join(self.home, 'Downloads'))

        # Initialize the gPodder home directory
        util.make_directory(self.home)

        # Open the database and configuration file
        self.db = database_class(database_file)
        self.model = model_class(self)
        self.config = config_class(config_file)

        # Load extension modules and install the extension manager
        gpodder.user_extensions = extensions.ExtensionManager(self)

        # Load installed/configured plugins
        self._load_plugins()

        self.cover_downloader = coverart.CoverDownloader(self)

    def _init_i18n(self):
        # i18n setup (will result in "gettext" to be available)
        # Use   _ = gpodder.gettext   in modules to enable string translations
        textdomain = 'gpodder'
        locale_dir = gettext.bindtextdomain(textdomain)
        t = gettext.translation(textdomain, locale_dir, fallback=True)
        gpodder.gettext = t.gettext
        gpodder.ngettext = t.ngettext

    def _set_socket_timeout(self):
        # Set up socket timeouts to fix bug 174
        SOCKET_TIMEOUT = 60
        socket.setdefaulttimeout(SOCKET_TIMEOUT)

    def _load_plugins(self):
        # Plugins to load by default
        DEFAULT_PLUGINS = [
            'gpodder.plugins.soundcloud',
            'gpodder.plugins.xspf',
            'gpodder.plugins.podcast',
        ]

        PLUGINS = os.environ.get('GPODDER_PLUGINS', None)
        if PLUGINS is None:
            PLUGINS = DEFAULT_PLUGINS
        else:
            PLUGINS = PLUGINS.split()
        for plugin in PLUGINS:
            try:
                __import__(plugin)
            except Exception as e:
                self.logger.warn('Cannot load plugin "%s": %s', plugin, e,
                        exc_info=True)

    def shutdown(self):
        self.logger.info('Shutting down core')

        # Notify all extensions that we are being shut down
        gpodder.user_extensions.shutdown()

        # Close the configuration and store outstanding changes
        self.config.close()

        # Close the database and store outstanding changes
        self.db.close()

