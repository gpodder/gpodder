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

from mygpoclient import simple
from mygpoclient import testing

import unittest

class Test_Podcast(unittest.TestCase):
    def test_podcastFromDict_raisesValueError_missingKey(self):
        self.assertRaises(ValueError,
                simple.Podcast.from_dict, {'url': 'a', 'title': 'b'})

class Test_SimpleClient(unittest.TestCase):
    USERNAME = 'a'
    PASSWORD = 'b'
    DEVICE_NAME = 'x'
    SUBSCRIPTIONS = [
            'http://lugradio.org/episodes.rss',
            'http://feeds2.feedburner.com/LinuxOutlaws',
    ]
    SUBSCRIPTIONS_JSON = """
      ["http://lugradio.org/episodes.rss",
       "http://feeds2.feedburner.com/LinuxOutlaws"]
    """
    SUGGESTIONS = [
      simple.Podcast('http://twit.tv/node/4350/feed',
                     'FLOSS Weekly',
                     'Free, Libre and Open Source Software with Leo.'),
      simple.Podcast('http://feeds.feedburner.com/LinuxOutlaws',
                     'The Linux Outlaws',
                     'A podcast about Linux with Dan and Fab.'),
    ]
    SUGGESTIONS_JSON = """
      [{"url": "http://twit.tv/node/4350/feed",
       "title": "FLOSS Weekly",
       "description": "Free, Libre and Open Source Software with Leo."
      },
      {"url": "http://feeds.feedburner.com/LinuxOutlaws",
       "title": "The Linux Outlaws",
       "description": "A podcast about Linux with Dan and Fab."
      }]
    """

    def setUp(self):
        self.fake_client = testing.FakeJsonClient()
        self.client = simple.SimpleClient(self.USERNAME, self.PASSWORD,
                client_class=self.fake_client)

    def test_putSubscriptions(self):
        self.fake_client.response_value = ''
        result = self.client.put_subscriptions(self.DEVICE_NAME, self.SUBSCRIPTIONS)
        self.assertEquals(result, True)
        self.assertEquals(len(self.fake_client.requests), 1)

    def test_getSubscriptions(self):
        self.fake_client.response_value = self.SUBSCRIPTIONS_JSON
        subscriptions = self.client.get_subscriptions(self.DEVICE_NAME)
        self.assertEquals(subscriptions, self.SUBSCRIPTIONS)
        self.assertEquals(len(self.fake_client.requests), 1)

    def test_getSuggestions(self):
        self.fake_client.response_value = self.SUGGESTIONS_JSON
        suggestions = self.client.get_suggestions(50)
        self.assertEquals(suggestions, self.SUGGESTIONS)
        self.assertEquals(len(self.fake_client.requests), 1)

