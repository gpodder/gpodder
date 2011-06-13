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

import mygpoclient

from mygpoclient import locator
from mygpoclient import json
from mygpoclient import simple

class ToplistPodcast(object):
    """Container class for a toplist entry

    This class encapsulates the metadata for a podcast
    in the podcast toplist.

    Attributes:
    url - The feed URL of the podcast
    title - The title of the podcast
    description - The description of the podcast
    subscribers - The current subscriber count
    subscribers_last_week - Last week's subscriber count
    """
    REQUIRED_KEYS = ('url', 'title', 'description', \
                     'subscribers', 'subscribers_last_week')

    def __init__(self, url, title, description,
            subscribers, subscribers_last_week):
        self.url = url
        self.title = title
        self.description = description
        self.subscribers = int(subscribers)
        self.subscribers_last_week = int(subscribers_last_week)

    def __eq__(self, other):
        """Test two ToplistPodcast objects for equality

        >>> ToplistPodcast('u', 't', 'd', 10, 12) == ToplistPodcast('u', 't', 'd', 10, 12)
        True
        >>> ToplistPodcast('u', 't', 'd', 10, 12) == ToplistPodcast('a', 'b', 'c', 13, 14)
        False
        >>> ToplistPodcast('u', 't', 'd', 10, 12) == 'x'
        False
        """
        if not isinstance(other, self.__class__):
            return False

        return all(getattr(self, k) == getattr(other, k) \
                for k in self.REQUIRED_KEYS)

    @classmethod
    def from_dict(cls, d):
        for key in cls.REQUIRED_KEYS:
            if key not in d:
                raise ValueError('Missing keys for toplist podcast')

        return cls(*(d.get(k) for k in cls.REQUIRED_KEYS))


class PublicClient(object):
    """Client for the gpodder.net "anonymous" API

    This is the API client implementation that provides a
    pythonic interface to the parts of the gpodder.net
    Simple API that don't need user authentication.
    """
    FORMAT = 'json'

    def __init__(self, host=mygpoclient.HOST, client_class=json.JsonClient):
        """Creates a new Public API client

        The parameter host is optional and defaults to
        the main webservice.

        The parameter client_class is optional and should
        not need to be changed in normal use cases. If it
        is changed, it should provide the same interface
        as the json.JsonClient class in mygpoclient.
        """
        self._locator = locator.Locator(None, host)
        self._client = client_class(None, None)

    def get_toplist(self, count=mygpoclient.TOPLIST_DEFAULT):
        """Get a list of most-subscribed podcasts

        Returns a list of ToplistPodcast objects.

        The parameter "count" is optional and describes
        the amount of podcasts that are returned. The
        default value is 50, the minimum value is 1 and
        the maximum value is 100.
        """
        uri = self._locator.toplist_uri(count, self.FORMAT)
        return [ToplistPodcast.from_dict(x) for x in self._client.GET(uri)]

    def search_podcasts(self, query):
        """Search for podcasts on the webservice

        Returns a list of simple.Podcast objects.

        The parameter "query" specifies the search
        query as a string.
        """
        uri = self._locator.search_uri(query, self.FORMAT)
        return [simple.Podcast.from_dict(x) for x in self._client.GET(uri)]

