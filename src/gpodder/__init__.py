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
#

__author__    = 'Thomas Perl <thp@gpodder.org>'
__version__   = '0.16.0'
__date__      = '2009-05-XX'
__copyright__ = 'Copyright © 2005-2009 Thomas Perl and the gPodder Team'
__licence__   = 'GNU General Public License, version 3 or later'
__url__       = 'http://gpodder.org/'

import sys
import gettext

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


# The User-Agent string for downloads
user_agent = 'gPodder/%s (+%s)' % (__version__, __url__)

# Interface type enums
(CLI, GUI, MAEMO) = range(3)

# Are we running in GUI, Maemo or console mode?
interface = CLI

# D-Bus specific interface names
dbus_bus_name = 'org.godder'
dbus_gui_object_path = '/gui'
dbus_interface = 'org.gpodder.interface'

# i18n setup (will result in "gettext" to be available)
# Use   _ = gpodder.gettext   in modules to enable string translations
textdomain = 'gpodder'
locale_dir = gettext.bindtextdomain(textdomain)
t = gettext.translation(textdomain, locale_dir, fallback=True)
gettext = t.ugettext
del locale_dir
del t

# Variables reserved for GUI-specific use (will be set accordingly)
glade_file = None
icon_file = None

