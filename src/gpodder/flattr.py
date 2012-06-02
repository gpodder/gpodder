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

import httplib2
import json
import os.path

import logging
logger = logging.getLogger(__name__)

import gpodder

KEY = '4sRHRAlZkrcYYOu7oYUfqxREmee1qJ9l1RTJh5zsnCgbgB9upTAGhiatmflDPlPG'
SECRET = '3ygatFtG8AIe1Hzgr0Nz8OTlT4Oygt59ScacHuJGUhKMPaT71wwZafaTaPih8ehQ'
SCOPE = 'flattr'

if not gpodder.images_folder:
    gpodder.images_folder = ''

class Flattr(object):
    CALLBACK = 'gpodder://flattr-token/'
    IMAGE_FLATTR = os.path.join(gpodder.images_folder, 'button-flattr.png')
    IMAGE_FLATTR_GREY = os.path.join(gpodder.images_folder, 'button-flattr-grey.png')
    IMAGE_FLATTRED = os.path.join(gpodder.images_folder, 'button-flattred.png')

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
        
    def get_auth_url(self):
        return 'https://flattr.com/oauth/authorize?scope=%s&response_type=code&client_id=%s&redirect_uri=%s' % (SCOPE, KEY, self.CALLBACK)
        
    def request_access_token(self, code):
        request_url = 'https://flattr.com/oauth/token'

        self.http.add_credentials(KEY, SECRET)
        params = {
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.CALLBACK
        }
        response, content = self.http.request(request_url, 'POST',
            json.dumps(params), headers={'Content-Type': 'application/json'})
        content = json.loads(content)
        
        if response['status'] == '200':
            return content.get('access_token', '')

        return ''

    def get_thing_info(self, url):
        request_url = 'https://api.flattr.com/rest/v2/things/lookup/?url=%s' % url
        thingdata = {}
        
        if self._config.flattr.token:
            thingdata = self._flattr_get_request(request_url)
            
        flattrs = int(thingdata.get('flattrs', 0))
        flattred = bool(thingdata.get('flattred', None))
        return flattrs, flattred
        
    def get_auth_username(self):
        request_url = 'https://api.flattr.com/rest/v2/user'
        
        if self._config.token:
            userdata = self._flattr_get_request(request_url)    
            return userdata.get('username', '?')

        return ''

    def flattr_url(self, url):
        request_url = 'https://api.flattr.com/rest/v2/flattr'
        params = {
            'url': url
        }
        
        response, content = self.http.request(request_url, 'POST',
            json.dumps(params), headers=self.__get_headers())
        content = json.loads(content)
            
        if response['status'] == '200':
            return content.get('description', '?')
            
        elif response['status'] == '401':
            return "Current user don't have enough means to flattr"
            
        elif response['status'] == '403':
            return "The current user have already flattred the thing or the user is the owner of the thing"
            
        elif response['status'] == '403':
            return "Thing does not exist"
            
        else:
            return "Request is not valid"
