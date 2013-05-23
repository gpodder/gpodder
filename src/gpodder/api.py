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

#
# gpodder.api - Listing of functions exposed to external applications
# Thomas Perl <m@thp.io>; 2013-05-23
#

# This module exposes top-level API functionality that can be imported
# by applications not living in the gPodder source tree. It is used to
# determine which functions must be provided by the gPodder tree.

import gpodder.core
import gpodder.util

class core:
    Core = gpodder.core.Core

class util:
    run_in_background = gpodder.util.run_in_background
    normalize_feed_url = gpodder.util.normalize_feed_url
    remove_html_tags = gpodder.util.remove_html_tags

