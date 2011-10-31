# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
# Copyright (c) 2011 Neal H. Walfield
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

#  gpodder.woodchuck - Woodchuck support for gPodder (2011-07)

import gpodder
from gpodder import feedcore
from gpodder.util import idle_add

from functools import wraps
import time
import threading
import traceback

import logging
logger = logging.getLogger(__name__)

# Don't fail if the Woodchuck modules are not available.  Just disable
# Woodchuck's functionality.

# Whether we imported the woodchuck modules successfully.
woodchuck_imported = True
try:
    import pywoodchuck
    from pywoodchuck import PyWoodchuck
    from pywoodchuck import woodchuck
except ImportError, e:
    logger.info('Unable to load pywoodchuck. Disabling woodchuck plug-in.')
    woodchuck_imported = False

    class PyWoodchuck(object):
        def __init__(self, *args, **kwargs):
            pass

        def available(self):
            return False

# The default podcast refresh interval: 6 hours.
REFRESH_INTERVAL = 6 * 60 * 60

_main_thread = None
def execute_in_main_thread(func):
    """
    Execute FUNC in the main thread asynchronously (i.e., do not wait
    for the function to be executed before returning to the caller).

    This is used for executing DBus calls, which are not thread safe,
    in the main thread.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not woodchuck_instance.available():
            return

        def doit():
            @wraps(func)
            def it():
                # Execute the function.

                # Assert that we are running in the main thread.
                assert _main_thread is not None
                assert threading.currentThread() == _main_thread, \
                    ("idle function executed in %s, not %s"
                     % (threading.currentThread(), _main_thread))

                try:
                    func(*args, **kwargs)
                except KeyboardInterrupt:
                    raise
                except:
                    logger.error(
                        "execute_in_main_thread: Executing %s: %s"
                        % (func, traceback.format_exc()))
    
                return False
            return it
    
        if threading.currentThread() == _main_thread:
            logger.debug("Already in main thread. Executing %s" % (func,))
            doit()()
        else:
            logger.debug("Queuing execution of %s from %s"
                         % (func, threading.currentThread()))
            idle_add(doit())
    return wrapper

def coroutine(func):
    """
    func is a function that returns a generator.  This routine runs
    the generator until it raises the StopIteration exception.

    After the generator emits a value and before it is run again, the
    event loop is iterated.
    """
    def wrapper(*args, **kwargs):
        def doit(generator):
            def execute():
                try:
                    generator.next()
                    idle_add(execute)
                except StopIteration:
                    return
                except Exception, e:
                    logger.exception("Running %s: %s" % (str(func), str(e)))
            execute()

        generator = func(*args, **kwargs)
        doit(generator)
    return wrapper

class mywoodchuck(PyWoodchuck):
    def __init__(self, model, podcast_update, episode_download):
        if podcast_update is None and episode_download is None:
            # Disable upcalls.
            request_feedback = False
        else:
            request_feedback = True

        PyWoodchuck.__init__(self, "gPodder", "org.gpodder",
                             request_feedback=request_feedback)

        self.model = model
        self.podcast_update = podcast_update
        self.episode_download = episode_download

    def auto_download(self, stream, obj):
        """Return whether to auto download an episode."""
        # If the episode was published before the stream was
        # registered, don't automatically download it.
        if obj.publication_time >= stream.registration_time:
            True

        # If the episode is one of the two newest episodes, download
        # it.
        try:
            podcast = self.stream_to_podcast(stream)
            episode = self.object_to_episode(stream, obj)
            episodes = podcast.get_all_episodes()
            episodes.sort(key=lambda e: e.published, reverse=True)
            if episode in episodes[:2]:
                logging.debug("Auto-downloading %s (from %s)",
                              episode.title, podcast.title)
                return True
            return False
        except Exception, e:
            logging.exception("Checking whether to auto-download episode: %s"
                              % (str(e),))

    def stream_to_podcast(self, stream):
        """
        Find the gPodder podcast corresponding to the Woodchuck stream.
        """
        known_podcasts = self.model.get_podcasts()
        matching_podcasts = [p for p in known_podcasts
                             if p.url == stream.identifier]
        if not matching_podcasts:
            logger.warn(
                "lookup_podcast: Unknown stream: %s (%s) (known: %s): %s"
                % (stream.human_readable_name, stream.identifier,
                   ' '.join(p.url for p in known_podcasts),
                   traceback.format_exc()))
            return None

        # URL is supposed to be a primary key and thus at most one
        # podcast should match.
        assert(len(matching_podcasts) == 1)

        return matching_podcasts[0]

    def object_to_episode(self, stream, object):
        """
        Find the gPodder podcast episode corresponding to the
        Woodchuck object (which is in the specified stream).
        """
        podcast = self.stream_to_podcast(stream)
        if podcast is None:
            return None

        episodes = [e for e in podcast.get_all_episodes()
                    if e.guid == object.identifier]
        if not episodes:
            # This can happen if Woodchuck queues a stream update and
            # an object download and the stream update indicates that
            # the object has disappeared.  This is often the case
            logger.warn("Unknown object: %s (%s): %s"
                        % (object.human_readable_name, object.identifier,
                           traceback.format_exc()))
            return None

        assert(len(episodes) == 1)
        return episodes[0]

    # Woodchuck upcalls.
    def stream_update_cb(self, stream, *args, **khwargs):
        logger.info("stream update called on %s (%s)"
                    % (stream.human_readable_name, stream.identifier,))

        podcast = self.stream_to_podcast(stream)
        if podcast is None:
            # Seems the podcast was deleted, but we didn't get the
            # notification.
            stream.update_failed(woodchuck.TransferStatus.FailureGone)
            stream.unregister()
        else:
            self.podcast_update(podcast)

    def object_transfer_cb(self, stream, object,
                           version, filename, quality,
                           *args, **khwargs):
        logger.info("object transfer called on %s (%s) in stream %s (%s)"
                    % (object.human_readable_name, object.identifier,
                       stream.human_readable_name, stream.identifier))

        episode = self.object_to_episode(stream, object)
        if episode is None:
            # This can happen if Woodchuck queues a stream update and
            # an object download and the stream update indicates that
            # the object has disappeared.  This can happen when
            # Woodchuck queues a stream update and an object download
            # at the same time: the stream update notices that the
            # object is no longer available, but the object update is
            # still queued up.
            object.transfer_failed(woodchuck.TransferStatus.FailureGone)
            object.unregister()
        else:
            self.episode_download(episode)

    # gPodder callbacks.
    @execute_in_main_thread
    def on_podcast_subscribe(self, podcast):
        logger.debug("Podcast %s (%s): subscribe"
                      % (podcast.url, podcast.title))

        try:
            stream = self.stream_register(
                podcast.url, podcast.title, REFRESH_INTERVAL)
        except woodchuck.ObjectExistsError:
            # We can get an ObjectExistsError because we also register
            # new podcasts in on_podcast_save.  We do this in case an
            # episode is registered before its podcast is registered.
            pass

    @execute_in_main_thread
    def on_podcast_delete(self, podcast):
        logger.debug("Podcast %s (%s): unsubscribe"
                     % (podcast.url, podcast.title))

        self.stream_unregister(podcast.url)

    @execute_in_main_thread
    def on_podcast_save(self, podcast):
        try:
            changes = podcast.changed
        except AttributeError:
            changes = None
        if changes is None:
            changes = {}

        logger.debug("Podcast %s (%s) being saving: the following changed: %s"
                     % (podcast.url, podcast.title, str(changes)))

        # If the key changed, we need the old value to find the
        # corresponding Woodchuck object.
        key = changes.get('url', podcast.url)
        try:
            stream = self[key]
            registered_stream = False
        except KeyError:
            # Seems we haven't registered the podcast yet.  It is
            # possible that this is called before on_podcast_subscribe
            # is called.

            # There is no key to change.
            key = podcast.url
            self.on_podcast_subscribe(self, podcast)
            stream = self[key]
            registered_stream = True

        if 'url' in changes and not registered_stream:
            stream.identifier = podcast.url

        if 'title' in changes:
            stream.human_readable_name = podcast.title

    @execute_in_main_thread
    def on_podcast_updated(self, podcast):
        logger.debug("podcast updated: %s (%s)"
                     % (podcast.title, podcast.url,))

        self.stream_updated(podcast.url)

    @execute_in_main_thread
    def on_podcast_update_failed(self, podcast, exception):
        logger.debug("podcast update failed: %s (%s)"
                     % (podcast.title, podcast.url,))

        # Assume the error is transient.
        status = woodchuck.DownloadStatus.TransientOther

        if (any(isinstance(exception, exception_class)
                for exception_class in [feedcore.Unsubscribe,
                                        feedcore.NotFound,
                                        feedcore.InvalidFeed,
                                        feedcore.UnknownStatusCode])):
            # The podcast disappeared...
            status = woodchuck.DownloadStatus.FailureGone
        elif (any(isinstance(exception, exception_class)
                  for exception_class in [feedcore.Offline,
                                          feedcore.WifiLogin])):
            # Tranient network error.
            status = woodchuck.DownloadStatus.TransientNetwork

        self.stream_update_failed(podcast.url, status)

    @execute_in_main_thread
    def on_episode_save(self, episode):
        try:
            changes = episode.changed
        except AttributeError:
            changes = None
        if changes is None:
            changes = {}

        logger.debug(
            "Episode %s (%s) being saving: the following changed: %s"
            % (episode.guid, episode.title, str(changes)))

        try:
            stream = self[episode.channel.url]
        except KeyError:
            # Seems we haven't registered the podcast yet.
            self.on_podcast_subscribe(self, episode.channel)
            stream = self[episode.channel.url]

        # If the key changed, we need the old value to find the
        # corresponding Woodchuck object.
        key = changes.get('guid', episode.guid)
        try:
            obj = stream[key]
            registered_object = False
        except KeyError:
            # It seems that there is no Woodchuck object with the
            # specified key.  Register it now.
            logger.debug(
                "Registering new episode: guid: %s; title: %s; size: %d"
                % (episode.guid, episode.title, episode.file_size))

            key = episode.guid

            obj = stream.object_register(
                key, episode.title, expected_size=episode.file_size)
            registered_object = True

            obj.publication_time = episode.published
            if not self.auto_download(stream, obj):
                obj.dont_transfer = True

            obj.discovery_time = int(time.time())

        if 'guid' in changes and not registered_object:
            obj.identifier = episode.guid

        if 'title' in changes:
            obj.human_readable_name = episode.title

        if 'published' in changes:
            obj.publication_time = episode.published

        if 'http_last_modified' in changes or 'etag' in changes:
            # The episode was modified.  If the episode is eligible
            # for download, note that an update is available.
            if self.auto_download(stream, obj):
                obj.need_update = True

        if 'last_playback' in changes:
            # Assume that the user played between the old current
            # position and the new current position.
            start = changes.get('current_position', 0)
            end = obj.current_position
            if start > end:
                # The user rewound.  Assume [0, end]
                start = 0

            use_mask = 0

            # A bit less than half of a 1/64.
            delta = (float(obj.total_time) / 64 / 2
                     - float(obj.total_time) / 100)
            for b in range(
                round(64 * (float(start - delta) / obj.total_time)),
                round(64 * (float(end + delta) / obj.total_time))):
                use_mask = use_mask | 2 << b
            if use_mask:
                obj.used(use_mask=use_mask)

    @execute_in_main_thread
    def on_episode_downloaded(self, episode):
        logger.debug("Episode %s (%s) downloaded"
                     % (episode.guid, episode.title))

        self[episode.channel.url][episode.guid].transferred(
            object_size=episode.file_size)

    @execute_in_main_thread
    def on_episode_delete(self, episode, filename):
        logger.debug("Episode %s (%s): file deleted (%s)"
                     % (episode.guid, episode.title, filename))

        self[episode.channel.url][episode.guid].files_deleted()

    @execute_in_main_thread
    def on_episode_removed_from_podcast(self, episode):
        logger.debug("Episode %s (%s) removed" % (episode.guid, episode.title))

        del self[episode.channel.url][episode.guid]

@coroutine
def check_subscriptions():
    # Called at start up to synchronize Woodchuck's database with
    # gPodder's database.

    # The list of known streams.
    streams = woodchuck_instance.streams_list()
    stream_ids = [s.identifier for s in streams]
    yield

    # Register any unknown streams.  Remove known streams from
    # STREAMS_IDS.
    for podcast in woodchuck_instance.model.get_podcasts():
        if podcast.url not in stream_ids:
            logger.debug("Registering previously unknown podcast: %s (%s)"
                          % (podcast.title, podcast.url,))
            woodchuck_instance.stream_register(
                podcast.url, podcast.title, REFRESH_INTERVAL)
        else:
            woodchuck_instance[podcast.url].human_readable_name = podcast.title
            stream_ids.remove(podcast.url)
        yield

    # Unregister any streams that are no longer subscribed to.
    for id in stream_ids:
        logger.debug("Unregistering %s" % (id,))
        woodchuck_instance.stream_unregister(id)
        yield

class WoodchuckLoader():
    def on_ui_initialized(self, model, update_podcast_callback,
            download_episode_callback):
        """
        Connect to the woodchuck server and initialize any state.

        model is an instance of the podcast model.

        podcast_update is a function that is passed a single argument: the
        PodcastPodcast that should be updated.

        episode_download is a function that is passed a single argument:
        the PodcastEpisode that should be downloaded.

        If podcast_update and episode_download are None, then Woodchuck
        upcalls will be disabled.  In this case, you don't need to specify
        the list of podcasts.  Just specify None.
        """
        logger.info('Got on_ui_initialized. Setting up woodchuck..')

        global woodchuck_loader
        gpodder.user_hooks.unregister_hooks(woodchuck_loader)
        woodchuck_loader = None

        if not woodchuck_imported:
            return

        global _main_thread
        _main_thread = threading.currentThread()

        global woodchuck_instance
        woodchuck_instance = mywoodchuck(model,
                update_podcast_callback,
                download_episode_callback)

        if not woodchuck_instance.available():
            logger.warn('Unable to contact Woodchuck server. Disabling.')
            return

        logger.info('Connected to Woodchuck server.')

        gpodder.user_hooks.register_hooks(woodchuck_instance)

        idle_add(check_subscriptions)

woodchuck_loader = WoodchuckLoader()
woodchuck_instance = None

gpodder.user_hooks.register_hooks(woodchuck_loader)

