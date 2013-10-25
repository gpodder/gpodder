# -*- coding: utf-8 -*-
#
# gpodder: Main module with release metadata
# Copyright (c) 2012, 2013, Thomas Perl <m@thp.io>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.
#

# This metadata block gets parsed by setup.py - use single quotes only
__tagline__   = 'Media and podcast aggregator'
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

