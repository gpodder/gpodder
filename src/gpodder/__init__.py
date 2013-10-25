# -*- coding: utf-8 -*-
#
# gpodder: Main module with release metadata
#

"""
gPodder: Media and podcast aggregator
Copyright (c) 2005-2013 Thomas Perl and the gPodder Team.

Historically, gPodder was licensed under the terms of the "GNU GPLv2 or
later", and has been upgraded to "GNU GPLv3 or later" in August 2007.

Code that has been solely written by thp was re-licensed to a more
permissive license (ISC license) in August 2013. The new license is
DFSG-compatible, FSF-approved, OSI-approved and GPL-compatible (see
http://en.wikipedia.org/wiki/ISC_license for more information).

For the license that applies to a file, see the copyright header in it.


==== ISC License Text ====

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.

==== GPLv3 License Text ====

gPodder is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

gPodder is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# This metadata block gets parsed by setup.py - use single quotes only
__tagline__   = 'Media and podcast aggregator'
__author__    = 'Thomas Perl <thp@gpodder.org>'
__version__   = '3.99.9'
__date__      = '2013-04-10'
__relname__   = 'Cuatro'
__copyright__ = '© 2005-2013 Thomas Perl and the gPodder Team'
__license__   = 'ISC / GPLv3 or later'
__url__       = 'http://gpodder.org/'

__version_info__ = tuple(int(x) for x in __version__.split('.'))

# The User-Agent string for downloads
user_agent = 'gPodder/%s (+%s)' % (__version__, __url__)

# Episode states used in the database
STATE_NORMAL, STATE_DOWNLOADED, STATE_DELETED = list(range(3))

