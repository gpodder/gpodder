# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
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
__tagline__   = 'Media aggregator and podcast client'
__author__    = 'Thomas Perl <thp@gpodder.org>'
__version__   = '3.8.3'
__date__      = '2014-10-30'
__relname__   = 'The Cheshire Project Part Two'
__copyright__ = '© 2005-2014 Thomas Perl and the gPodder Team'
__license__   = 'GNU General Public License, version 3 or later'
__url__       = 'http://gpodder.org/'

__version_info__ = tuple(int(x) for x in __version__.split('.'))

import os
import sys
import platform
import gettext
import locale

# Check if real hard dependencies are available
try:
    import feedparser
except ImportError:
    print """
  Error: Module "feedparser" (python-feedparser) not found.
         The feedparser module can be downloaded from
         http://code.google.com/p/feedparser/

  From a source checkout, you can download local copies of all
  CLI dependencies for debugging (will be placed into "src/"):

      python tools/localdepends.py
"""
    sys.exit(1)
del feedparser

try:
    import mygpoclient
except ImportError:
    print """
  Error: Module "mygpoclient" (python-mygpoclient) not found.
         The mygpoclient module can be downloaded from
         http://thp.io/2010/mygpoclient/

  From a source checkout, you can download local copies of all
  CLI dependencies for debugging (will be placed into "src/"):

      python tools/localdepends.py
"""
    sys.exit(1)
del mygpoclient

try:
    import sqlite3
except ImportError:
    print """
  Error: Module "sqlite3" not found.
         Build Python with SQLite 3 support or get it from
         http://code.google.com/p/pysqlite/
"""
    sys.exit(1)
del sqlite3


# The User-Agent string for downloads
user_agent = 'gPodder/%s (+%s)' % (__version__, __url__)

# Are we running in GUI, MeeGo 1.2 Harmattan or console mode?
class UI(object):
    def __init__(self):
        self.harmattan = False
        self.gtk = False
        self.qml = False
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

# i18n setup (will result in "gettext" to be available)
# Use   _ = gpodder.gettext   in modules to enable string translations
textdomain = 'gpodder'
locale_dir = gettext.bindtextdomain(textdomain)
t = gettext.translation(textdomain, locale_dir, fallback=True)

try:
    # Python 2
    gettext = t.ugettext
    ngettext = t.ungettext
except AttributeError:
    # Python 3
    gettext = t.gettext
    ngettext = t.ngettext

if ui.win32:
    try:
        # Workaround for bug 650
        from gtk.glade import bindtextdomain
        bindtextdomain(textdomain, locale_dir)
        del bindtextdomain
    except:
        # Ignore for QML UI or missing glade module
        pass
del t

# Set up textdomain for gtk.Builder (this accesses the C library functions)
if hasattr(locale, 'bindtextdomain'):
    locale.bindtextdomain(textdomain, locale_dir)

del locale_dir

# Set up socket timeouts to fix bug 174
SOCKET_TIMEOUT = 60
import socket
socket.setdefaulttimeout(SOCKET_TIMEOUT)
del socket
del SOCKET_TIMEOUT

# Variables reserved for GUI-specific use (will be set accordingly)
ui_folders = []
credits_file = None
icon_file = None
images_folder = None
user_extensions = None

# Episode states used in the database
STATE_NORMAL, STATE_DOWNLOADED, STATE_DELETED = range(3)

# Paths (gPodder's home folder, config, db, download and data prefix)
home = None
config_file = None
database_file = None
downloads = None
prefix = None

ENV_HOME, ENV_DOWNLOADS = 'GPODDER_HOME', 'GPODDER_DOWNLOAD_DIR'

# Function to set a new gPodder home folder
def set_home(new_home):
    global home, config_file, database_file, downloads
    home = os.path.abspath(new_home)

    config_file = os.path.join(home, 'Settings.json')
    database_file = os.path.join(home, 'Database')
    if ENV_DOWNLOADS not in os.environ:
        downloads = os.path.join(home, 'Downloads')

def fixup_home(old_home):
    if ui.osx:
        new_home = os.path.expanduser(os.path.join('~', 'Library',
            'Application Support', 'gPodder'))

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
    print >>sys.stderr, 'Storing data in', home, '(GPODDER_HOME is set)'

if ENV_DOWNLOADS in os.environ:
    # Allow to relocate the downloads folder (pull request 4, bug 466)
    downloads = os.environ[ENV_DOWNLOADS]
    print >>sys.stderr, 'Storing downloads in %s (%s is set)' % (downloads,
            ENV_DOWNLOADS)

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
        except Exception, e:
            print >>sys.stderr, 'Cannot load plugin: %s (%s)' % (plugin, e)


def detect_platform():
    global ui

    try:
        etc_issue = open('/etc/issue').read()
    except Exception, e:
        etc_issue = ''

    ui.harmattan = ('MeeGo 1.2 Harmattan' in etc_issue)

    if ui.harmattan and ENV_HOME not in os.environ:
        new_home = os.path.expanduser(os.path.join('~', 'MyDocs', 'gPodder'))
        set_home(os.path.expanduser(new_home))

