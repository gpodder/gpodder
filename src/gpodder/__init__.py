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

# This metadata block gets parsed by setup.py - use single quotes only
__tagline__   = 'Media aggregator and podcast client'
__author__    = 'Thomas Perl <thp@gpodder.org>'
__version__   = '3.99.9'
__date__      = '2013-04-10'
__relname__   = 'Cuatro'
__copyright__ = '© 2005-2013 Thomas Perl and the gPodder Team'
__license__   = 'GNU General Public License, version 3 or later'
__url__       = 'http://gpodder.org/'

__version_info__ = tuple(int(x) for x in __version__.split('.'))

# The User-Agent string for downloads
user_agent = 'gPodder/%s (+%s)' % (__version__, __url__)

# Episode states used in the database
STATE_NORMAL, STATE_DOWNLOADED, STATE_DELETED = list(range(3))

# Fallback implementation when gettext is not used
gettext = lambda x: x
ngettext = lambda x, y, n: x if n == 1 else y

