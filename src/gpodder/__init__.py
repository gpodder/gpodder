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

__author__    = 'Thomas Perl <thp@gpodder.org>'
__version__   = '2.11'
__date__      = '2010-12-19'
__copyright__ = '© 2005-2010 Thomas Perl and the gPodder Team'
__licence__   = 'GNU General Public License, version 3 or later'
__url__       = 'http://gpodder.org/'

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
  Error: Module "feedparser" not found. Please install "python-feedparser".
         The feedparser module can be downloaded from www.feedparser.org.
"""
    sys.exit(1)
del feedparser

try:
    import mygpoclient
except ImportError:
    print """
  Error: Module "mygpoclient" not found. Please install "python-mygpoclient"
         or download it from http://thp.io/2010/mygpoclient/
"""
    sys.exit(1)
del mygpoclient

# The User-Agent string for downloads
user_agent = 'gPodder/%s (+%s)' % (__version__, __url__)

# Are we running in GUI, Maemo or console mode?
class UI(object):
    def __init__(self):
        self.desktop = False
        self.fremantle = False

    @property
    def maemo(self):
        return self.fremantle

ui = UI()

# D-Bus specific interface names
dbus_bus_name = 'org.gpodder'
dbus_gui_object_path = '/gui'
dbus_podcasts_object_path = '/podcasts'
dbus_interface = 'org.gpodder.interface'
dbus_podcasts = 'org.gpodder.podcasts'
dbus_session_bus = None

# Set "win32" to True if we are on Windows
win32 = (platform.system() == 'Windows')

# i18n setup (will result in "gettext" to be available)
# Use   _ = gpodder.gettext   in modules to enable string translations
textdomain = 'gpodder'
locale_dir = gettext.bindtextdomain(textdomain)
t = gettext.translation(textdomain, locale_dir, fallback=True)
gettext = t.ugettext
ngettext = t.ungettext
if win32:
    # Workaround for bug 650
    from gtk.glade import bindtextdomain
    bindtextdomain(textdomain, locale_dir)
    del bindtextdomain
del t

# Set up textdomain for gtk.Builder (this accesses the C library functions)
if hasattr(locale, 'bindtextdomain'):
    locale.bindtextdomain(textdomain, locale_dir)
else:
    # On Win32, the locale module does not have bindtextdomain. We use a
    # small module that provides similar functionality here (from doc/dev/).
    try:
        import gtkbuilderi18n
        gtkbuilderi18n.bindtextdomain(textdomain, locale_dir)
    except ImportError, ioe:
        pass

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
user_hooks = None

# Episode states used in the database
STATE_NORMAL, STATE_DOWNLOADED, STATE_DELETED = range(3)

# Paths (gPodder's home folder, config, db and download folder)
home = None
config_file = None
database_file = None
downloads = None

# Function to set a new gPodder home folder
def set_home(new_home):
    global home, config_file, database_file, downloads
    home = new_home

    config_file = os.path.join(home, 'Settings')
    database_file = os.path.join(home, 'Database')
    downloads = os.path.join(home, 'Downloads')

# Default locations for configuration and data files
default_home = os.path.expanduser(os.path.join('~', 'gPodder'))
set_home(os.environ.get('GPODDER_HOME', default_home))

if home != default_home:
    print >>sys.stderr, 'Storing data in', home, '(GPODDER_HOME is set)'

# Plugins to load by default
DEFAULT_PLUGINS = ['gpodder.soundcloud', 'gpodder.xspf']

def load_plugins():
    """Load (non-essential) plugin modules

    This loads a default set of plugins, but you can use
    the environment variable "GPODDER_PLUGINS" to modify
    the list of plugins."""
    global DEFAULT_PLUGINS
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

