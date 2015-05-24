#!/usr/bin/python
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
#  my.py -- mygpo Client Abstraction for gPodder
#  Thomas Perl <thp@gpodder.org>; 2010-01-19
#

import gpodder
_ = gpodder.gettext

import atexit
import datetime
import calendar
import os
import sys
import time

import logging
logger = logging.getLogger(__name__)

from gpodder import util
from gpodder import minidb

# Append gPodder's user agent to mygpoclient's user agent
import mygpoclient
mygpoclient.user_agent += ' ' + gpodder.user_agent

# 2013-02-08: We should update this to 1.7 once we use the new features
MYGPOCLIENT_REQUIRED = '1.4'

if not hasattr(mygpoclient, 'require_version') or \
        not mygpoclient.require_version(MYGPOCLIENT_REQUIRED):
    print >>sys.stderr, """
    Please upgrade your mygpoclient library.
    See http://thp.io/2010/mygpoclient/

    Required version:  %s
    Installed version: %s
    """ % (MYGPOCLIENT_REQUIRED, mygpoclient.__version__)
    sys.exit(1)

try:
    from mygpoclient.simple import MissingCredentials

except ImportError:
    # if MissingCredentials does not yet exist in the installed version of
    # mygpoclient, we use an object that can never be raised/caught
    MissingCredentials = object()


from mygpoclient import api
from mygpoclient import public

from mygpoclient import util as mygpoutil

EPISODE_ACTIONS_BATCH_SIZE=100

# Database model classes
class SinceValue(object):
    __slots__ = {'host': str, 'device_id': str, 'category': int, 'since': int}

    # Possible values for the "category" field
    PODCASTS, EPISODES = range(2)

    def __init__(self, host, device_id, category, since=0):
        self.host = host
        self.device_id = device_id
        self.category = category
        self.since = since

class SubscribeAction(object):
    __slots__ = {'action_type': int, 'url': str}

    # Possible values for the "action_type" field
    ADD, REMOVE = range(2)

    def __init__(self, action_type, url):
        self.action_type = action_type
        self.url = url

    @property
    def is_add(self):
        return self.action_type == self.ADD

    @property
    def is_remove(self):
        return self.action_type == self.REMOVE

    @classmethod
    def add(cls, url):
        return cls(cls.ADD, url)

    @classmethod
    def remove(cls, url):
        return cls(cls.REMOVE, url)

    @classmethod
    def undo(cls, action):
        if action.is_add:
            return cls(cls.REMOVE, action.url)
        elif action.is_remove:
            return cls(cls.ADD, action.url)

        raise ValueError('Cannot undo action: %r' % action)

# New entity name for "received" actions
class ReceivedSubscribeAction(SubscribeAction): pass

class UpdateDeviceAction(object):
    __slots__ = {'device_id': str, 'caption': str, 'device_type': str}

    def __init__(self, device_id, caption, device_type):
        self.device_id = device_id
        self.caption = caption
        self.device_type = device_type

class EpisodeAction(object):
    __slots__ = {'podcast_url': str, 'episode_url': str, 'device_id': str,
                 'action': str, 'timestamp': int,
                 'started': int, 'position': int, 'total': int}

    def __init__(self, podcast_url, episode_url, device_id, \
            action, timestamp, started, position, total):
        self.podcast_url = podcast_url
        self.episode_url = episode_url
        self.device_id = device_id
        self.action = action
        self.timestamp = timestamp
        self.started = started
        self.position = position
        self.total = total

# New entity name for "received" actions
class ReceivedEpisodeAction(EpisodeAction): pass

class RewrittenUrl(object):
    __slots__ = {'old_url': str, 'new_url': str}

    def __init__(self, old_url, new_url):
        self.old_url = old_url
        self.new_url = new_url
# End Database model classes



# Helper class for displaying changes in the UI
class Change(object):
    def __init__(self, action, podcast=None):
        self.action = action
        self.podcast = podcast

    @property
    def description(self):
        if self.action.is_add:
            return _('Add %s') % self.action.url
        else:
            return _('Remove %s') % self.podcast.title


class MygPoClient(object):
    STORE_FILE = 'gpodder.net'
    FLUSH_TIMEOUT = 60
    FLUSH_RETRIES = 3

    def __init__(self, config):
        self._store = minidb.Store(os.path.join(gpodder.home, self.STORE_FILE))

        self._config = config
        self._client = None

        # Initialize the _client attribute and register with config
        self.on_config_changed()
        assert self._client is not None

        self._config.add_observer(self.on_config_changed)

        self._worker_thread = None
        atexit.register(self._at_exit)

    def create_device(self):
        """Uploads the device changes to the server

        This should be called when device settings change
        or when the mygpo client functionality is enabled.
        """
        # Remove all previous device update actions
        self._store.remove(self._store.load(UpdateDeviceAction))

        # Insert our new update action
        action = UpdateDeviceAction(self.device_id, \
                self._config.mygpo.device.caption, \
                self._config.mygpo.device.type)
        self._store.save(action)

    def get_rewritten_urls(self):
        """Returns a list of rewritten URLs for uploads

        This should be called regularly. Every object returned
        should be merged into the database, and the old_url
        should be updated to new_url in every podcdast.
        """
        rewritten_urls = self._store.load(RewrittenUrl)
        self._store.remove(rewritten_urls)
        return rewritten_urls

    def process_episode_actions(self, find_episode, on_updated=None):
        """Process received episode actions

        The parameter "find_episode" should be a function accepting
        two parameters (podcast_url and episode_url). It will be used
        to get an episode object that needs to be updated. It should
        return None if the requested episode does not exist.

        The optional callback "on_updated" should accept a single
        parameter (the episode object) and will be called whenever
        the episode data is changed in some way.
        """
        logger.debug('Processing received episode actions...')
        for action in self._store.load(ReceivedEpisodeAction):
            if action.action not in ('play', 'delete'):
                # Ignore all other action types for now
                continue

            episode = find_episode(action.podcast_url, action.episode_url)

            if episode is None:
                # The episode does not exist on this client
                continue

            if action.action == 'play':
                logger.debug('Play action for %s', episode.url)
                episode.mark(is_played=True)

                if (action.timestamp > episode.current_position_updated and
                        action.position is not None):
                    logger.debug('Updating position for %s', episode.url)
                    episode.current_position = action.position
                    episode.current_position_updated = action.timestamp

                if action.total:
                    logger.debug('Updating total time for %s', episode.url)
                    episode.total_time = action.total

                episode.save()
                if on_updated is not None:
                    on_updated(episode)
            elif action.action == 'delete':
                if not episode.was_downloaded(and_exists=True):
                    # Set the episode to a "deleted" state
                    logger.debug('Marking as deleted: %s', episode.url)
                    episode.delete_from_disk()
                    episode.save()
                    if on_updated is not None:
                        on_updated(episode)

        # Remove all received episode actions
        self._store.delete(ReceivedEpisodeAction)
        self._store.commit()
        logger.debug('Received episode actions processed.')

    def get_received_actions(self):
        """Returns a list of ReceivedSubscribeAction objects

        The list might be empty. All these actions have to
        be processed. The user should confirm which of these
        actions should be taken, the reest should be rejected.

        Use confirm_received_actions and reject_received_actions
        to return and finalize the actions received by this
        method in order to not receive duplicate actions.
        """
        return self._store.load(ReceivedSubscribeAction)

    def confirm_received_actions(self, actions):
        """Confirm that a list of actions has been processed

        The UI should call this with a list of actions that
        have been accepted by the user and processed by the
        podcast backend.
        """
        # Simply remove the received actions from the queue
        self._store.remove(actions)

    def reject_received_actions(self, actions):
        """Reject (undo) a list of ReceivedSubscribeAction objects

        The UI should call this with a list of actions that
        have been rejected by the user. A reversed set of
        actions will be uploaded to the server so that the
        state on the server matches the state on the client.
        """
        # Create "undo" actions for received subscriptions
        self._store.save(SubscribeAction.undo(a) for a in actions)
        self.flush()

        # After we've handled the reverse-actions, clean up
        self._store.remove(actions)

    @property
    def host(self):
        return self._config.mygpo.server

    @property
    def device_id(self):
        return self._config.mygpo.device.uid

    def can_access_webservice(self):
        return self._config.mygpo.enabled and \
               self._config.mygpo.username and \
               self._config.mygpo.device.uid

    def set_subscriptions(self, urls):
        if self.can_access_webservice():
            logger.debug('Uploading (overwriting) subscriptions...')
            self._client.put_subscriptions(self.device_id, urls)
            logger.debug('Subscription upload done.')
        else:
            raise Exception('Webservice access not enabled')

    def _convert_played_episode(self, episode, start, end, total):
        return EpisodeAction(episode.channel.url, \
                episode.url, self.device_id, 'play', \
                int(time.time()), start, end, total)

    def _convert_episode(self, episode, action):
        return EpisodeAction(episode.channel.url, \
                episode.url, self.device_id, action, \
                int(time.time()), None, None, None)

    def on_delete(self, episodes):
        logger.debug('Storing %d episode delete actions', len(episodes))
        self._store.save(self._convert_episode(e, 'delete') for e in episodes)

    def on_download(self, episodes):
        logger.debug('Storing %d episode download actions', len(episodes))
        self._store.save(self._convert_episode(e, 'download') for e in episodes)

    def on_playback_full(self, episode, start, end, total):
        logger.debug('Storing full episode playback action')
        self._store.save(self._convert_played_episode(episode, start, end, total))

    def on_playback(self, episodes):
        logger.debug('Storing %d episode playback actions', len(episodes))
        self._store.save(self._convert_episode(e, 'play') for e in episodes)

    def on_subscribe(self, urls):
        # Cancel previously-inserted "remove" actions
        self._store.remove(SubscribeAction.remove(url) for url in urls)

        # Insert new "add" actions
        self._store.save(SubscribeAction.add(url) for url in urls)

        self.flush()

    def on_unsubscribe(self, urls):
        # Cancel previously-inserted "add" actions
        self._store.remove(SubscribeAction.add(url) for url in urls)

        # Insert new "remove" actions
        self._store.save(SubscribeAction.remove(url) for url in urls)

        self.flush()

    def _at_exit(self):
        self._worker_proc(forced=True)
        self._store.commit()
        self._store.close()

    def _worker_proc(self, forced=False):
        if not forced:
            # Store the current contents of the queue database
            self._store.commit()

            logger.debug('Worker thread waiting for timeout')
            time.sleep(self.FLUSH_TIMEOUT)

        # Only work when enabled, UID set and allowed to work
        if self.can_access_webservice() and \
                (self._worker_thread is not None or forced):
            self._worker_thread = None

            logger.debug('Worker thread starting to work...')
            for retry in range(self.FLUSH_RETRIES):
                must_retry = False

                if retry:
                    logger.debug('Retrying flush queue...')

                # Update the device first, so it can be created if new
                for action in self._store.load(UpdateDeviceAction):
                    if self.update_device(action):
                        self._store.remove(action)
                    else:
                        must_retry = True

                # Upload podcast subscription actions
                actions = self._store.load(SubscribeAction)
                if self.synchronize_subscriptions(actions):
                    self._store.remove(actions)
                else:
                    must_retry = True

                # Upload episode actions
                actions = self._store.load(EpisodeAction)
                if self.synchronize_episodes(actions):
                    self._store.remove(actions)
                else:
                    must_retry = True

                if not must_retry or not self.can_access_webservice():
                    # No more pending actions, or no longer enabled.
                    # Ready to quit.
                    break

            logger.debug('Worker thread finished.')
        else:
            logger.info('Worker thread may not execute (disabled).')

        # Store the current contents of the queue database
        self._store.commit()

    def flush(self, now=False):
        if not self.can_access_webservice():
            logger.warn('Flush requested, but sync disabled.')
            return

        if self._worker_thread is None or now:
            if now:
                logger.debug('Flushing NOW.')
            else:
                logger.debug('Flush requested.')
            self._worker_thread = util.run_in_background(lambda: self._worker_proc(now), True)
        else:
            logger.debug('Flush requested, already waiting.')

    def on_config_changed(self, name=None, old_value=None, new_value=None):
        if name in ('mygpo.username', 'mygpo.password', 'mygpo.server') \
                or self._client is None:
            self._client = api.MygPodderClient(self._config.mygpo.username,
                    self._config.mygpo.password, self._config.mygpo.server)
            logger.info('Reloading settings.')
        elif name.startswith('mygpo.device.'):
            # Update or create the device
            self.create_device()

    def synchronize_episodes(self, actions):
        logger.debug('Starting episode status sync.')

        def convert_to_api(action):
            dt = datetime.datetime.utcfromtimestamp(action.timestamp)
            action_ts = mygpoutil.datetime_to_iso8601(dt)
            return api.EpisodeAction(action.podcast_url, \
                    action.episode_url, action.action, \
                    action.device_id, action_ts, \
                    action.started, action.position, action.total)

        def convert_from_api(action):
            dt = mygpoutil.iso8601_to_datetime(action.timestamp)
            action_ts = calendar.timegm(dt.timetuple())
            return ReceivedEpisodeAction(action.podcast, \
                    action.episode, action.device, \
                    action.action, action_ts, \
                    action.started, action.position, action.total)

        try:
            # Load the "since" value from the database
            since_o = self._store.get(SinceValue, host=self.host, \
                                                  device_id=self.device_id, \
                                                  category=SinceValue.EPISODES)

            # Use a default since object for the first-time case
            if since_o is None:
                since_o = SinceValue(self.host, self.device_id, SinceValue.EPISODES)

            # Step 1: Download Episode actions
            try:
                changes = self._client.download_episode_actions(since_o.since)

                received_actions = [convert_from_api(a) for a in changes.actions]
                logger.debug('Received %d episode actions', len(received_actions))
                self._store.save(received_actions)

                # Save the "since" value for later use
                self._store.update(since_o, since=changes.since)

            except (MissingCredentials, mygpoclient.http.Unauthorized):
                # handle outside
                raise

            except Exception, e:
                logger.warn('Exception while polling for episodes.', exc_info=True)

            # Step 2: Upload Episode actions

            # Uploads are done in batches; uploading can resume if only parts
            # be uploaded; avoids empty uploads as well
            for lower in range(0, len(actions), EPISODE_ACTIONS_BATCH_SIZE):
                batch = actions[lower:lower+EPISODE_ACTIONS_BATCH_SIZE]

                # Convert actions to the mygpoclient format for uploading
                episode_actions = [convert_to_api(a) for a in batch]

                # Upload the episode actions
                self._client.upload_episode_actions(episode_actions)

                # Actions have been uploaded to the server - remove them
                self._store.remove(batch)

            logger.debug('Episode actions have been uploaded to the server.')
            return True

        except (MissingCredentials, mygpoclient.http.Unauthorized):
            logger.warn('Invalid credentials. Disabling gpodder.net.')
            self._config.mygpo.enabled = False
            return False

        except Exception, e:
            logger.error('Cannot upload episode actions: %s', str(e), exc_info=True)
            return False

    def synchronize_subscriptions(self, actions):
        logger.debug('Starting subscription sync.')
        try:
            # Load the "since" value from the database
            since_o = self._store.get(SinceValue, host=self.host, \
                                                  device_id=self.device_id, \
                                                  category=SinceValue.PODCASTS)

            # Use a default since object for the first-time case
            if since_o is None:
                since_o = SinceValue(self.host, self.device_id, SinceValue.PODCASTS)

            # Step 1: Pull updates from the server and notify the frontend
            result = self._client.pull_subscriptions(self.device_id, since_o.since)

            # Update the "since" value in the database
            self._store.update(since_o, since=result.since)

            # Store received actions for later retrieval (and in case we
            # have outdated actions in the database, simply remove them)
            for url in result.add:
                logger.debug('Received add action: %s', url)
                self._store.remove(ReceivedSubscribeAction.remove(url))
                self._store.remove(ReceivedSubscribeAction.add(url))
                self._store.save(ReceivedSubscribeAction.add(url))
            for url in result.remove:
                logger.debug('Received remove action: %s', url)
                self._store.remove(ReceivedSubscribeAction.add(url))
                self._store.remove(ReceivedSubscribeAction.remove(url))
                self._store.save(ReceivedSubscribeAction.remove(url))

            # Step 2: Push updates to the server and rewrite URLs (if any)
            actions = self._store.load(SubscribeAction)

            add = [a.url for a in actions if a.is_add]
            remove = [a.url for a in actions if a.is_remove]

            if add or remove:
                logger.debug('Uploading: +%d / -%d', len(add), len(remove))
                # Only do a push request if something has changed
                result = self._client.update_subscriptions(self.device_id, add, remove)

                # Update the "since" value in the database
                self._store.update(since_o, since=result.since)

                # Store URL rewrites for later retrieval by GUI
                for old_url, new_url in result.update_urls:
                    if new_url:
                        logger.debug('Rewritten URL: %s', new_url)
                        self._store.save(RewrittenUrl(old_url, new_url))

            # Actions have been uploaded to the server - remove them
            self._store.remove(actions)
            logger.debug('All actions have been uploaded to the server.')
            return True

        except (MissingCredentials, mygpoclient.http.Unauthorized):
            logger.warn('Invalid credentials. Disabling gpodder.net.')
            self._config.mygpo.enabled = False
            return False

        except Exception, e:
            logger.error('Cannot upload subscriptions: %s', str(e), exc_info=True)
            return False

    def update_device(self, action):
        try:
            logger.debug('Uploading device settings...')
            self._client.update_device_settings(action.device_id, \
                    action.caption, action.device_type)
            logger.debug('Device settings uploaded.')
            return True

        except (MissingCredentials, mygpoclient.http.Unauthorized):
            logger.warn('Invalid credentials. Disabling gpodder.net.')
            self._config.mygpo.enabled = False
            return False

        except Exception, e:
            logger.error('Cannot update device %s: %s', self.device_id,
                str(e), exc_info=True)
            return False

    def get_devices(self):
        result = []

        try:
            devices = self._client.get_devices()

        except (MissingCredentials, mygpoclient.http.Unauthorized):
            logger.warn('Invalid credentials. Disabling gpodder.net.')
            self._config.mygpo.enabled = False
            raise

        for d in devices:
            result.append((d.device_id, d.caption, d.type))
        return result

    def open_website(self):
        util.open_website('http://' + self._config.mygpo.server)


class Directory(object):
    def __init__(self):
        self.client = public.PublicClient()

    def toplist(self):
        return [(p.title or p.url, p.url)
                for p in self.client.get_toplist()
                if p.url]

    def search(self, query):
        return [(p.title or p.url, p.url)
                for p in self.client.search_podcasts(query)
                if p.url]

