# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2012 Thomas Perl and the gPodder Team
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

# Test Runner for the podcastparser
# Thomas Perl <thp@gpodder.org>; 2012-12-29

import os
import glob
import json
import sys

here = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(here, '..', '..', 'src'))

from gpodder import podcastparser

RSS_FILES = os.path.join(here, 'data', '*.rss')

for rss_filename in glob.glob(RSS_FILES):
    basename, _ = os.path.splitext(rss_filename)
    json_filename = basename + '.json'

    expected = json.load(open(json_filename))
    parsed = podcastparser.parse(rss_filename, open(rss_filename))

    if expected != parsed:
        print 'FAIL:    ', basename
        print '='*40
        print 'EXPECTED:', json.dumps(expected, indent=2)
        print '='*40
        print 'PARSED:  ', json.dumps(parsed, indent=2)
        print '='*40
        sys.exit(1)
    else:
        print 'OK:      ', basename

