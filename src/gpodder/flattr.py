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


#
#  flattr.py -- gPodder Flattr integration
#  Bernd Schlapsi <brot@gmx.info>   2012-05-26
#

import atexit
import os
import urllib
import urllib2
import urlparse
import json

import logging
logger = logging.getLogger(__name__)

from gpodder import minidb
from gpodder import util

import gpodder

_ = gpodder.gettext


class FlattrAction(object):
    __slots__ = {'url': str}

    def __init__(self, url):
        self.url = url


class Flattr(object):
    STORE_FILE = 'flattr.cache'

    KEY = 'DD2bUSu1TJ7voHz9yNgtC7ld54lKg29Kw2MhL68uG5QUCgT1UZkmXvpSqBtxut7R'
    SECRET = 'lJYWGXhcTXWm4FdOvn0iJg1ZIkm3DkKPTzCpmJs5xehrKk55yWe736XCg9vKj5p3'

    CALLBACK = 'http://gpodder.org/flattr/token.html'
    GPODDER_THING = ('https://flattr.com/submit/auto?' +
            'user_id=thp&url=http://gpodder.org/')

    # OAuth URLs
    OAUTH_BASE = 'https://flattr.com/oauth'
    AUTH_URL_TEMPLATE = (OAUTH_BASE + '/authorize?scope=flattr&' +
            'response_type=code&client_id=%(client_id)s&' +
            'redirect_uri=%(redirect_uri)s')
    OAUTH_TOKEN_URL = OAUTH_BASE + '/token'

    # REST API URLs
    API_BASE = 'https://api.flattr.com/rest/v2'
    USER_INFO_URL = API_BASE + '/user'
    FLATTR_URL = API_BASE + '/flattr'
    THING_INFO_URL_TEMPLATE = API_BASE + '/things/lookup/?url=%(url)s'

    def __init__(self, config):
        self._config = config

        self._store = minidb.Store(os.path.join(gpodder.home, self.STORE_FILE))
        self._worker_thread = None
        atexit.register(self._at_exit)
        
    def _at_exit(self):
        self._worker_proc()
        self._store.close()
        
    def _worker_proc(self):
        self._store.commit()        
        if not self.api_reachable():
            self._worker_thread = None
            return
        
        logger.debug('Processing stored flattr actions...')        
        for flattr_action in self._store.load(FlattrAction):
            success, message = self.flattr_url(flattr_action.url)
            if success:
                self._store.remove(flattr_action)
        self._store.commit()
        self._worker_thread = None
        
    def api_reachable(self):
        reachable, response = util.website_reachable(self.API_BASE)
        if not reachable:
            return False
            
        try:
            content = response.readline()
            content = json.loads(content)
            if 'message' in content and content['message'] == 'hello_world':
                return True
        except ValueError as err:
            pass

        return False

    def request(self, url, data=None):
        headers = {'Content-Type': 'application/json'}

        if url == self.OAUTH_TOKEN_URL:
            # Inject username and password into the request URL
            url = util.url_add_authentication(url, self.KEY, self.SECRET)
        elif self._config.token:
            headers['Authorization'] = 'Bearer ' + self._config.token

        if data is not None:
            data = json.dumps(data)

        try:
            response = util.urlopen(url, headers, data)
        except urllib2.HTTPError, error:
            return {'_gpodder_statuscode': error.getcode()}
        except urllib2.URLError, error:
            return {'_gpodder_no_connection': False}

        if response.getcode() == 200:
            return json.loads(response.read())

        return {'_gpodder_statuscode': response.getcode()}

    def get_auth_url(self):
        return self.AUTH_URL_TEMPLATE % {
                'client_id': self.KEY,
                'redirect_uri': self.CALLBACK,
        }

    def has_token(self):
        return bool(self._config.token)

    def process_retrieved_code(self, url):
        url_parsed = urlparse.urlparse(url)
        query = urlparse.parse_qs(url_parsed.query)

        if 'code' in query:
            code = query['code'][0]
            logger.info('Got code: %s', code)
            self._config.token = self._request_access_token(code)
            return True

        return False

    def _request_access_token(self, code):
        request_url = 'https://flattr.com/oauth/token'

        params = {
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.CALLBACK,
        }

        content = self.request(self.OAUTH_TOKEN_URL, data=params)
        return content.get('access_token', '')

    def get_thing_info(self, payment_url):
        """Get information about a Thing on Flattr

        Return a tuple (flattrs, flattred):

            flattrs ... The number of Flattrs this thing received
            flattred ... True if this user already flattred this thing
        """
        if not self._config.token:
            return (0, False)

        quote_url = urllib.quote_plus(util.sanitize_encoding(payment_url))
        url = self.THING_INFO_URL_TEMPLATE % {'url': quote_url}
        data = self.request(url)
        return (int(data.get('flattrs', 0)), bool(data.get('flattred', False)))

    def get_auth_username(self):
        if not self._config.token:
            return ''

        data = self.request(self.USER_INFO_URL)
        return data.get('username', '')

    def flattr_url(self, payment_url):
        """Flattr an object given its Flattr payment URL

        Returns a tuple (success, message):

            success ... True if the item was Flattr'd
            message ... The success or error message
        """
        params = {
            'url': payment_url
        }

        content = self.request(self.FLATTR_URL, data=params)

        if '_gpodder_statuscode' in content:
            status_code = content['_gpodder_statuscode']
            if status_code == 401:
                return (False, _('Not enough means to flattr'))
            elif status_code == 404:
                return (False, _('Item does not exist on Flattr'))
            elif status_code == 403:
                return (True, _('Already flattred or own item'))
            else:
                return (False, _('Invalid request'))
                
        if '_gpodder_no_connection' in content:
            if not self._store.get(FlattrAction, url=payment_url):
                flattr_action = FlattrAction(payment_url)
                self._store.save(flattr_action)
            return (False, _('No internet connection'))
        
        if self._worker_thread is None:        
            self._worker_thread = util.run_in_background(lambda: self._worker_proc(), True)

        return (True, content.get('description', _('No description')))

    def is_flattr_url(self, url):
        if 'flattr.com' in url:
            return True
        return False

    def is_flattrable(self, url):
        if self._config.token and self.is_flattr_url(url):
            return True
        return False
