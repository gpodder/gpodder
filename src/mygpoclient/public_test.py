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

from mygpoclient import public
from mygpoclient import simple
from mygpoclient import testing

import unittest

class Test_ToplistPodcast(unittest.TestCase):
    def test_toplistPodcastFromDict_raisesValueError_missingKey(self):
        d = {
                'url': 'http://example.org/feeds/podcast.rss',
                'title': 'My Example Podcast Feed',
        }
        self.assertRaises(ValueError,
                public.ToplistPodcast.from_dict, d)


class Test_PublicClient(unittest.TestCase):
    TOPLIST_JSON = """
    [{"url": "http://twit.tv/node/4350/feed",
     "title": "FLOSS Weekly",
     "description": "Free, Libre and Open Source Software with Leo.",
     "subscribers": 4711,
     "subscribers_last_week": 4700
    },
    {"url": "http://feeds.feedburner.com/LinuxOutlaws",
     "title": "The Linux Outlaws",
     "description": "A podcast about Linux with Dan and Fab.",
     "subscribers": 1337,
     "subscribers_last_week": 1330
    }]
    """
    TOPLIST = [
            public.ToplistPodcast('http://twit.tv/node/4350/feed',
                'FLOSS Weekly',
                'Free, Libre and Open Source Software with Leo.',
                4711, 4700),
            public.ToplistPodcast('http://feeds.feedburner.com/LinuxOutlaws',
                'The Linux Outlaws',
                'A podcast about Linux with Dan and Fab.',
                1337, 1330),
    ]
    SEARCHRESULT_JSON = """
    [{"url": "http://twit.tv/node/4350/feed",
      "title": "FLOSS Weekly",
      "description": "Free, Libre and Open Source Software with Leo."
    },
    {"url": "http://feeds.feedburner.com/LinuxOutlaws",
      "title": "The Linux Outlaws",
      "description": "A podcast about Linux with Dan and Fab."
    }]
    """
    SEARCHRESULT = [
            simple.Podcast('http://twit.tv/node/4350/feed',
                'FLOSS Weekly',
                'Free, Libre and Open Source Software with Leo.'),
            simple.Podcast('http://feeds.feedburner.com/LinuxOutlaws',
                'The Linux Outlaws',
                'A podcast about Linux with Dan and Fab.'),
    ]

    def setUp(self):
        self.fake_client = testing.FakeJsonClient()
        self.client = public.PublicClient(client_class=self.fake_client)

    def test_getToplist(self):
        self.fake_client.response_value = self.TOPLIST_JSON
        result = self.client.get_toplist()
        self.assertEquals(result, self.TOPLIST)
        self.assertEquals(len(self.fake_client.requests), 1)

    def test_searchPodcasts(self):
        self.fake_client.response_value = self.SEARCHRESULT_JSON
        result = self.client.search_podcasts('wicked')
        self.assertEquals(result, self.SEARCHRESULT)
        self.assertEquals(len(self.fake_client.requests), 1)

