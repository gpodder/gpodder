#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2010 Thomas Perl and the gPodder Team
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
#  my.py -- mygpo Client Abstraction for gPodder
#  Thomas Perl <thp@gpodder.org>; 2010-01-19
#

import gpodder
_ = gpodder.gettext

import atexit
import os
import threading
import time

from gpodder.liblogger import log

from gpodder import util

# Append gPodder's user agent to mygpoclient's user agent
import mygpoclient
mygpoclient.user_agent += ' ' + gpodder.user_agent

from mygpoclient import api

try:
    import simplejson as json
except ImportError:
    import json


class Change(object):
    ADD, REMOVE = range(2)

    def __init__(self, url, change, podcast=None):
        self.url = url
        self.change = change
        self.podcast = podcast

    @property
    def description(self):
        if self.change == self.ADD:
            return _('Add %s') % self.url
        else:
            return _('Remove %s') % self.podcast.title


class Actions(object):
    NONE = 0

    SYNC_PODCASTS, \
    UPLOAD_EPISODES, \
    UPDATE_DEVICE = (1<<x for x in range(3))

class MygPoClient(object):
    CACHE_FILE = 'mygpo.queue.json'
    FLUSH_TIMEOUT = 60
    FLUSH_RETRIES = 3

    def __init__(self, config,
            on_rewrite_url=lambda old_url, new_url: None,
            on_add_remove_podcasts=lambda add_urls, remove_urls: None,
            on_send_full_subscriptions=lambda: None):
        self._cache = {'actions': Actions.NONE,
                       'add_podcasts': [],
                       'remove_podcasts': [],
                       'episodes': []}

        self._config = config
        self._client = None

        # Callback for actions that need to be handled by the UI frontend
        self._on_rewrite_url = on_rewrite_url
        self._on_add_remove_podcasts = on_add_remove_podcasts
        self._on_send_full_subscriptions = on_send_full_subscriptions

        # Initialize the _client attribute and register with config
        self.on_config_changed('mygpo_username')
        assert self._client is not None
        self._config.add_observer(self.on_config_changed)

        # Initialize and load the local queue
        self._cache_file = os.path.join(gpodder.home, self.CACHE_FILE)
        try:
            self._cache = json.loads(open(self._cache_file).read())
        except Exception, e:
            log('Cannot read cache file: %s', str(e), sender=self)

        self._worker_thread = None
        atexit.register(self._at_exit)

        # Do the initial flush (in case any actions are queued)
        self.flush()

    def can_access_webservice(self):
        return self._config.mygpo_enabled and self._config.mygpo_device_uid

    def schedule_podcast_sync(self):
        log('Scheduling podcast list sync', sender=self)
        self.schedule(Actions.SYNC_PODCASTS)

    def request_podcast_lists_in_cache(self):
        if 'add_podcasts' not in self._cache:
            self._cache['add_podcasts'] = []
        if 'remove_podcasts' not in self._cache:
            self._cache['remove_podcasts'] = []

    def force_fresh_upload(self):
        self._on_send_full_subscriptions()

    def set_subscriptions(self, urls):
        log('Uploading (overwriting) subscriptions...')
        self._client.put_subscriptions(self._config.mygpo_device_uid, urls)
        log('Subscription upload done.')

    def on_subscribe(self, urls):
        self.request_podcast_lists_in_cache()
        self._cache['add_podcasts'].extend(urls)
        for url in urls:
            if url in self._cache['remove_podcasts']:
                self._cache['remove_podcasts'].remove(url)
        self.schedule(Actions.SYNC_PODCASTS)
        self.flush()

    def on_unsubscribe(self, urls):
        self.request_podcast_lists_in_cache()
        self._cache['remove_podcasts'].extend(urls)
        for url in urls:
            if url in self._cache['add_podcasts']:
                self._cache['add_podcasts'].remove(url)
        self.schedule(Actions.SYNC_PODCASTS)
        self.flush()

    @property
    def actions(self):
        return self._cache.get('actions', Actions.NONE)

    def _at_exit(self):
        self._worker_proc(forced=True)

    def _worker_proc(self, forced=False):
        if not forced:
            log('Worker thread waiting for timeout', sender=self)
            time.sleep(self.FLUSH_TIMEOUT)

        # Only work when enabled, UID set and allowed to work
        if self.can_access_webservice() and \
                (self._worker_thread is not None or forced):
            self._worker_thread = None
            log('Worker thread starting to work...', sender=self)
            for retry in range(self.FLUSH_RETRIES):
                if retry:
                    log('Retrying flush queue...', sender=self)

                # Update the device first, so it can be created if new
                if self.actions & Actions.UPDATE_DEVICE:
                    self.update_device()

                if self.actions & Actions.SYNC_PODCASTS:
                    self.synchronize_subscriptions()

                if self.actions & Actions.UPLOAD_EPISODES:
                    # TODO: Upload episode actions
                    pass

                if not self.actions:
                    # No more pending actions. Ready to quit.
                    break

            log('Flush completed (result: %d)', self.actions, sender=self)
            self._dump_cache_to_file()

    def _dump_cache_to_file(self):
        try:
            fp = open(self._cache_file, 'w')
            fp.write(json.dumps(self._cache))
            fp.close()
            # FIXME: Atomic file write would be nice ;)
        except Exception, e:
            log('Cannot dump cache to file: %s', str(e), sender=self)

    def flush(self):
        if not self.actions:
            return

        if self._worker_thread is None:
            self._worker_thread = threading.Thread(target=self._worker_proc)
            self._worker_thread.setDaemon(True)
            self._worker_thread.start()
        else:
            log('Flush already queued', sender=self)

    def schedule(self, action):
        if 'actions' not in self._cache:
            self._cache['actions'] = 0

        self._cache['actions'] |= action
        self.flush()

    def done(self, action):
        if 'actions' not in self._cache:
            self._cache['actions'] = 0

        if action == Actions.SYNC_PODCASTS:
            self._cache['add_podcasts'] = []
            self._cache['remove_podcasts'] = []

        self._cache['actions'] &= ~action

    def on_config_changed(self, name=None, old_value=None, new_value=None):
        if name in ('mygpo_username', 'mygpo_password', 'mygpo_server'):
            self._client = api.MygPodderClient(self._config.mygpo_username,
                    self._config.mygpo_password, self._config.mygpo_server)
            log('Reloading settings.', sender=self)
        elif name.startswith('mygpo_device_'):
            self.schedule(Actions.UPDATE_DEVICE)
            if name == 'mygpo_device_uid':
                # Reset everything because we have a new device ID
                threading.Thread(target=self.force_fresh_upload).start()
                self._cache['podcasts_since'] = 0

    def synchronize_subscriptions(self):
        try:
            device_id = self._config.mygpo_device_uid
            since = self._cache.get('podcasts_since', 0)

            # Step 1: Pull updates from the server and notify the frontend
            result = self._client.pull_subscriptions(device_id, since)
            self._cache['podcasts_since'] = result.since
            if result.add or result.remove:
                log('Changes from server: add %d, remove %d', \
                        len(result.add), \
                        len(result.remove), \
                        sender=self)
                self._on_add_remove_podcasts(result.add, result.remove)

            # Step 2: Push updates to the server and rewrite URLs (if any)
            add = list(set(self._cache.get('add_podcasts', [])))
            remove = list(set(self._cache.get('remove_podcasts', [])))
            if add or remove:
                # Only do a push request if something has changed
                result = self._client.update_subscriptions(device_id, add, remove)
                self._cache['podcasts_since'] = result.since

                for old_url, new_url in result.update_urls:
                    if new_url:
                        log('URL %s rewritten: %s', old_url, new_url, sender=self)
                        self._on_rewrite_url(old_url, new_url)

            self.done(Actions.SYNC_PODCASTS)
            return True
        except Exception, e:
            log('Cannot upload subscriptions: %s', str(e), sender=self, traceback=True)
            return False

    def update_device(self):
        try:
            log('Uploading device settings...', sender=self)
            uid = self._config.mygpo_device_uid
            caption = self._config.mygpo_device_caption
            device_type = self._config.mygpo_device_type
            self._client.update_device_settings(uid, caption, device_type)
            log('Device settings uploaded.', sender=self)
            self.done(Actions.UPDATE_DEVICE)
            return True
        except Exception, e:
            log('Cannot update device %s: %s', uid, str(e), sender=self, traceback=True)
            return False

    def get_devices(self):
        result = []
        for d in self._client.get_devices():
            result.append((d.device_id, d.caption, d.type))
        return result

    def open_website(self):
        util.open_website('http://' + self._config.mygpo_server)

