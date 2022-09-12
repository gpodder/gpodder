# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2022 The gPodder Team
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

from gpodder import my
from gpodder import config

import minidb
import tempfile
import json
import atexit


class PodcastMockObject(object):
    def __init__(self, url):
        self.url = url

class EpisodeMockObject(object):
    def __init__(self, podcast_url, episode_url):
        self.channel = PodcastMockObject(podcast_url)
        self.url = episode_url
        self.current_position = None
        self.current_position_updated = 0
        self.total_time = -1
        self.mark_state = None
        self.mark_is_played = None
        self.mark_is_locked = None
        self.deleted_from_disk = False
        self.on_updated_called = False

    def mark(self, state=None, is_played=None, is_locked=None):
        self.mark_state = state
        self.mark_is_played = is_played
        self.mark_is_locked = is_locked

    def save(self):
        ...

    def was_downloaded(self, and_exists=False):
        return False

    def delete_from_disk(self):
        self.deleted_from_disk = True


def test_mygpoclient(httpserver):
    # Fixture value we inject into the actions, so that the JSON request is predictable
    now_ts_string = '2022-09-16T16:16:47'
    now_ts_value = 1663345007

    # Client requests initial subscriptions for the device
    httpserver.expect_request('/api/2/subscriptions/dummy-username/unittest-device.json', query_string='since=0',
            ).respond_with_json({'add': ['https://example.org/feed2.xml'], 'remove': [], 'timestamp': 1337})

    # Client requests susbcription changes after bootstrap
    httpserver.expect_request('/api/2/subscriptions/dummy-username/unittest-device.json', query_string='since=1337',
            ).respond_with_json({'add': [], 'remove': [], 'timestamp': 1337})

    # Client requests initial episode actions for the device
    httpserver.expect_request('/api/2/episodes/dummy-username.json', query_string='since=0',
            ).respond_with_json({'actions': [
                {
                    'podcast': 'http://example.org/podcast.rss',
                    'episode': 'http://example.net/episode.mp3',
                    'device': 'some-other-device',
                    'action': 'delete',
                    'timestamp': '2022-09-16T19:00:00',
                },
                {
                    'podcast': 'http://example.org/foo.xml',
                    'episode': 'http://example.net/bar.ogg',
                    'device': 'some-other-device',
                    'action': 'play',
                    'timestamp': '2022-09-16T19:00:00',
                    'started': 0,
                    'position': 120,
                    'total': 500,
                },
            ], 'timestamp': 1337})

    # Client requests episode actions after bootstrap
    httpserver.expect_request('/api/2/episodes/dummy-username.json', query_string='since=1337',
            ).respond_with_json({'actions': [], 'timestamp': 1337})

    # Client updates device metadata after create_device()
    httpserver.expect_request('/api/2/devices/dummy-username/unittest-device.json', method='POST',
            json={'caption': 'The Unit Test Device', 'type': 'unittest'}
            ).respond_with_json({})

    # Client updates subscription list after on_subscribe()
    httpserver.expect_request('/api/2/subscriptions/dummy-username/unittest-device.json', method='POST',
            json={'add': ['http://example.com/test.rss'], 'remove': []}
            ).respond_with_json({'timestamp': 1337, 'update_urls': []})

    # Client uploads episode actions
    httpserver.expect_request('/api/2/episodes/dummy-username.json', method='POST',
            json=[
                {
                    'podcast': 'a',
                    'episode': 'b',
                    'action': 'delete',

                    'device': 'unittest-device',
                    'timestamp': now_ts_string,
                },
                {
                    'podcast': 'c',
                    'episode': 'd',
                    'action': 'download',

                    'device': 'unittest-device',
                    'timestamp': now_ts_string,
                },
                {
                    'podcast': 'e',
                    'episode': 'f',
                    'action': 'play',

                    'device': 'unittest-device',
                    'timestamp': now_ts_string,
                    'started': 0,
                    'position': 20,
                    'total': 100,
                },
                {
                    'podcast': 'g',
                    'episode': 'h',
                    'action': 'play',

                    'device': 'unittest-device',
                    'timestamp': now_ts_string,
                },
            ],
            ).respond_with_json({'timestamp': 1337, 'update_urls': []})

    with tempfile.NamedTemporaryFile() as temporary_config:
        temporary_config.write(json.dumps({
            'mygpo': {
                'enabled': True,
                'server': httpserver.url_for('/'),
                'username': 'dummy-username',
                'password': 'dummy-password',
                'device': {
                    'uid': 'unittest-device',
                    'type': 'unittest',
                    'caption': 'The Unit Test Device',
                },
            },
        }).encode())
        temporary_config.flush()

        cfg = config.Config(temporary_config.name)
        store = minidb.Store(debug=True)
        client = my.MygPoClient(cfg, store)
        client.create_device()
        client.on_subscribe(['http://example.com/test.rss'])
        client._worker_proc(forced=True)

        # Test receiving subscribe actions
        actions = list(client.get_received_actions())

        assert len(actions) == 1
        assert isinstance(actions[0], my.ReceivedSubscribeAction)
        assert actions[0].url == 'https://example.org/feed2.xml'
        assert actions[0].action_type == my.SubscribeAction.ADD

        client.confirm_received_actions(actions)

        # Test receiving episode actions
        deleted_episode = EpisodeMockObject('http://example.org/podcast.rss',
                                               'http://example.net/episode.mp3')

        played_episode = EpisodeMockObject('http://example.org/foo.xml',
                                           'http://example.net/bar.ogg')

        mocked_episodes = [
            deleted_episode,
            played_episode,
        ]

        def find_episode(podcast_url, episode_url):
            for episode in mocked_episodes:
                if episode.channel.url == podcast_url and episode.url == episode_url:
                    return episode

        def on_updated(episode):
            episode.on_updated_called = True

        client.process_episode_actions(find_episode, on_updated)

        # Test that remotely-deleted episodes are deleted locally
        assert deleted_episode.deleted_from_disk is True
        assert deleted_episode.on_updated_called is True

        # Test that play actions are merged into the local episode
        assert played_episode.mark_is_played is True
        assert played_episode.on_updated_called is True
        assert played_episode.current_position == 120
        assert played_episode.total_time == 500

        # Test signalling and uploading episode actions
        client.on_delete([EpisodeMockObject('a', 'b')])
        client.on_download([EpisodeMockObject('c', 'd')])
        client.on_playback_full(EpisodeMockObject('e', 'f'), 0, 20, 100)
        client.on_playback([EpisodeMockObject('g', 'h')])

        # Hack: Patch timestamps so they match the now_ts_string and
        # result in a predictable JSON document being uploaded
        for action in client._store.load(my.EpisodeAction):
            action.timestamp = now_ts_value
            action.save(client._store)

        # Manually run atexit handler to sync with backend
        atexit.unregister(client._at_exit)
        client._at_exit()

        httpserver.check_assertions()
