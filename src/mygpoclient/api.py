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

from mygpoclient import util
from mygpoclient import simple

# Additional error types for the advanced API client
class InvalidResponse(Exception): pass


class UpdateResult(object):
    """Container for subscription update results

    Attributes:
    update_urls - A list of (old_url, new_url) tuples
    since - A timestamp value for use in future requests
    """
    def __init__(self, update_urls, since):
        self.update_urls = update_urls
        self.since = since

class SubscriptionChanges(object):
    """Container for subscription changes

    Attributes:
    add - A list of URLs that have been added
    remove - A list of URLs that have been removed
    since - A timestamp value for use in future requests
    """
    def __init__(self, add, remove, since):
        self.add = add
        self.remove = remove
        self.since = since

class EpisodeActionChanges(object):
    """Container for added episode actions

    Attributes:
    actions - A list of EpisodeAction objects
    since - A timestamp value for use in future requests
    """
    def __init__(self, actions, since):
        self.actions = actions
        self.since = since

class PodcastDevice(object):
    """This class encapsulates a podcast device

    Attributes:
    device_id - The ID used to refer to this device
    caption - A user-defined "name" for this device
    type - A valid type of podcast device (see VALID_TYPES)
    subscriptions - The number of podcasts this device is subscribed to
    """
    VALID_TYPES = ('desktop', 'laptop', 'mobile', 'server', 'other')

    def __init__(self, device_id, caption, type, subscriptions):
        # Check if the device type is valid
        if type not in self.VALID_TYPES:
            raise ValueError('Invalid device type "%s" (see VALID_TYPES)' % type)

        # Check if subsciptions is a numeric value
        try:
            int(subscriptions)
        except:
            raise ValueError('Subscription must be a numeric value but was %s' % subscriptions)

        self.device_id = device_id
        self.caption = caption
        self.type = type
        self.subscriptions = int(subscriptions)

    def __str__(self):
        """String representation of this device

        >>> device = PodcastDevice('mygpo', 'My Device', 'mobile', 10)
        >>> print device
        PodcastDevice('mygpo', 'My Device', 'mobile', 10)
        """
        return '%s(%r, %r, %r, %r)' % (self.__class__.__name__,
                self.device_id, self.caption, self.type, self.subscriptions)

    @classmethod
    def from_dictionary(cls, d):
        return cls(d['id'], d['caption'], d['type'], d['subscriptions'])

class EpisodeAction(object):
    """This class encapsulates an episode action

    The mandatory attributes are:
    podcast - The feed URL of the podcast
    episode - The enclosure URL or GUID of the episode
    action - One of 'download', 'play', 'delete' or 'new'

    The optional attributes are:
    device - The device_id on which the action has taken place
    timestamp - When the action took place (in XML time format)
    started - The start time of a play event in seconds
    position - The current position of a play event in seconds
    total - The total time of the episode (for play events)

    The attribute "position" is only valid for "play" action types.
    """
    VALID_ACTIONS = ('download', 'play', 'delete', 'new')

    def __init__(self, podcast, episode, action,
            device=None, timestamp=None,
            started=None, position=None, total=None):
        # Check if the action is valid
        if action not in self.VALID_ACTIONS:
            raise ValueError('Invalid action type "%s" (see VALID_TYPES)' % action)

        # Disallow play-only attributes for non-play actions
        if action != 'play':
            if started is not None:
                raise ValueError('Started can only be set for the "play" action')
            elif position is not None:
                raise ValueError('Position can only be set for the "play" action')
            elif total is not None:
                raise ValueError('Total can only be set for the "play" action')

        # Check the format of the timestamp value
        if timestamp is not None:
            if util.iso8601_to_datetime(timestamp) is None:
                raise ValueError('Timestamp has to be in ISO 8601 format but was %s' % timestamp)

        # Check if we have a "position" value if we have started or total
        if position is None and (started is not None or total is not None):
            raise ValueError('Started or total set, but no position given')

        # Check that "started" is a number if it's set
        if started is not None:
            try:
                started = int(started)
            except ValueError:
                raise ValueError('Started must be an integer value (seconds) but was %s' % started)

        # Check that "position" is a number if it's set
        if position is not None:
            try:
                position = int(position)
            except ValueError:
                raise ValueError('Position must be an integer value (seconds) but was %s' % position)

        # Check that "total" is a number if it's set
        if total is not None:
            try:
                total = int(total)
            except ValueError:
                raise ValueError('Total must be an integer value (seconds) but was %s' % total)

        self.podcast = podcast
        self.episode = episode
        self.action = action
        self.device = device
        self.timestamp = timestamp
        self.started = started
        self.position = position
        self.total = total

    @classmethod
    def from_dictionary(cls, d):
        return cls(d['podcast'], d['episode'], d['action'],
                   d.get('device'), d.get('timestamp'),
                   d.get('started'), d.get('position'), d.get('total'))

    def to_dictionary(self):
        d = {}

        for mandatory in ('podcast', 'episode', 'action'):
            value = getattr(self, mandatory)
            d[mandatory] = value

        for optional in ('device', 'timestamp',
                'started', 'position', 'total'):
            value = getattr(self, optional)
            if value is not None:
                d[optional] = value

        return d


class MygPodderClient(simple.SimpleClient):
    """gpodder.net API Client

    This is the API client that implements both the Simple and
    Advanced API of gpodder.net. See the SimpleClient class
    for a smaller class that only implements the Simple API.
    """

    def get_subscriptions(self, device):
        # Overloaded to accept PodcastDevice objects as arguments
        device = getattr(device, 'device_id', device)
        return simple.SimpleClient.get_subscriptions(self, device)

    def put_subscriptions(self, device, urls):
        # Overloaded to accept PodcastDevice objects as arguments
        device = getattr(device, 'device_id', device)
        return simple.SimpleClient.put_subscriptions(self, device, urls)

    def update_subscriptions(self, device_id, add_urls=[], remove_urls=[]):
        """Update the subscription list for a given device.

        Returns a UpdateResult object that contains a list of (sanitized)
        URLs and a "since" value that can be used for future calls to
        pull_subscriptions.

        For every (old_url, new_url) tuple in the updated_urls list of
        the resulting object, the client should rewrite the URL in its
        subscription list so that new_url is used instead of old_url.
        """
        uri = self._locator.add_remove_subscriptions_uri(device_id)

        if not all(isinstance(x, basestring) for x in add_urls):
            raise ValueError('add_urls must be a list of strings but was %s' % add_urls)

        if not all(isinstance(x, basestring) for x in remove_urls):
            raise ValueError('remove_urls must be a list of strings but was %s' % remove_urls)

        data = {'add': add_urls, 'remove': remove_urls}
        response = self._client.POST(uri, data)

        if response is None:
            raise InvalidResponse('Got empty response')

        if 'timestamp' not in response:
            raise InvalidResponse('Response does not contain timestamp')

        try:
            since = int(response['timestamp'])
        except ValueError:
            raise InvalidResponse('Invalid value %s for timestamp in response' % response['timestamp'])

        if 'update_urls' not in response:
            raise InvalidResponse('Response does not contain update_urls')

        try:
            update_urls = [(a, b) for a, b in response['update_urls']]
        except:
            raise InvalidResponse('Invalid format of update_urls in response: %s' % response['update_urls'])

        if not all(isinstance(a, basestring) and isinstance(b, basestring) \
                    for a, b in update_urls):
            raise InvalidResponse('Invalid format of update_urls in response: %s' % update_urls)

        return UpdateResult(update_urls, since)

    def pull_subscriptions(self, device_id, since=None):
        """Downloads subscriptions since the time of the last update

        The "since" parameter should be a timestamp that has been
        retrieved previously by a call to update_subscriptions or
        pull_subscriptions.

        Returns a SubscriptionChanges object with two lists (one for
        added and one for removed podcast URLs) and a "since" value
        that can be used for future calls to this method.
        """
        uri = self._locator.subscription_updates_uri(device_id, since)
        data = self._client.GET(uri)

        if data is None:
            raise InvalidResponse('Got empty response')

        if 'add' not in data:
            raise InvalidResponse('List of added podcasts not in response')

        if 'remove' not in data:
            raise InvalidResponse('List of removed podcasts not in response')

        if 'timestamp' not in data:
            raise InvalidResponse('Timestamp missing from response')

        if not all(isinstance(x, basestring) for x in data['add']):
            raise InvalidResponse('Invalid value(s) in list of added podcasts: %s' % data['add'])

        if not all(isinstance(x, basestring) for x in data['remove']):
            raise InvalidResponse('Invalid value(s) in list of removed podcasts: %s' % data['remove'])

        try:
            since = int(data['timestamp'])
        except ValueError:
            raise InvalidResponse('Timestamp has invalid format in response: %s' % data['timestamp'])

        return SubscriptionChanges(data['add'], data['remove'], since)

    def upload_episode_actions(self, actions=[]):
        """Uploads a list of EpisodeAction objects to the server

        Returns the timestamp that can be used for retrieving changes.
        """
        uri = self._locator.upload_episode_actions_uri()
        actions = [action.to_dictionary() for action in actions]
        response = self._client.POST(uri, actions)

        if response is None:
            raise InvalidResponse('Got empty response')

        if 'timestamp' not in response:
            raise InvalidResponse('Response does not contain timestamp')

        try:
            since = int(response['timestamp'])
        except ValueError:
            raise InvalidResponse('Invalid value %s for timestamp in response' % response['timestamp'])

        return since

    def download_episode_actions(self, since=None,
            podcast=None, device_id=None):
        """Downloads a list of EpisodeAction objects from the server

        Returns a EpisodeActionChanges object with the list of
        new actions and a "since" timestamp that can be used for
        future calls to this method when retrieving episodes.
        """
        uri = self._locator.download_episode_actions_uri(since,
                podcast, device_id)
        data = self._client.GET(uri)

        if data is None:
            raise InvalidResponse('Got empty response')

        if 'actions' not in data:
            raise InvalidResponse('Response does not contain actions')

        if 'timestamp' not in data:
            raise InvalidResponse('Response does not contain timestamp')

        try:
            since = int(data['timestamp'])
        except ValueError:
            raise InvalidResponse('Invalid value for timestamp: ' +
                    data['timestamp'])

        dicts = data['actions']
        try:
            actions = [EpisodeAction.from_dictionary(d) for d in dicts]
        except KeyError:
            raise InvalidResponse('Missing keys in action list response')

        return EpisodeActionChanges(actions, since)

    def update_device_settings(self, device_id, caption=None, type=None):
        """Update the description of a device on the server

        This changes the caption and/or type of a given device
        on the server. If the device does not exist, it is
        created with the given settings.

        The parameters caption and type are both optional and
        when set to a value other than None will be used to
        update the device settings.

        Returns True if the request succeeded, False otherwise.
        """
        uri = self._locator.device_settings_uri(device_id)
        data = {}
        if caption is not None:
            data['caption'] = caption
        if type is not None:
            data['type'] = type
        return (self._client.POST(uri, data) is None)

    def get_devices(self):
        """Returns a list of this user's PodcastDevice objects

        The resulting list can be used to display a selection
        list to the user or to determine device IDs to pull
        the subscription list from.
        """
        uri = self._locator.device_list_uri()
        dicts = self._client.GET(uri)
        if dicts is None:
            raise InvalidResponse('No response received')

        try:
            return [PodcastDevice.from_dictionary(d) for d in dicts]
        except KeyError:
            raise InvalidResponse('Missing keys in device list response')


