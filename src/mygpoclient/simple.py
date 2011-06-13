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

class Podcast(object):
    """Container class for a podcast

    Encapsulates the metadata for a podcast.

    Attributes:
    url - The URL of the podcast feed
    title - The title of the podcast
    description - The description of the podcast
    """
    REQUIRED_FIELDS = ('url', 'title', 'description')

    def __init__(self, url, title, description):
        self.url = url
        self.title = title
        self.description = description

    @classmethod
    def from_dict(cls, d):
        for key in cls.REQUIRED_FIELDS:
            if key not in d:
                raise ValueError('Missing keys for toplist podcast')

        return cls(*(d.get(k) for k in cls.REQUIRED_FIELDS))

    def __eq__(self, other):
        """Test two Podcast objects for equality

        >>> Podcast('a', 'b', 'c') == Podcast('a', 'b', 'c')
        True
        >>> Podcast('a', 'b', 'c') == Podcast('x', 'y', 'z')
        False
        >>> Podcast('a', 'b', 'c') == 'a'
        False
        """
        if not isinstance(other, self.__class__):
            return False

        return all(getattr(self, k) == getattr(other, k) \
                for k in self.REQUIRED_FIELDS)


class SimpleClient(object):
    """Client for the gpodder.net Simple API

    This is the API client implementation that provides a
    pythonic interface to the gpodder.net Simple API.
    """
    FORMAT = 'json'

    def __init__(self, username, password, host=mygpoclient.HOST,
            client_class=json.JsonClient):
        """Creates a new Simple API client

        Username and password must be specified and are
        the user's login data for the webservice.

        The parameter host is optional and defaults to
        the main webservice.

        The parameter client_class is optional and should
        not need to be changed in normal use cases. If it
        is changed, it should provide the same interface
        as the json.JsonClient class in mygpoclient.
        """
        self.username = username
        self.password = password
        self._locator = locator.Locator(username, host)
        self._client = client_class(username, password)

    def get_subscriptions(self, device_id):
        """Get a list of subscriptions for a device

        Returns a list of URLs (one per subscription) for
        the given device_id that reflects the current list
        of subscriptions.

        Raises http.NotFound if the device does not exist.
        """
        uri = self._locator.subscriptions_uri(device_id, self.FORMAT)
        return self._client.GET(uri)

    def put_subscriptions(self, device_id, urls):
        """Update a device's subscription list

        Sets the server-side subscription list for the device
        "device_id" to be equivalent to the URLs in the list of
        strings "urls".

        The device will be created if it does not yet exist.

        Returns True if the update was successful, False otherwise.
        """
        uri = self._locator.subscriptions_uri(device_id, self.FORMAT)
        return (self._client.PUT(uri, urls) == None)

    def get_suggestions(self, count=10):
        """Get podcast suggestions for the user

        Returns a list of Podcast objects that are
        to be suggested to the user.

        The parameter count is optional and if
        specified has to be a value between 1
        and 100 (with 10 being the default), and
        determines how much search results are
        returned (at maximum).
        """
        uri = self._locator.suggestions_uri(count, self.FORMAT)
        return [Podcast.from_dict(x) for x in self._client.GET(uri)]

