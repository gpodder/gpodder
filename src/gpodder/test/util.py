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

# gpodder.test.util - Unit tests for gpodder.util
# Kyle Stevens <kstevens715@gmail.com>; 2013-05-25


import unittest

import gpodder

from gpodder import util

class TestNormalizeFeedUrl(unittest.TestCase):

    def test_convert_scheme(self):
        self.assertEqual(util.normalize_feed_url('itpc://example.org/podcast.rss'), 'http://example.org/podcast.rss')

    def test_no_url_scheme(self):
        self.assertEqual(util.normalize_feed_url('curry.com'), 'http://curry.com/')

    def test_convert_to_lower(self):
        self.assertEqual(util.normalize_feed_url('http://Example.COM/'), 'http://example.com/')

    def test_auth_not_altered(self):
        self.assertEqual(util.normalize_feed_url('http://Bob@example.com:Password@Example.COM/'), 'http://Bob@example.com:Password@example.com/')

    def test_remove_empty_query(self):
        self.assertEqual(util.normalize_feed_url('http://example.org/test?'), 'http://example.org/test')

    def test_shortcut(self):
        self.assertEqual(util.normalize_feed_url('fb:43FPodcast'), 'http://feeds.feedburner.com/43FPodcast')
