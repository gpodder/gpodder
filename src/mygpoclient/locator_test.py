# -*- coding: utf-8 -*-
# gpodder.net API Client
# Copyright (C) 2009-2010 Thomas Perl
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from mygpoclient import locator
import unittest

class Test_Exceptions(unittest.TestCase):
    def setUp(self):
        self.locator = locator.Locator('jane')

    def test_subscriptions_uri_exceptions(self):
        """Test if unsupported formats raise a ValueError"""
        self.assertRaises(ValueError,
                self.locator.subscriptions_uri, 'gpodder', 'html')

    def test_toplist_uri_exceptions(self):
        """Test if unsupported formats raise a ValueError"""
        self.assertRaises(ValueError,
                self.locator.toplist_uri, 10, 'html')

    def test_suggestions_uri_exceptions(self):
        """Test if unsupported formats raise a ValueError"""
        self.assertRaises(ValueError,
                self.locator.suggestions_uri, 20, 'jpeg')

    def test_search_uri_exception(self):
        """Test if unsupported formats raise a ValueError"""
        self.assertRaises(ValueError,
                self.locator.search_uri, 30, 'mp3')

    def test_subscription_updates_uri_exceptions(self):
        """Test if wrong "since" values raise a ValueError"""
        self.assertRaises(ValueError,
                self.locator.subscription_updates_uri, 'ipod', 'anytime')

    def test_download_episode_actions_uri_exceptions(self):
        """Test if using both "podcast" and "device_id" raises a ValueError"""
        self.assertRaises(ValueError,
                self.locator.download_episode_actions_uri,
                podcast='http://example.org/episodes.rss',
                device_id='gpodder')

