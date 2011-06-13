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

import urllib2
import cookielib
import mygpoclient

class SimpleHttpPasswordManager(urllib2.HTTPPasswordMgr):
    """Simplified password manager for urllib2

    This class always provides the username/password combination that
    is passed to it as constructor argument, independent of the realm
    or authuri that is used.
    """

    # The maximum number of authentication retries
    MAX_RETRIES = 3

    def __init__(self, username, password):
        self._username = username
        self._password = password
        self._count = 0

    def find_user_password(self, realm, authuri):
        self._count += 1
        if self._count > self.MAX_RETRIES:
            return (None, None)
        return (self._username, self._password)

class HttpRequest(urllib2.Request):
    """Request object with customizable method

    The default behaviour of urllib2.Request is unchanged:

    >>> request = HttpRequest('http://example.org/')
    >>> request.get_method()
    'GET'
    >>> request = HttpRequest('http://example.org/', data='X')
    >>> request.get_method()
    'POST'

    However, it's possible to customize the method name:

    >>> request = HttpRequest('http://example.org/', data='X')
    >>> request.set_method('PUT')
    >>> request.get_method()
    'PUT'
    """
    def set_method(self, method):
        setattr(self, '_method', method)

    def get_method(self):
        if hasattr(self, '_method'):
            return getattr(self, '_method')
        else:
            return urllib2.Request.get_method(self)


# Possible exceptions that will be raised by HttpClient
class Unauthorized(Exception): pass
class NotFound(Exception): pass
class BadRequest(Exception): pass
class UnknownResponse(Exception): pass


class HttpClient(object):
    """A comfortable HTTP client

    This class hides the gory details of the underlying HTTP protocol
    from the rest of the code by providing a simple interface for doing
    requests and handling authentication.
    """
    def __init__(self, username=None, password=None):
        self._username = username
        self._password = password
        self._cookie_jar = cookielib.CookieJar()
        cookie_handler = urllib2.HTTPCookieProcessor(self._cookie_jar)
        if username is not None and password is not None:
            password_manager = SimpleHttpPasswordManager(username, password)
            auth_handler = urllib2.HTTPBasicAuthHandler(password_manager)
            self._opener = urllib2.build_opener(auth_handler, cookie_handler)
        else:
            self._opener = urllib2.build_opener(cookie_handler)

    @staticmethod
    def _prepare_request(method, uri, data):
        """Prepares the HttpRequest object"""

        request = HttpRequest(uri, data)
        request.set_method(method)
        request.add_header('User-agent', mygpoclient.user_agent)
        return request

    @staticmethod
    def _process_response(response):
        return response.read()

    def _request(self, method, uri, data, **kwargs):
        """Request and exception handling

        Carries out a request with a given method (GET, POST, PUT) on
        a given URI with optional data (data only makes sense for POST
        and PUT requests and should be None for GET requests).
        """
        request = self._prepare_request(method, uri, data)
        try:
            response = self._opener.open(request)
        except urllib2.HTTPError, http_error:
            if http_error.code == 404:
                raise NotFound()
            elif http_error.code == 401:
                raise Unauthorized()
            elif http_error.code == 400:
                raise BadRequest()
            else:
                raise UnknownResponse(http_error.code)
        return self._process_response(response)

    def GET(self, uri):
        """Convenience method for carrying out a GET request"""
        return self._request('GET', uri, None)

    def POST(self, uri, data):
        """Convenience method for carrying out a POST request"""
        return self._request('POST', uri, data)

    def PUT(self, uri, data):
        """Convenience method for carrying out a PUT request"""
        return self._request('PUT', uri, data)

