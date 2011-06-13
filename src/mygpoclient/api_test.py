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

from mygpoclient import api
from mygpoclient import testing

import unittest

# Example data for testing purposes
FEED_URL_1 = 'http://example.com/test.rss'
FEED_URL_2 = 'http://feeds.example.org/1/feed.atom'
FEED_URL_3 = 'http://example.co.uk/episodes.xml'
FEED_URL_4 = 'http://pod.cast/test.xml'

EPISODE_URL_1 = 'http://dl.example.net/episodes/one.mp3'
EPISODE_URL_2 = 'http://pod.cast.invalid/downloads/s02e04.ogg'
EPISODE_URL_3 = 'http://example.org/05-skylarking.m4v'
EPISODE_URL_4 = 'http://www.example.com/test/me_now.avi'

DEVICE_ID_1 = 'gpodder.on.my.phone'
DEVICE_ID_2 = '95dce59cf340123fa'

class Test_SubscriptionChanges(unittest.TestCase):
    ADD = [
            FEED_URL_1,
            FEED_URL_3,
    ]
    REMOVE = [
            FEED_URL_2,
            FEED_URL_4,
    ]
    SINCE = 1262101867

    def test_initSetsCorrectAttributes(self):
        changes = api.SubscriptionChanges(self.ADD, self.REMOVE, self.SINCE)
        self.assertEquals(changes.add, self.ADD)
        self.assertEquals(changes.remove, self.REMOVE)
        self.assertEquals(changes.since, self.SINCE)


class Test_EpisodeActionChanges(unittest.TestCase):
    ACTIONS = [
            api.EpisodeAction(FEED_URL_1, EPISODE_URL_1, 'download'),
            api.EpisodeAction(FEED_URL_2, EPISODE_URL_3, 'play'),
            api.EpisodeAction(FEED_URL_2, EPISODE_URL_4, 'delete'),
    ]
    SINCE = 1262102013

    def test_initSetsCorrectAttributes(self):
        changes = api.EpisodeActionChanges(self.ACTIONS, self.SINCE)
        self.assertEquals(changes.actions, self.ACTIONS)
        self.assertEquals(changes.since, self.SINCE)


class Test_PodcastDevice(unittest.TestCase):
    CAPTION = 'My Nice Device'

    def test_initSetsCorrectAttributes(self):
        device = api.PodcastDevice(DEVICE_ID_1, self.CAPTION, 'mobile', 42)
        self.assertEquals(device.device_id, DEVICE_ID_1)
        self.assertEquals(device.caption, self.CAPTION)
        self.assertEquals(device.type, 'mobile')
        self.assertEquals(device.subscriptions, 42)

    def test_invalidDeviceType_raisesValueError(self):
        self.assertRaises(ValueError,
                api.PodcastDevice, DEVICE_ID_2, self.CAPTION,
                'does-not-exist', 1337)

    def test_nonNumericSubscriptions_raisesValueError(self):
        self.assertRaises(ValueError,
                api.PodcastDevice, DEVICE_ID_1, self.CAPTION,
                'laptop', 'notanumber')


class Test_EpisodeAction(unittest.TestCase):
    XML_TIMESTAMP = '2009-12-12T09:00:00'
    VALID_STARTED = 100
    VALID_POSITION = 123
    VALID_TOTAL = 321

    def test_initSetsCorrectAttributes(self):
        action = api.EpisodeAction(FEED_URL_1, EPISODE_URL_1, 'play',
                DEVICE_ID_1, self.XML_TIMESTAMP, self.VALID_STARTED,
                self.VALID_POSITION, self.VALID_TOTAL)
        self.assertEquals(action.podcast, FEED_URL_1)
        self.assertEquals(action.episode, EPISODE_URL_1)
        self.assertEquals(action.action, 'play')
        self.assertEquals(action.device, DEVICE_ID_1)
        self.assertEquals(action.timestamp, self.XML_TIMESTAMP)
        self.assertEquals(action.started, self.VALID_STARTED)
        self.assertEquals(action.position, self.VALID_POSITION)
        self.assertEquals(action.total, self.VALID_TOTAL)

    def test_invalidAction_raisesValueError(self):
        self.assertRaises(ValueError,
                api.EpisodeAction, FEED_URL_2, EPISODE_URL_3, 'invalidaction',
                DEVICE_ID_2, self.XML_TIMESTAMP)

    def test_positionIsSetWithNoPlayAction_raisesValueError(self):
        self.assertRaises(ValueError,
                api.EpisodeAction, FEED_URL_4, EPISODE_URL_2, 'download',
                DEVICE_ID_1, self.XML_TIMESTAMP, self.VALID_POSITION)

    def test_invalidTimestampFormat_raisesValueError(self):
        self.assertRaises(ValueError,
                api.EpisodeAction, FEED_URL_3, EPISODE_URL_3, 'delete',
                DEVICE_ID_2, 'today')

    def test_invalidPositionFormat_raisesValueError(self):
        self.assertRaises(ValueError,
                api.EpisodeAction, FEED_URL_1, EPISODE_URL_4, 'play',
                DEVICE_ID_1, self.XML_TIMESTAMP, '10 minutes into the show')

    def test_toDictionary_containsMandatoryAttributes(self):
        action = api.EpisodeAction(FEED_URL_1, EPISODE_URL_1, 'play')
        dictionary = action.to_dictionary()
        self.assertEquals(len(dictionary.keys()), 3)
        self.assert_('podcast' in dictionary)
        self.assert_('episode' in dictionary)
        self.assert_('action' in dictionary)
        self.assertEquals(dictionary['podcast'], FEED_URL_1)
        self.assertEquals(dictionary['episode'], EPISODE_URL_1)
        self.assertEquals(dictionary['action'], 'play')

    def test_toDictionary_containsAllAttributes(self):
        action = api.EpisodeAction(FEED_URL_3, EPISODE_URL_4, 'play',
                DEVICE_ID_1, self.XML_TIMESTAMP, self.VALID_STARTED,
                self.VALID_POSITION, self.VALID_TOTAL)
        dictionary = action.to_dictionary()
        self.assertEquals(len(dictionary.keys()), 8)
        self.assert_('podcast' in dictionary)
        self.assert_('episode' in dictionary)
        self.assert_('action' in dictionary)
        self.assert_('device' in dictionary)
        self.assert_('timestamp' in dictionary)
        self.assert_('started' in dictionary)
        self.assert_('position' in dictionary)
        self.assert_('total' in dictionary)
        self.assertEquals(dictionary['podcast'], FEED_URL_3)
        self.assertEquals(dictionary['episode'], EPISODE_URL_4)
        self.assertEquals(dictionary['action'], 'play')
        self.assertEquals(dictionary['device'], DEVICE_ID_1)
        self.assertEquals(dictionary['timestamp'], self.XML_TIMESTAMP)
        self.assertEquals(dictionary['started'], self.VALID_STARTED)
        self.assertEquals(dictionary['position'], self.VALID_POSITION)
        self.assertEquals(dictionary['total'], self.VALID_TOTAL)


class Test_MygPodderClient(unittest.TestCase):
    ADD = [
            FEED_URL_1,
            FEED_URL_3,
    ]
    REMOVE = [
            FEED_URL_2,
            FEED_URL_4,
    ]
    ADD_REMOVE_AS_JSON_UPLOAD = {
            'add': [FEED_URL_1, FEED_URL_3],
            'remove': [FEED_URL_2, FEED_URL_4],
    }
    ACTIONS = [
            api.EpisodeAction(FEED_URL_1, EPISODE_URL_1, 'download'),
            api.EpisodeAction(FEED_URL_2, EPISODE_URL_3, 'play'),
            api.EpisodeAction(FEED_URL_2, EPISODE_URL_4, 'delete'),
    ]
    ACTIONS_AS_JSON_UPLOAD = [
            {'podcast': FEED_URL_1, 'episode': EPISODE_URL_1, 'action': 'download'},
            {'podcast': FEED_URL_2, 'episode': EPISODE_URL_3, 'action': 'play'},
            {'podcast': FEED_URL_2, 'episode': EPISODE_URL_4, 'action': 'delete'},
    ]
    USERNAME = 'user01'
    PASSWORD = 's3cret'
    SINCE = 1262103016

    def setUp(self):
        self.fake_client = testing.FakeJsonClient()
        self.client = api.MygPodderClient(self.USERNAME, self.PASSWORD,
                client_class=self.fake_client)

    def set_http_response_value(self, value):
        self.fake_client.response_value = value

    def assert_http_request_count(self, count):
        self.assertEquals(len(self.fake_client.requests), count)

    def has_put_json_data(self, data, required_method='PUT'):
        """Returns True if the FakeJsonClient has received the given data"""
        for method, uri, sent in self.fake_client.requests:
            if method == required_method:
                self.assertEquals(sent, data)
                return True

        return False

    def has_posted_json_data(self, data):
        """Same as has_put_json_data, but require a POST request"""
        return self.has_put_json_data(data, required_method='POST')

    def test_getSubscriptions_withPodcastDevice(self):
        self.set_http_response_value('[]')
        device = api.PodcastDevice('manatee', 'My Device', 'mobile', 20)
        self.assertEquals(self.client.get_subscriptions(device), [])
        self.assert_http_request_count(1)

    def test_putSubscriptions_withPodcastDevice(self):
        self.set_http_response_value('')
        device = api.PodcastDevice('manatee', 'My Device', 'mobile', 20)
        self.assertEquals(self.client.put_subscriptions(device, self.ADD), True)
        self.assert_http_request_count(1)
        self.assert_(self.has_put_json_data(self.ADD))

    def test_updateSubscriptions_raisesValueError_onInvalidAddList(self):
        self.assertRaises(ValueError,
                self.client.update_subscriptions, DEVICE_ID_2,
                [FEED_URL_1, 123, FEED_URL_3], self.REMOVE)

    def test_updateSubscriptions_raisesValueError_onInvalidRemoveList(self):
        self.assertRaises(ValueError,
                self.client.update_subscriptions, DEVICE_ID_2,
                self.ADD, [FEED_URL_2, FEED_URL_4, [1,2,3]])

    def test_updateSubscriptions_raisesInvalidResponse_onEmptyResponse(self):
        self.set_http_response_value('')
        self.assertRaises(api.InvalidResponse,
                self.client.update_subscriptions, DEVICE_ID_1,
                self.ADD, self.REMOVE)

    def test_updateSubscriptions_raisesInvalidResponse_onMissingTimestamp(self):
        self.set_http_response_value('{}')
        self.assertRaises(api.InvalidResponse,
                self.client.update_subscriptions, DEVICE_ID_1,
                self.ADD, self.REMOVE)

    def test_updateSubscriptions_raisesInvalidResponse_onInvalidTimestamp(self):
        self.set_http_response_value("""
        {"timestamp": "not gonna happen"}
        """)
        self.assertRaises(api.InvalidResponse,
                self.client.update_subscriptions, DEVICE_ID_1,
                self.ADD, self.REMOVE)

    def test_updateSubscriptions_raisesInvalidResponse_withoutUpdateUrls(self):
        self.set_http_response_value("""
        {"timestamp": 1262103016}
        """)
        self.assertRaises(api.InvalidResponse,
                self.client.update_subscriptions, DEVICE_ID_1,
                self.ADD, self.REMOVE)

    def test_updateSubscriptions_raisesInvalidResponse_withNonStringList(self):
        self.set_http_response_value("""
        {"timestamp": 1262103016, "update_urls": [
            ["http://example.com/", 2],
            [56, "http://example.org/"]
        ]}
        """)
        self.assertRaises(api.InvalidResponse,
                self.client.update_subscriptions, DEVICE_ID_2,
                self.ADD, self.REMOVE)

    def test_updateSubscriptions_raisesInvalidResponse_withInvalidList(self):
        self.set_http_response_value("""
        {"timestamp": 1262103016, "update_urls": [
            ["test", "test2", "test3"],
            ["test", "test2"]
        ]}
        """)
        self.assertRaises(api.InvalidResponse,
                self.client.update_subscriptions, DEVICE_ID_2,
                self.ADD, self.REMOVE)

    def test_updateSubscriptions_returnsUpdateResult(self):
        self.set_http_response_value("""
        {"timestamp": 1262103016, "update_urls": [
            ["http://test2.invalid/feed.rss",
             "http://test2.invalid/feed.rss"],
            ["http://x.invalid/episodes.xml?format=2",
             "http://x.invalid/episodes.xml"]
        ]}
        """)
        update_urls_expected = [
                ('http://test2.invalid/feed.rss',
                 'http://test2.invalid/feed.rss'),
                ('http://x.invalid/episodes.xml?format=2',
                 'http://x.invalid/episodes.xml'),
        ]

        result = self.client.update_subscriptions(DEVICE_ID_1,
                self.ADD, self.REMOVE)
        # result is a UpdateResult object
        self.assert_(hasattr(result, 'since'))
        self.assert_(hasattr(result, 'update_urls'))
        self.assertEquals(result.since, self.SINCE)
        self.assertEquals(result.update_urls, update_urls_expected)
        self.assert_http_request_count(1)
        self.assert_(self.has_posted_json_data(self.ADD_REMOVE_AS_JSON_UPLOAD))

    def test_pullSubscriptions_raisesInvalidResponse_onEmptyResponse(self):
        self.set_http_response_value('')
        self.assertRaises(api.InvalidResponse,
                self.client.pull_subscriptions, DEVICE_ID_2)

    def test_pullSubscriptions_raisesInvalidResponse_onMissingTimestamp(self):
        self.set_http_response_value("""
        {"add": [
            "http://example.com/test.rss",
            "http://feeds.example.org/1/feed.atom"
        ],
        "remove": [
            "http://example.co.uk/episodes.xml",
            "http://pod.cast/test.xml"
        ]}
        """)
        self.assertRaises(api.InvalidResponse,
                self.client.pull_subscriptions, DEVICE_ID_2)

    def test_pullSubscriptions_raisesInvalidResponse_onMissingAddList(self):
        self.set_http_response_value("""
        {"remove": [
            "http://example.co.uk/episodes.xml",
            "http://pod.cast/test.xml"
        ],
        "timestamp": 1262103016}
        """)
        self.assertRaises(api.InvalidResponse,
                self.client.pull_subscriptions, DEVICE_ID_2)

    def test_pullSubscriptions_raisesInvalidResponse_onMissingRemoveList(self):
        self.set_http_response_value("""
        {"add": [
            "http://example.com/test.rss",
            "http://feeds.example.org/1/feed.atom"
        ],
        "timestamp": 1262103016}
        """)
        self.assertRaises(api.InvalidResponse,
                self.client.pull_subscriptions, DEVICE_ID_2)

    def test_pullSubscriptions_raisesInvalidResponse_onInvalidTimestamp(self):
        self.set_http_response_value("""
        {"add": [
            "http://example.com/test.rss",
            "http://feeds.example.org/1/feed.atom"
        ],
        "remove": [
            "http://example.co.uk/episodes.xml",
            "http://pod.cast/test.xml"
        ],
        "timestamp": "should not work"}
        """)
        self.assertRaises(api.InvalidResponse,
                self.client.pull_subscriptions, DEVICE_ID_2)

    def test_pullSubscriptions_raisesInvalidResponse_onInvalidAddList(self):
        self.set_http_response_value("""
        {"add": [
            "http://example.com/test.rss",
            1234,
            "http://feeds.example.org/1/feed.atom"
        ],
        "remove": [
            "http://example.co.uk/episodes.xml",
            "http://pod.cast/test.xml"
        ],
        "timestamp": 1262103016}
        """)
        self.assertRaises(api.InvalidResponse,
                self.client.pull_subscriptions, DEVICE_ID_2)

    def test_pullSubscriptions_raisesInvalidResponse_onInvalidRemoveList(self):
        self.set_http_response_value("""
        {"add": [
            "http://example.com/test.rss",
            "http://feeds.example.org/1/feed.atom"
        ],
        "remove": [
            "http://example.co.uk/episodes.xml",
            ["should", "not", "work", "either"],
            "http://pod.cast/test.xml"
        ],
        "timestamp": 1262103016}
        """)
        self.assertRaises(api.InvalidResponse,
                self.client.pull_subscriptions, DEVICE_ID_2)

    def test_pullSubscriptions_returnsChangesListAndTimestamp(self):
        self.set_http_response_value("""
        {"add": [
            "http://example.com/test.rss",
            "http://feeds.example.org/1/feed.atom"
        ],
        "remove": [
            "http://example.co.uk/episodes.xml",
            "http://pod.cast/test.xml"
        ],
        "timestamp": 1262103016}
        """)
        changes = self.client.pull_subscriptions(DEVICE_ID_2)
        self.assertEquals(changes.add, [FEED_URL_1, FEED_URL_2])
        self.assertEquals(changes.remove, [FEED_URL_3, FEED_URL_4])
        self.assertEquals(changes.since, self.SINCE)
        self.assert_http_request_count(1)

    def test_uploadEpisodeActions_raisesInvalidResponse_onEmptyResponse(self):
        self.set_http_response_value('')
        self.assertRaises(api.InvalidResponse,
                self.client.upload_episode_actions, self.ACTIONS)

    def test_uploadEpisodeActions_raisesInvalidResponse_onMissingTimestamp(self):
        self.set_http_response_value('{}')
        self.assertRaises(api.InvalidResponse,
                self.client.upload_episode_actions, self.ACTIONS)

    def test_uploadEpisodeActions_raisesInvalidResponse_onInvalidTimestamp(self):
        self.set_http_response_value("""
        {"timestamp": "just nothin'.."}
        """)
        self.assertRaises(api.InvalidResponse,
                self.client.upload_episode_actions, self.ACTIONS)

    def test_uploadEpisodeActions_returnsTimestamp(self):
        self.set_http_response_value("""
        {"timestamp": 1262103016}
        """)
        result = self.client.upload_episode_actions(self.ACTIONS)
        self.assertEquals(result, self.SINCE)
        self.assert_http_request_count(1)
        self.assert_(self.has_posted_json_data(self.ACTIONS_AS_JSON_UPLOAD))

    def test_downloadEpisodeActions_raisesInvalidResponse_onEmptyResponse(self):
        self.set_http_response_value('')
        self.assertRaises(api.InvalidResponse, self.client.download_episode_actions)

    def test_downloadEpisodeActions_raisesInvalidResponse_onMissingActions(self):
        self.set_http_response_value("""
        {"timestamp": 1262103016}
        """)
        self.assertRaises(api.InvalidResponse, self.client.download_episode_actions)

    def test_downloadEpisodeActions_raisesInvalidResponse_onMissingTimestamp(self):
        self.set_http_response_value("""
        {"actions": [
            {"podcast": "a", "episode": "b", "action": "download"},
            {"podcast": "x", "episode": "y", "action": "play"}
        ]}
        """)
        self.assertRaises(api.InvalidResponse, self.client.download_episode_actions)

    def test_downloadEpisodeActions_raisesInvalidResponse_onInvalidTimestamp(self):
        self.set_http_response_value("""
        {"actions": [
            {"podcast": "a", "episode": "b", "action": "download"},
            {"podcast": "x", "episode": "y", "action": "play"}
        ], "timestamp": "right now"}
        """)
        self.assertRaises(api.InvalidResponse, self.client.download_episode_actions)

    def test_downloadEpisodeActions_raisesInvalidResponse_onIncompleteActions(self):
        self.set_http_response_value("""
        {"actions": [
            {"podcast": "a", "episode": "b", "action": "download"},
            {"podcast": "x", "episode": "y"}
        ], "timestamp": 1262103016}
        """)
        self.assertRaises(api.InvalidResponse, self.client.download_episode_actions)

    def test_downloadEpisodeActions_returnsActionList(self):
        self.set_http_response_value("""
        {"actions": [
            {"podcast": "a", "episode": "b", "action": "download"},
            {"podcast": "x", "episode": "y", "action": "play"}
        ], "timestamp": 1262103016}
        """)
        changes = self.client.download_episode_actions()
        self.assertEquals(len(changes.actions), 2)
        action1, action2 = changes.actions
        self.assertEquals(action1.podcast, 'a')
        self.assertEquals(action1.episode, 'b')
        self.assertEquals(action1.action, 'download')
        self.assertEquals(action2.podcast, 'x')
        self.assertEquals(action2.episode, 'y')
        self.assertEquals(action2.action, 'play')
        self.assertEquals(changes.since, self.SINCE)
        self.assert_http_request_count(1)

    def test_updateDeviceSettings_withNothing(self):
        self.set_http_response_value('')
        result = self.client.update_device_settings(DEVICE_ID_1)
        self.assertEquals(result, True)
        self.assert_http_request_count(1)
        self.assert_(self.has_posted_json_data({}))

    def test_updateDeviceSettings_withCaption(self):
        self.set_http_response_value('')
        result = self.client.update_device_settings(DEVICE_ID_1,
                caption='Poodonkis')
        self.assertEquals(result, True)
        self.assert_http_request_count(1)
        self.assert_(self.has_posted_json_data({'caption': 'Poodonkis'}))

    def test_updateDeviceSettings_withType(self):
        self.set_http_response_value('')
        result = self.client.update_device_settings(DEVICE_ID_1,
                type='desktop')
        self.assertEquals(result, True)
        self.assert_http_request_count(1)
        self.assert_(self.has_posted_json_data({'type': 'desktop'}))

    def test_updateDeviceSettings_withCaptionAndType(self):
        self.set_http_response_value('')
        result = self.client.update_device_settings(DEVICE_ID_1,
                'My Unit Testing Device', 'desktop')
        self.assertEquals(result, True)
        self.assert_http_request_count(1)
        self.assert_(self.has_posted_json_data({
            'caption': 'My Unit Testing Device',
            'type': 'desktop'}))

    def test_getDevices_raisesInvalidResponse_onEmptyResponse(self):
        self.set_http_response_value('')
        self.assertRaises(api.InvalidResponse, self.client.get_devices)

    def test_getDevices_raisesInvalidResponse_onMissingKeys(self):
        self.set_http_response_value("""
        [
            {"id": "gpodder.on.my.phone",
             "type": "mobile",
             "subscriptions": 42},
            {"id": "95dce59cf340123fa",
             "caption": "The Lappy",
             "subscriptions": 4711}
        ]
        """)
        self.assertRaises(api.InvalidResponse, self.client.get_devices)

    def test_getDevices_returnsDeviceList(self):
        self.set_http_response_value("""
        [
            {"id": "gpodder.on.my.phone",
             "caption": "Phone",
             "type": "mobile",
             "subscriptions": 42},
            {"id": "95dce59cf340123fa",
             "caption": "The Lappy",
             "type": "laptop",
             "subscriptions": 4711}
        ]
        """)
        devices = self.client.get_devices()
        self.assertEquals(len(devices), 2)
        device1, device2 = devices
        self.assertEquals(device1.device_id, DEVICE_ID_1)
        self.assertEquals(device1.caption, 'Phone')
        self.assertEquals(device1.type, 'mobile')
        self.assertEquals(device1.subscriptions, 42)
        self.assertEquals(device2.device_id, DEVICE_ID_2)
        self.assertEquals(device2.caption, 'The Lappy')
        self.assertEquals(device2.type, 'laptop')
        self.assertEquals(device2.subscriptions, 4711)
        self.assert_http_request_count(1)


