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

import os
import urllib

from mygpoclient import util

class Locator(object):
    """URI Locator for API endpoints

    This helper class abstracts the URIs for the gpodder.net
    webservice and provides a nice facility for generating API
    URIs and checking parameters.
    """
    SIMPLE_FORMATS = ('opml', 'json', 'txt')

    def __init__(self, username, host=mygpoclient.HOST,
            version=mygpoclient.VERSION):
        self._username = username
        self._simple_base = 'http://%(host)s' % locals()
        self._base = 'http://%(host)s/api/%(version)s' % locals()

    def _convert_since(self, since):
        """Convert "since" into a numeric value

        This is internally used for value-checking.
        """
        try:
            return int(since)
        except ValueError:
            raise ValueError('since must be a numeric value (or None)')

    def subscriptions_uri(self, device_id, format='opml'):
        """Get the Simple API URI for a subscription list

        >>> locator = Locator('john')
        >>> locator.subscriptions_uri('n800')
        'http://gpodder.net/subscriptions/john/n800.opml'
        >>> locator.subscriptions_uri('ipod', 'txt')
        'http://gpodder.net/subscriptions/john/ipod.txt'
        """
        if format not in self.SIMPLE_FORMATS:
            raise ValueError('Unsupported file format')

        filename = '%(device_id)s.%(format)s' % locals()
        return util.join(self._simple_base,
                'subscriptions', self._username, filename)

    def toplist_uri(self, count=50, format='opml'):
        """Get the Simple API URI for the toplist

        >>> locator = Locator(None)
        >>> locator.toplist_uri()
        'http://gpodder.net/toplist/50.opml'
        >>> locator.toplist_uri(70)
        'http://gpodder.net/toplist/70.opml'
        >>> locator.toplist_uri(10, 'json')
        'http://gpodder.net/toplist/10.json'
        """
        if format not in self.SIMPLE_FORMATS:
            raise ValueError('Unsupported file format')

        filename = 'toplist/%(count)d.%(format)s' % locals()
        return util.join(self._simple_base, filename)

    def suggestions_uri(self, count=10, format='opml'):
        """Get the Simple API URI for user suggestions

        >>> locator = Locator('john')
        >>> locator.suggestions_uri()
        'http://gpodder.net/suggestions/10.opml'
        >>> locator.suggestions_uri(50)
        'http://gpodder.net/suggestions/50.opml'
        >>> locator.suggestions_uri(70, 'json')
        'http://gpodder.net/suggestions/70.json'
        """
        if format not in self.SIMPLE_FORMATS:
            raise ValueError('Unsupported file format')

        filename = 'suggestions/%(count)d.%(format)s' % locals()
        return util.join(self._simple_base, filename)

    def search_uri(self, query, format='opml'):
        """Get the Simple API URI for podcast search

        >>> locator = Locator(None)
        >>> locator.search_uri('outlaws')
        'http://gpodder.net/search.opml?q=outlaws'
        >>> locator.search_uri(':something?', 'txt')
        'http://gpodder.net/search.txt?q=%3Asomething%3F'
        >>> locator.search_uri('software engineering', 'json')
        'http://gpodder.net/search.json?q=software+engineering'
        """
        if format not in self.SIMPLE_FORMATS:
            raise ValueError('Unsupported file format')

        query = urllib.quote_plus(query)
        filename = 'search.%(format)s?q=%(query)s' % locals()
        return util.join(self._simple_base, filename)

    def add_remove_subscriptions_uri(self, device_id):
        """Get the Advanced API URI for uploading list diffs

        >>> locator = Locator('bill')
        >>> locator.add_remove_subscriptions_uri('n810')
        'http://gpodder.net/api/2/subscriptions/bill/n810.json'
        """
        filename = '%(device_id)s.json' % locals()
        return util.join(self._base,
                'subscriptions', self._username, filename)

    def subscription_updates_uri(self, device_id, since=None):
        """Get the Advanced API URI for downloading list diffs

        The parameter "since" is optional and should be a numeric
        value (otherwise a ValueError is raised).

        >>> locator = Locator('jen')
        >>> locator.subscription_updates_uri('n900')
        'http://gpodder.net/api/2/subscriptions/jen/n900.json'
        >>> locator.subscription_updates_uri('n900', 1234)
        'http://gpodder.net/api/2/subscriptions/jen/n900.json?since=1234'
        """
        filename = '%(device_id)s.json' % locals()
        if since is not None:
            since = self._convert_since(since)
            filename += '?since=%(since)d' % locals()

        return util.join(self._base,
                'subscriptions', self._username, filename)

    def upload_episode_actions_uri(self):
        """Get the Advanced API URI for uploading episode actions

        >>> locator = Locator('thp')
        >>> locator.upload_episode_actions_uri()
        'http://gpodder.net/api/2/episodes/thp.json'
        """
        filename = self._username + '.json'
        return util.join(self._base, 'episodes', filename)

    def download_episode_actions_uri(self, since=None,
            podcast=None, device_id=None):
        """Get the Advanced API URI for downloading episode actions

        The parameter "since" is optional and should be a numeric
        value (otherwise a ValueError is raised).

        Both "podcast" and "device_id" are optional and exclusive:

        "podcast" should be a podcast URL
        "device_id" should be a device ID

        >>> locator = Locator('steve')
        >>> locator.download_episode_actions_uri()
        'http://gpodder.net/api/2/episodes/steve.json'
        >>> locator.download_episode_actions_uri(since=1337)
        'http://gpodder.net/api/2/episodes/steve.json?since=1337'
        >>> locator.download_episode_actions_uri(podcast='http://example.org/episodes.rss')
        'http://gpodder.net/api/2/episodes/steve.json?podcast=http%3A//example.org/episodes.rss'
        >>> locator.download_episode_actions_uri(since=2000, podcast='http://example.com/')
        'http://gpodder.net/api/2/episodes/steve.json?since=2000&podcast=http%3A//example.com/'
        >>> locator.download_episode_actions_uri(device_id='ipod')
        'http://gpodder.net/api/2/episodes/steve.json?device=ipod'
        >>> locator.download_episode_actions_uri(since=54321, device_id='ipod')
        'http://gpodder.net/api/2/episodes/steve.json?since=54321&device=ipod'
        """
        if podcast is not None and device_id is not None:
            raise ValueError('must not specify both "podcast" and "device_id"')

        filename = self._username+'.json'

        params = []
        if since is not None:
            since = str(self._convert_since(since))
            params.append(('since', since))

        if podcast is not None:
            params.append(('podcast', podcast))

        if device_id is not None:
            params.append(('device', device_id))

        if params:
            filename += '?' + '&'.join('%s=%s' % (key, urllib.quote(value)) for key, value in params)

        return util.join(self._base, 'episodes', filename)

    def device_settings_uri(self, device_id):
        """Get the Advanced API URI for setting per-device settings uploads

        >>> locator = Locator('mike')
        >>> locator.device_settings_uri('ipod')
        'http://gpodder.net/api/2/devices/mike/ipod.json'
        """
        filename = '%(device_id)s.json' % locals()
        return util.join(self._base, 'devices', self._username, filename)

    def device_list_uri(self):
        """Get the Advanced API URI for retrieving the device list

        >>> locator = Locator('jeff')
        >>> locator.device_list_uri()
        'http://gpodder.net/api/2/devices/jeff.json'
        """
        filename = self._username + '.json'
        return util.join(self._base, 'devices', filename)


