# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2012 Thomas Perl and the gPodder Team
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

import json
import httplib2

import logging
logger = logging.getLogger(__name__)

KEY = '4sRHRAlZkrcYYOu7oYUfqxREmee1qJ9l1RTJh5zsnCgbgB9upTAGhiatmflDPlPG'
SECRET = '3ygatFtG8AIe1Hzgr0Nz8OTlT4Oygt59ScacHuJGUhKMPaT71wwZafaTaPih8ehQ'
CALLBACK = 'gpodder://flattr-token/'
SCOPE = 'flattr'

class Flattr(object):
    def __init__(self, config):
        self._config = config
        self.http = httplib2.Http()

    def __get_headers(self):
        headers = {'Content-Type': 'application/json'}
        if self._config.token:
            headers['Authorization'] = 'Bearer %s' % self._config.token
        return headers

    def _flattr_get_request(self, url):
        response, content = self.http.request(url, headers=self.__get_headers())        
        if response['status'] == '200':
            return json.loads(content)
        return {}
        
    def get_callback_uri(self):
        return CALLBACK
        
    def get_auth_uri(self):
        return 'https://flattr.com/oauth/authorize?scope=%s&response_type=code&client_id=%s&redirect_uri=%s' % (SCOPE, KEY, CALLBACK)
        
    def request_access_token(self, code):
        url = 'https://flattr.com/oauth/token'

        self.http.add_credentials(KEY, SECRET)
        params = {
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': CALLBACK
        }
        response, content = self.http.request(url, 'POST',
            json.dumps(params), headers={'Content-Type': 'application/json'})
        content = json.loads(content)
        if response['status'] == '200' and content.has_key('access_token'):
            return content['access_token']

        return ''

    def get_thing_info(self, url):
        uri = 'https://api.flattr.com/rest/v2/things/lookup/?url=%s' % url
        
        thingdata = self._flattr_get_request(uri)
        flattrs = int(thingdata.get('flattrs', 0))
        flattred = bool(thingdata.get('flattred', False))        

        return flattrs, flattred
        
    def get_auth_username(self):
        uri = 'https://api.flattr.com/rest/v2/user'
        
        if self._config.token:
            userdata = self._flattr_get_request(uri)    
            return userdata.get('username', '?')

        return ''
