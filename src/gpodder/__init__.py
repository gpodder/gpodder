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

# This metadata block gets parsed by setup.py - use single quotes only
__tagline__ = 'Media aggregator and podcast client'
__author__ = 'Thomas Perl <thp@gpodder.org>'
__version__ = '3.11.2'
__date__ = '2023-08-13'
__copyright__ = '© 2005-2023 The gPodder Team'
__license__ = 'GNU General Public License, version 3 or later'
__url__ = 'http://gpodder.org/'

# Use public version part for __version_info__, see PEP 440
__public_version__, __local_version__ = next(
    (v[0], v[1] if len(v) > 1 else '') for v in (__version__.split('+'),))
__version_info__ = tuple(int(x) for x in __public_version__.split('.'))

import gettext
import locale
import os
import platform
import socket
import sys

from gpodder.build_info import BUILD_TYPE

# Check if real hard dependencies are available
try:
    import podcastparser
except ImportError:
    print("""
  Error: Module "podcastparser" (python-podcastparser) not found.
         The podcastparser module can be downloaded from
         http://gpodder.org/podcastparser/

  From a source checkout, see https://gpodder.github.io/docs/run-from-git.html
""")
    sys.exit(1)
del podcastparser

try:
    import mygpoclient
except ImportError:
    print("""
  Error: Module "mygpoclient" (python-mygpoclient) not found.
         The mygpoclient module can be downloaded from
         http://gpodder.org/mygpoclient/

  From a source checkout, see https://gpodder.github.io/docs/run-from-git.html
""")
    sys.exit(1)
del mygpoclient

try:
    import sqlite3
except ImportError:
    print("""
  Error: Module "sqlite3" not found.
         Build Python with SQLite 3 support or get it from
         http://code.google.com/p/pysqlite/
""")
    sys.exit(1)
del sqlite3


# Is gpodder running in verbose mode?
verbose = False
# Is gpodder running in quiet mode?
quiet = False


# The User-Agent string for downloads
user_agent = 'gPodder/%s (+%s) %s' % (__version__, __url__, platform.system())


# Are we running in GUI or console mode?
class UI(object):
    def __init__(self):
        self.gtk = False
        self.cli = False


ui = UI()

# D-Bus specific interface names
dbus_bus_name = 'org.gpodder'
dbus_gui_object_path = '/gui'
dbus_podcasts_object_path = '/podcasts'
dbus_interface = 'org.gpodder.interface'
dbus_podcasts = 'org.gpodder.podcasts'
dbus_session_bus = None

# Set "win32" to True if we are on Windows
ui.win32 = (platform.system() == 'Windows')
# Set "osx" to True if we are on Mac OS X
ui.osx = (platform.system() == 'Darwin')
# We assume it's a freedesktop.org system if it's not Windows or OS X
ui.freedesktop = not ui.win32 and not ui.osx

# i18n setup (will result in "gettext" to be available)
# Use   _ = gpodder.gettext   in modules to enable string translations
textdomain = 'gpodder'
locale_dir = gettext.bindtextdomain(textdomain)

if ui.win32:
    # this must be done prior to gettext.translation to set the locale (see #484)
    from gpodder.utilwin32locale import install
    install(textdomain, locale_dir)

t = gettext.translation(textdomain, locale_dir, fallback=True)

gettext = t.gettext
ngettext = t.ngettext

del t

# Set up textdomain for Gtk.Builder (this accesses the C library functions)
if hasattr(locale, 'bindtextdomain'):
    locale.bindtextdomain(textdomain, locale_dir)

del locale_dir

# Set up socket timeouts to fix bug 174
SOCKET_TIMEOUT = 60
socket.setdefaulttimeout(SOCKET_TIMEOUT)
del socket
SOCKET_TIMEOUT

# Variables reserved for GUI-specific use (will be set accordingly)
ui_folders = []
icon_file = None
images_folder = None
user_extensions = None

# Episode states used in the database
STATE_NORMAL, STATE_DOWNLOADED, STATE_DELETED = list(range(3))

# Paths (gPodder's home folder, config, db, download and data prefix)
home = None
config_file = None
database_file = None
downloads = None
prefix = None

ENV_HOME, ENV_DOWNLOADS = 'GPODDER_HOME', 'GPODDER_DOWNLOAD_DIR'

no_update_check_file = None


# Function to set a new gPodder home folder
def set_home(new_home):
    global home, config_file, database_file, downloads
    home = os.path.abspath(new_home)

    config_file = os.path.join(home, 'Settings.json')
    database_file = os.path.join(home, 'Database')
    if ENV_DOWNLOADS not in os.environ:
        downloads = os.path.join(home, 'Downloads')


def fixup_home(old_home):
    if ui.osx or ui.win32:
        if ui.osx:
            new_home = os.path.expanduser(os.path.join('~', 'Library',
                'Application Support', 'gPodder'))
        elif BUILD_TYPE == 'windows-portable':
            new_home = os.path.normpath(os.path.join(os.path.dirname(sys.executable), "..", "..", "config"))
            old_home = new_home  # force to config directory
            print("D: windows-portable build; forcing home to config directory %s" % new_home, file=sys.stderr)
        else:  # ui.win32, not portable build
            from gpodder.utilwin32ctypes import (
                get_documents_folder, get_reg_current_user_string_value)
            try:
                # from old launcher, see
                # https://github.com/gpodder/gpodder/blob/old/gtk2/tools/win32-launcher/folderselector.c
                new_home = get_reg_current_user_string_value("Software\\gpodder.org\\gPodder", "GPODDER_HOME")
                print("D: windows build; registry home = %s" % new_home, file=sys.stderr)
            except Exception as e:
                print("E: can't get GPODDER_HOME from registry: %s" % e, file=sys.stderr)
                new_home = None
            if new_home is None:
                try:
                    new_home = os.path.join(get_documents_folder(), "gPodder")
                    print("D: windows build; documents home = %s" % new_home, file=sys.stderr)
                except Exception as e:
                    print("E: can't get user's Documents folder: %s" % e, file=sys.stderr)
                    new_home = old_home

        # Users who do not have the old home directory, or who have it but also
        # have the new home directory (to cater to situations where the user
        # might for some reason or the other have a ~/gPodder/ directory) get
        # to use the new, more OS X-ish home.
        if not os.path.exists(old_home) or os.path.exists(new_home):
            return new_home

    return old_home


# Default locations for configuration and data files
default_home = os.path.expanduser(os.path.join('~', 'gPodder'))
default_home = fixup_home(default_home)
set_home(os.environ.get(ENV_HOME, default_home))

if home != default_home:
    print('Storing data in', home, '(GPODDER_HOME is set)', file=sys.stderr)

if ENV_DOWNLOADS in os.environ:
    # Allow to relocate the downloads folder (pull request 4, bug 466)
    downloads = os.environ[ENV_DOWNLOADS]
    print('Storing downloads in %s (%s is set)' % (downloads,
            ENV_DOWNLOADS), file=sys.stderr)

# Plugins to load by default
DEFAULT_PLUGINS = [
    'gpodder.plugins.soundcloud',
]


def load_plugins():
    """Load (non-essential) plugin modules

    This loads a default set of plugins, but you can use
    the environment variable "GPODDER_PLUGINS" to modify
    the list of plugins."""
    PLUGINS = os.environ.get('GPODDER_PLUGINS', None)
    if PLUGINS is None:
        PLUGINS = DEFAULT_PLUGINS
    else:
        PLUGINS = PLUGINS.split()
    for plugin in PLUGINS:
        try:
            __import__(plugin)
        except Exception as e:
            print('Cannot load plugin: %s (%s)' % (plugin, e), file=sys.stderr)
