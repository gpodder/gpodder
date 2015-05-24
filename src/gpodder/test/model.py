# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2015 Thomas Perl and the gPodder Team
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

# gpodder.test.model - Unit tests for gpodder.model
# Thomas Perl <thp@gpodder.org>; 2013-02-12


import unittest

import gpodder

from gpodder import model

class TestEpisodePublishedProperties(unittest.TestCase):
    PUBLISHED_UNIXTIME = 1360666744
    PUBLISHED_SORT = '2013-02-12'
    PUBLISHED_YEAR = '13'
    PUBLISHED_MONTH = '02'
    PUBLISHED_DAY = '12'

    def setUp(self):
        self.podcast = model.PodcastChannel(None)
        self.episode = model.PodcastEpisode(self.podcast)
        self.episode.published = self.PUBLISHED_UNIXTIME

    def test_sortdate(self):
        self.assertEqual(self.episode.sortdate, self.PUBLISHED_SORT)

    def test_pubdate_year(self):
        self.assertEqual(self.episode.pubdate_year, self.PUBLISHED_YEAR)

    def test_pubdate_month(self):
        self.assertEqual(self.episode.pubdate_month, self.PUBLISHED_MONTH)

    def test_pubdate_day(self):
        self.assertEqual(self.episode.pubdate_day, self.PUBLISHED_DAY)

