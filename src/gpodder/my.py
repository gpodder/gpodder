# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2018 The gPodder Team
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

import atexit
import calendar
import datetime
import logging
import os
import sys
import time

import minidb
import mygpoclient
from mygpoclient import api, public
from mygpoclient import util as mygpoutil

import gpodder
from gpodder import util

_ = gpodder.gettext


logger = logging.getLogger(__name__)


# Append gPodder's user agent to mygpoclient's user agent
mygpoclient.user_agent += ' ' + gpodder.user_agent

# 2013-02-08: We should update this to 1.7 once we use the new features
MYGPOCLIENT_REQUIRED = '1.4'

if (not hasattr(mygpoclient, 'require_version')
        or not mygpoclient.require_version(MYGPOCLIENT_REQUIRED)):
    print("""
    Please upgrade your mygpoclient library.
    See http://thp.io/2010/mygpoclient/

    Required version:  %s
    Installed version: %s
    """ % (MYGPOCLIENT_REQUIRED, mygpoclient.__version__), file=sys.stderr)
    sys.exit(1)

try:
    from mygpoclient.simple import MissingCredentials

except ImportError:
    # if MissingCredentials does not yet exist in the installed version of
    # mygpoclient, we use an object that can never be raised/caught
    MissingCredentials = object()


EPISODE_ACTIONS_BATCH_SIZE = 100


# Database model classes
class SinceValue(minidb.Model):
    host = str
    device_id = str
    category = int
    since = int

    # Possible values for the "category" field
    PODCASTS, EPISODES = list(range(2))


class SubscribeAction(minidb.Model):
    action_type = int
    url = str

    # Possible values for the "action_type" field
    ADD, REMOVE = list(range(2))

    @classmethod
    def undo(cls, action):
        if action.action_type == self.ADD:
            return cls(self.REMOVE, action.url)
        elif action.action_type == self.REMOVE:
            return cls(self.ADD, action.url)

        raise ValueError('Cannot undo action: %r' % action)


class ReceivedSubscribeAction(minidb.Model):
    action_type = int
    url = str


class UpdateDeviceAction(minidb.Model):
    device_id = str
    caption = str
    device_type = str


class EpisodeAction(minidb.Model):
    podcast_url = str
    episode_url = str
    device_id = str
    action = str
    timestamp = int
    started = int
    position = int
    total = int


class ReceivedEpisodeAction(minidb.Model):
    podcast_url = str
    episode_url = str
    device_id = str
    action = str
    timestamp = int
    started = int
    position = int
    total = int


class RewrittenUrl(minidb.Model):
    old_url = str
    new_url = str
# End Database model classes


# Helper class for displaying changes in the UI
class Change(object):
    def __init__(self, action, podcast=None):
        self.action = action
        self.podcast = podcast

    @property
    def description(self):
        if self.action.action_type == SubscribeAction.ADD:
            return _('Add %s') % self.action.url
        else:
            return _('Remove %s') % self.podcast.title


class MygPoClient(object):
    STORE_FILE = 'mygposync.db'
    FLUSH_TIMEOUT = 60
    FLUSH_RETRIES = 3

    def __init__(self, config, store=None):
        if store is None:
            store = minidb.Store(os.path.join(gpodder.home, self.STORE_FILE))

        self._store = store

        for modelclass in (SinceValue,
                           SubscribeAction, ReceivedSubscribeAction,
                           UpdateDeviceAction,
                           EpisodeAction, ReceivedEpisodeAction,
                           RewrittenUrl):
            self._store.register(modelclass)

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
        self._store.delete_all(UpdateDeviceAction)

        # Insert our new update action
        action = UpdateDeviceAction(device_id=self.device_id,
                caption=self._config.mygpo.device.caption,
                device_type=self._config.mygpo.device.type)
        self._store.save(action)

    def get_rewritten_urls(self):
        """Returns a list of rewritten URLs for uploads

        This should be called regularly. Every object returned
        should be merged into the database, and the old_url
        should be updated to new_url in every podcdast.
        """
        rewritten_urls = list(self._store.load(RewrittenUrl))
        self._store.delete_all(RewrittenUrl)
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
        self._store.delete_all(ReceivedEpisodeAction)
        self._store.commit()
        logger.debug('Received episode actions processed.')

    def get_received_actions(self):
        """Returns a list of ReceivedSubscribeAction objects

        The list might be empty. All these actions have to
        be processed. The user should confirm which of these
        actions should be taken, the rest should be rejected.

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
        for action in actions:
            action.delete()

    def reject_received_actions(self, actions):
        """Reject (undo) a list of ReceivedSubscribeAction objects

        The UI should call this with a list of actions that
        have been rejected by the user. A reversed set of
        actions will be uploaded to the server so that the
        state on the server matches the state on the client.
        """
        # Create "undo" actions for received subscriptions
        for action in actions:
            self._store.save(SubscribeAction.undo(a))
            action.delete()
        self.flush()

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
        return EpisodeAction(podcast_url=episode.channel.url,
                episode_url=episode.url,
                device_id=self.device_id,
                action='play',
                timestamp=int(time.time()),
                started=start,
                position=end,
                total=total)

    def _convert_episode(self, episode, action):
        return EpisodeAction(podcast_url=episode.channel.url,
                episode_url=episode.url,
                device_id=self.device_id,
                action=action,
                timestamp=int(time.time()),
                started=None,
                position=None,
                total=None)

    def on_delete(self, episodes):
        logger.debug('Storing %d episode delete actions', len(episodes))
        for e in episodes:
            self._convert_episode(e, 'delete').save(self._store)

    def on_download(self, episodes):
        logger.debug('Storing %d episode download actions', len(episodes))
        for e in episodes:
            self._convert_episode(e, 'download').save(self._store)

    def on_playback_full(self, episode, start, end, total):
        logger.debug('Storing full episode playback action')
        self._convert_played_episode(episode, start, end, total).save(self._store)

    def on_playback(self, episodes):
        logger.debug('Storing %d episode playback actions', len(episodes))
        for e in episodes:
            self._convert_episode(e, 'play').save(self._store)

    def on_subscribe(self, urls):
        for url in urls:
            # Cancel previously-inserted "remove" action
            self._store.delete_where(SubscribeAction, (SubscribeAction.c.url == url and
                                                       SubscribeAction.c.action_type == SubscribeAction.REMOVE))

            # Insert new "add" action
            SubscribeAction(url=url, action_type=SubscribeAction.ADD).save(self._store)

        self.flush()

    def on_unsubscribe(self, urls):
        for url in urls:
            # Cancel previously-inserted "add" actions
            self._store.delete_where(SubscribeAction, (SubscribeAction.c.url == url and
                                                       SubscribeAction.c.action_type == SubscribeAction.ADD))

            # Insert new "remove" actions
            SubscribeAction(url=url, action_type=SubscribeAction.REMOVE).save(self._store)

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
                        action.delete()
                    else:
                        must_retry = True

                # Upload podcast subscription actions
                actions = self._store.load(SubscribeAction)
                if self.synchronize_subscriptions(actions):
                    for action in actions:
                        action.delete()
                else:
                    must_retry = True

                # Upload episode actions
                actions = self._store.load(EpisodeAction)
                if self.synchronize_episodes(actions):
                    for action in actions:
                        action.delete()
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
            logger.warning('Flush requested, but sync disabled.')
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
            return api.EpisodeAction(action.podcast_url,
                    action.episode_url, action.action,
                    action.device_id, action_ts,
                    action.started, action.position, action.total)

        def convert_from_api(action):
            dt = mygpoutil.iso8601_to_datetime(action.timestamp)
            action_ts = calendar.timegm(dt.timetuple())
            return ReceivedEpisodeAction(podcast_url=action.podcast,
                    episode_url=action.episode,
                    device_id=action.device,
                    action=action.action,
                    timestamp=action_ts,
                    started=action.started,
                    position=action.position,
                    total=action.total)

        try:
            # Load the "since" value from the database
            since_o = self._store.get(SinceValue, host=self.host,
                                      device_id=self.device_id,
                                      category=SinceValue.EPISODES)

            # Use a default since object for the first-time case
            if since_o is None:
                since_o = SinceValue(host=self.host, device_id=self.device_id, category=SinceValue.EPISODES, since=0)

            # Step 1: Download Episode actions
            try:
                changes = self._client.download_episode_actions(since_o.since)

                received_actions = [convert_from_api(a) for a in changes.actions]
                logger.debug('Received %d episode actions', len(received_actions))
                for action in received_actions:
                    action.save(self._store)

                # Save the "since" value for later use
                since_o.since = changes.since
                since_o.save(self._store)

            except (MissingCredentials, mygpoclient.http.Unauthorized):
                # handle outside
                raise

            except Exception as e:
                logger.warning('Exception while polling for episodes.', exc_info=True)

            # Step 2: Upload Episode actions

            actions = list(actions)

            # Uploads are done in batches; uploading can resume if only parts
            # be uploaded; avoids empty uploads as well
            for lower in range(0, len(actions), EPISODE_ACTIONS_BATCH_SIZE):
                batch = actions[lower:(lower + EPISODE_ACTIONS_BATCH_SIZE)]

                # Convert actions to the mygpoclient format for uploading
                episode_actions = [convert_to_api(a) for a in batch]

                # Upload the episode actions
                self._client.upload_episode_actions(episode_actions)

                # Actions have been uploaded to the server - remove them
                for action in batch:
                    action.delete()

            logger.debug('Episode actions have been uploaded to the server.')
            return True

        except (MissingCredentials, mygpoclient.http.Unauthorized):
            logger.warning('Invalid credentials. Disabling gpodder.net.')
            self._config.mygpo.enabled = False
            return False

        except Exception as e:
            logger.error('Cannot upload episode actions: %s', str(e), exc_info=True)
            return False

    def synchronize_subscriptions(self, actions):
        logger.debug('Starting subscription sync.')
        try:
            # Load the "since" value from the database
            since_o = self._store.get(SinceValue, host=self.host,
                                      device_id=self.device_id,
                                      category=SinceValue.PODCASTS)

            # Use a default since object for the first-time case
            if since_o is None:
                since_o = SinceValue(host=self.host, device_id=self.device_id, category=SinceValue.PODCASTS, since=0)

            # Step 1: Pull updates from the server and notify the frontend
            result = self._client.pull_subscriptions(self.device_id, since_o.since)

            # Update the "since" value in the database
            since_o.since = result.since
            since_o.save(self._store)

            # Store received actions for later retrieval (and in case we
            # have outdated actions in the database, simply remove them)
            for url in result.add:
                logger.debug('Received add action: %s', url)
                self._store.delete_where(ReceivedSubscribeAction, ReceivedSubscribeAction.c.url == url)
                ReceivedSubscribeAction(url=url, action_type=SubscribeAction.ADD).save(self._store)
            for url in result.remove:
                logger.debug('Received remove action: %s', url)
                self._store.delete_where(ReceivedSubscribeAction, ReceivedSubscribeAction.c.url == url)
                ReceivedSubscribeAction(url=url, action_type=SubscribeAction.REMOVE).save(self._store)

            # Step 2: Push updates to the server and rewrite URLs (if any)
            actions = self._store.load(SubscribeAction)

            add = [a.url for a in actions if a.action_type == SubscribeAction.ADD]
            remove = [a.url for a in actions if a.action_type == SubscribeAction.REMOVE]

            if add or remove:
                logger.debug('Uploading: +%d / -%d', len(add), len(remove))
                # Only do a push request if something has changed
                result = self._client.update_subscriptions(self.device_id, add, remove)

                # Update the "since" value in the database
                since_o.since = result.since
                since_o.save(self._store)

                # Store URL rewrites for later retrieval by GUI
                for old_url, new_url in result.update_urls:
                    if new_url:
                        logger.debug('Rewritten URL: %s', new_url)
                        RewrittenUrl(old_url=old_url, new_url=new_url).save(self._store)

            # Actions have been uploaded to the server - remove them
            for action in actions:
                action.delete()
            logger.debug('All actions have been uploaded to the server.')
            return True

        except (MissingCredentials, mygpoclient.http.Unauthorized):
            logger.warning('Invalid credentials. Disabling gpodder.net.')
            self._config.mygpo.enabled = False
            return False

        except Exception as e:
            logger.error('Cannot upload subscriptions: %s', str(e), exc_info=True)
            return False

    def update_device(self, action):
        try:
            logger.debug('Uploading device settings...')
            self._client.update_device_settings(action.device_id,
                    action.caption, action.device_type)
            logger.debug('Device settings uploaded.')
            return True

        except (MissingCredentials, mygpoclient.http.Unauthorized):
            logger.warning('Invalid credentials. Disabling gpodder.net.')
            self._config.mygpo.enabled = False
            return False

        except Exception as e:
            logger.error('Cannot update device %s: %s', self.device_id,
                str(e), exc_info=True)
            return False

    def get_devices(self):
        result = []

        try:
            devices = self._client.get_devices()

        except (MissingCredentials, mygpoclient.http.Unauthorized):
            logger.warning('Invalid credentials. Disabling gpodder.net.')
            self._config.mygpo.enabled = False
            raise

        for d in devices:
            result.append((d.device_id, d.caption, d.type))
        return result

    def open_website(self):
        util.open_website('http://' + self._config.mygpo.server)

    def get_download_user_subscriptions_url(self):
        OPML_URL = self._client.locator.subscriptions_uri()
        url = util.url_add_authentication(OPML_URL,
                self._config.mygpo.username,
                self._config.mygpo.password)
        return url


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
