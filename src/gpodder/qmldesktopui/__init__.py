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

# gpodder.qmldesktopui - gPodder's QML Desktop interface
# Thomas Perl <thp@gpodder.org>; 2011-02-06
# Mikołaj Milej <mikolajmm@gmail.com>; 2012-12-24

import os
import io
import signal
import functools
import subprocess
import logging
logger = logging.getLogger("qmldesktopui")

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

from PySide.QtGui import QApplication
from PySide.QtCore import Qt, QObject, Signal, Slot, Property, QUrl
from PySide.QtDeclarative import QDeclarativeComponent, QDeclarativeContext, QDeclarativeEngine
from PySide.QtDeclarative import QDeclarativeError

import gpodder
from gpodder import core
from gpodder import util
from gpodder import my
from gpodder import query
from gpodder import common
from gpodder.model import Model
from gpodder.qmldesktopui import model
from gpodder.qmldesktopui import helper
from gpodder.qmldesktopui import images
from gpodder.qmldesktopui.controller import Controller

import qmlcommon
from qmlcommon import _, EPISODE_LIST_FILTERS

class ConfigProxy(QObject):
    def __init__(self, config):
        QObject.__init__(self)
        self._config = config

        config.add_observer(self._on_config_changed)

    def _on_config_changed(self, name, old_value, new_value):
        if name == 'ui.qml.autorotate':
            self.autorotateChanged.emit()
        elif name == 'flattr.token':
            self.flattrTokenChanged.emit()
        elif name == 'flattr.flattr_on_play':
            self.flattrOnPlayChanged.emit()

    def get_autorotate(self):
        return self._config.ui.qml.autorotate

    def set_autorotate(self, autorotate):
        self._config.ui.qml.autorotate = autorotate

    autorotateChanged = Signal()

    autorotate = Property(bool, get_autorotate, set_autorotate,
            notify=autorotateChanged)

    def get_flattr_token(self):
        return self._config.flattr.token

    def set_flattr_token(self, flattr_token):
        self._config.flattr.token = flattr_token

    flattrTokenChanged = Signal()

    flattrToken = Property(unicode, get_flattr_token, set_flattr_token,
            notify=flattrTokenChanged)

    def get_flattr_on_play(self):
        return self._config.flattr.flattr_on_play

    def set_flattr_on_play(self, flattr_on_play):
        self._config.flattr.flattr_on_play = flattr_on_play

    flattrOnPlayChanged = Signal()

    flattrOnPlay = Property(bool, get_flattr_on_play, set_flattr_on_play,
            notify=flattrOnPlayChanged)
                
def QML(filename):
    for folder in gpodder.ui_folders:
        filename = os.path.join(folder, filename)
        if os.path.exists(filename):
            return filename

class qtPodder(QObject):
    def __init__(self, args, gpodder_core, dbus_bus_name):
        QObject.__init__(self)

        self.dbus_bus_name = dbus_bus_name
        # TODO: Expose the same D-Bus API as the Gtk UI D-Bus qmlObject (/gui)
        # TODO: Create a gpodder.dbusproxy.DBusPodcastsProxy qmlObject (/podcasts)

        self.app = QApplication(args)
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        self.quit.connect(self.on_quit)

        self.core = gpodder_core
        self.config = self.core.config
        self.db = self.core.db
        self.model = self.core.model

        self.config_proxy = ConfigProxy(self.config)

        # Initialize the gpodder.net client
        self.mygpo_client = my.MygPoClient(self.config)

        gpodder.user_extensions.on_ui_initialized(self.model,
                self.extensions_podcast_update_cb,
                self.extensions_episode_download_cb)


        self.controller = Controller(self)
        self.media_buttons_handler = helper.MediaButtonsHandler()
        self.tracker_miner_config = helper.TrackerMinerConfig()
        self.podcast_model = model.gPodderPodcastListModel()
        self.episode_model = model.gPodderEpisodeListModel(self.config)
        self.last_episode = None

        # A dictionary of episodes that are currently active
        # in some way (i.e. playing back or downloading)
        self.active_episode_wrappers = {}

        # Add the cover art image provider
        self.cover_provider = images.LocalCachedImageProvider()

        self._create_qml_gui('MainWindow.qml')

        # Proxy to the "main" QML qmlObject for direct access to Qt Properties
        self.main = helper.QObjectProxy(self.qmlObject.property('main'))

        self.main.podcastModel = self.podcast_model
        self.main.episodeModel = self.episode_model

        self.qmlObject.show()

        self.do_start_progress.connect(self.on_start_progress)
        self.do_end_progress.connect(self.on_end_progress)
        self.do_show_message.connect(self.on_show_message)

        podcasts = self.load_podcasts()

        self.resumable_episodes = None
        self.do_offer_download_resume.connect(self.on_offer_download_resume)
        util.run_in_background(self.find_partial_downloads(podcasts))

    def _create_qml_gui(self, filename):
        self.qmlEngine = QDeclarativeEngine()
        self.qmlEngine.addImageProvider('cover', self.cover_provider)
        
        context = self.qmlEngine.rootContext()
        
        context.setContextProperty('controller', self.controller)
        context.setContextProperty('configProxy', self.config_proxy)
        context.setContextProperty('mediaButtonsHandler',
                self.media_buttons_handler)
        context.setContextProperty('trackerMinerConfig',
                self.tracker_miner_config)
        
        # Load the QML UI (this could take a while...)
        self.qmlComponent = QDeclarativeComponent(self.qmlEngine, QUrl.fromLocalFile(QML(filename)))
        self.qmlObject = self.qmlComponent.create(context)
        
#        self.view.setResizeMode(QDeclarativeView.SizeRootObjectToView)
#        self.view.setWindowTitle('gPodder')
        

    def find_partial_downloads(self, podcasts):
        def start_progress_callback(count):
            self.start_progress(_('Loading incomplete downloads'))

        def progress_callback(title, progress):
            self.start_progress('%s (%d%%)' % (
                _('Loading incomplete downloads'),
                progress*100))

        def finish_progress_callback(resumable_episodes):
            self.end_progress()
            self.resumable_episodes = resumable_episodes
            self.do_offer_download_resume.emit()

        common.find_partial_downloads(podcasts,
                start_progress_callback,
                progress_callback,
                finish_progress_callback)

    do_offer_download_resume = Signal()

    def on_offer_download_resume(self):
        if self.resumable_episodes:
            def download_episodes():
                for episode in self.resumable_episodes:
                    qepisode = self.wrap_simple_episode(episode)
                    self.controller.downloadEpisode(qepisode)

            def delete_episodes():
                logger.debug('Deleting incomplete downloads.')
                common.clean_up_downloads(delete_partial=True)

            message = _('Incomplete downloads from a previous session were found.')
            title = _('Resume')

            self.controller.confirm_action(message, title, download_episodes, delete_episodes)

    def add_active_episode(self, episode):
        self.active_episode_wrappers[episode.id] = episode
        episode.episode_wrapper_refcount += 1

    def remove_active_episode(self, episode):
        episode.episode_wrapper_refcount -= 1
        if episode.episode_wrapper_refcount == 0:
            del self.active_episode_wrappers[episode.id]

    def load_last_episode(self):
        last_episode = None
        last_podcast = None
        for podcast in self.podcast_model.get_podcasts():
            for episode in podcast.get_all_episodes():
                if not episode.last_playback:
                    continue
                if last_episode is None or \
                        episode.last_playback > last_episode.last_playback:
                    last_episode = episode
                    last_podcast = podcast

        if last_episode is not None:
            self.last_episode = self.wrap_episode(last_podcast, last_episode)
            # FIXME: Send last episode to player
            #self.select_episode(self.last_episode)

    def on_episode_deleted(self, episode):
        # Remove episode from play queue (if it's in there)
        self.main.removeQueuedEpisode(episode)

        # If the episode that has been deleted is currently
        # being played back (or paused), stop playback now.
        if self.main.currentEpisode == episode:
            self.main.togglePlayback(None)

    def enqueue_episode(self, episode):
        self.main.enqueueEpisode(episode)

    def run(self):
        return self.app.exec_()

    quit = Signal()

    def on_quit(self):
        # Make sure the audio playback is stopped immediately
#        self.main.togglePlayback(None)
#        self.save_pending_data()
        self.qmlObject.hide()
        self.core.shutdown()
        self.app.quit()

    do_show_message = Signal(unicode)

    @Slot(unicode)
    def on_show_message(self, message):
        self.main.showMessage(message)

    def show_message(self, message):
        self.do_show_message.emit(message)

    def show_input_dialog(self, message, value='', accept=_('OK'),
            reject=_('Cancel'), is_text=True):
        self.main.showInputDialog(message, value, accept, reject, is_text)

    def open_context_menu(self, items):
        self.main.openContextMenu(items)

    do_start_progress = Signal(str)

    @Slot(str)
    def on_start_progress(self, text):
        self.main.startProgress(text)

    def start_progress(self, text=_('Please wait...')):
        self.do_start_progress.emit(text)

    do_end_progress = Signal()

    @Slot()
    def on_end_progress(self):
        self.main.endProgress()

    def end_progress(self):
        self.do_end_progress.emit()

    def resort_podcast_list(self):
        self.podcast_model.sort()

    def insert_podcast(self, podcast):
        self.podcast_model.insert_object(podcast)
        self.mygpo_client.on_subscribe([podcast.url])
        self.mygpo_client.flush()

    def remove_podcast(self, podcast):
        # Remove queued episodes for this specific podcast
        self.main.removeQueuedEpisodesForPodcast(podcast)

        if self.main.currentEpisode is not None:
            # If the currently-playing episode is in the podcast
            # that is to be deleted, stop playback immediately.
            if self.main.currentEpisode.qpodcast == podcast:
                self.main.togglePlayback(None)
        self.podcast_model.remove_object(podcast)
        self.mygpo_client.on_unsubscribe([podcast.url])
        self.mygpo_client.flush()

    def load_podcasts(self):
        podcasts = map(model.QPodcast, self.model.get_podcasts())
        self.podcast_model.set_podcasts(self.db, podcasts)
        return podcasts

    def wrap_episode(self, podcast, episode):
        try:
            return self.active_episode_wrappers[episode.id]
        except KeyError:
            return model.QEpisode(self, podcast, episode)

    def wrap_simple_episode(self, episode):
        for podcast in self.podcast_model.get_podcasts():
            if podcast.id == episode.podcast_id:
                return self.wrap_episode(podcast, episode)

        return None

    def select_podcast(self, podcast):
        if isinstance(podcast, model.QPodcast):
            # Normal QPodcast instance
            wrap = functools.partial(self.wrap_episode, podcast)
            objects = podcast.get_all_episodes()
            self.episode_model.set_is_subset_view(False)
        else:
            # EpisodeSubsetView
            wrap = lambda args: self.wrap_episode(*args)
            objects = podcast.get_all_episodes_with_podcast()
            self.episode_model.set_is_subset_view(True)

        self.episode_model.set_objects(map(wrap, objects))
        self.main.state = 'episodes'

    def save_pending_data(self):
        current_ep = self.main.currentEpisode
        if isinstance(current_ep, model.QEpisode):
            current_ep.save()

    def podcast_to_qpodcast(self, podcast):
        podcasts = filter(lambda p: p._podcast == podcast,
                          self.podcast_model.get_podcasts())
        assert len(podcasts) <= 1
        if podcasts:
            return podcasts[0]
        return None

    def extensions_podcast_update_cb(self, podcast):
        logger.debug('extensions_podcast_update_cb(%s)', podcast)
        try:
            qpodcast = self.podcast_to_qpodcast(podcast)
            if qpodcast is not None and not qpodcast.pause_subscription:
                qpodcast.qupdate(
                    finished_callback=self.controller.update_subset_stats)
        except Exception, e:
            logger.exception('extensions_podcast_update_cb(%s): %s', podcast, e)

    def extensions_episode_download_cb(self, episode):
        logger.debug('extensions_episode_download_cb(%s)', episode)
        try:
            qpodcast = self.podcast_to_qpodcast(episode.channel)
            qepisode = self.wrap_episode(qpodcast, episode)
            self.controller.downloadEpisode(qepisode)
        except Exception, e:
            logger.exception('extensions_episode_download_cb(%s): %s', episode, e)

def main(args):
    try:
        dbus_main_loop = DBusGMainLoop(set_as_default=True)
        gpodder.dbus_session_bus = dbus.SessionBus(dbus_main_loop)

        bus_name = dbus.service.BusName(gpodder.dbus_bus_name,
                bus=gpodder.dbus_session_bus)
    except dbus.exceptions.DBusException, dbe:
        logger.warn('Cannot get "on the bus".', exc_info=True)
        bus_name = None

    gui = qtPodder(args, core.Core(), bus_name)
    return gui.run()

