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

from mygpoclient import json

class FakeJsonClient(object):
    """Fake implementation of a JsonClient used for testing

    Set the response using response_value and check the list
    of requests this object got using the requests list.
    """
    def __init__(self):
        self.requests = []
        self.response_value = ''

    def __call__(self, *args, **kwargs):
        """Fake a constructor for an existing object

        >>> fake_class = FakeJsonClient()
        >>> fake_object = fake_class('username', 'password')
        >>> fake_object == fake_class
        True
        """
        return self

    def _request(self, method, uri, data):
        self.requests.append((method, uri, data))
        data = json.JsonClient.encode(data)
        return json.JsonClient.decode(self.response_value)

    def GET(self, uri):
        return self._request('GET', uri, None)

    def POST(self, uri, data):
        return self._request('POST', uri, data)

    def PUT(self, uri, data):
        return self._request('PUT', uri, data)

