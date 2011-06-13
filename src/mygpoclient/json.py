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

# Fix gPodder bug 900 (so "import json" doesn't import this module)
from __future__ import absolute_import

import mygpoclient

try:
    # Prefer the usage of the simplejson module, as it
    # is most likely newer if it's installed as module
    # than the built-in json module (and is mandatory
    # in Python versions before 2.6, anyway).
    import simplejson as json
except ImportError:
    # Python 2.6 ships the "json" module by default
    import json

from mygpoclient import http

# Additional exceptions for JSON-related errors
class JsonException(Exception): pass

class JsonClient(http.HttpClient):
    """A HttpClient with built-in JSON support

    This client will automatically marshal and unmarshal data for
    JSON-related web services so that code using this class will
    not need to care about (de-)serialization of data structures.
    """
    def __init__(self, username=None, password=None):
        http.HttpClient.__init__(self, username, password)

    @staticmethod
    def encode(data):
        """Encodes a object into its JSON string repesentation

        >>> JsonClient.encode(None)
        ''
        >>> JsonClient.encode([1,2,3])
        '[1, 2, 3]'
        >>> JsonClient.encode(42)
        '42'
        """
        if data is None:
            return ''
        else:
            return json.dumps(data)

    @staticmethod
    def decode(data):
        """Decodes a response string to a Python object

        >>> JsonClient.decode('')
        >>> JsonClient.decode('[1,2,3]')
        [1, 2, 3]
        >>> JsonClient.decode('42')
        42
        """
        if data == '':
            return None
        else:
            try:
                return json.loads(data)
            except ValueError, ve:
                raise JsonException('Value error while parsing response: ' + data)

    @staticmethod
    def _prepare_request(method, uri, data):
        data = JsonClient.encode(data)
        return http.HttpClient._prepare_request(method, uri, data)

    @staticmethod
    def _process_response(response):
        data = http.HttpClient._process_response(response)
        return JsonClient.decode(data)
