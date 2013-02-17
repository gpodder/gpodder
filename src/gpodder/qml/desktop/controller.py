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

# Mikołaj Milej <mikolajmm@gmail.com>; 2013-01-02

import collections
import dbus
import subprocess

from PySide.QtCore import QObject
from PySide.QtCore import Signal
from PySide.QtCore import Slot
from PySide.QtDeclarative import QDeclarativeContext
from PySide.QtDeclarative import QDeclarativeEngine

import gpodder
from gpodder import util
from gpodder import youtube
from gpodder.model import Model

from gpodder import qml
from gpodder.qml import helper
from gpodder.qml import images
from gpodder.qml.common import QObjectProxy
from gpodder.qml.common import _, N_
from gpodder.qml.common import createQmlComponent
from gpodder.qml.controller import CommonController as QmlCommonController
from gpodder.qml.controller import CommonQtPodder as QmlCommonQtPodder
from gpodder.qml.desktop import model as desktopModel
from gpodder.qml.desktop.basiccontroller import BasicController

import logging
logger = logging.getLogger(__name__)

CONTROLLERS_SEARCH_MODULE = "gpodder.qml.desktop."


def classForName(module_name, class_name):
    try:
        import importlib

        # load the module, will raise ImportError if module cannot be loaded
        m = importlib.import_module(module_name)
        # get the class, will raise AttributeError if class cannot be found
        c = getattr(m, class_name)
        return c

    except ImportError as ex:
        print ex.args, ex.message
        return None


class Controller(QmlCommonController):
    changed = Signal()

    def __init__(self, root):
        QmlCommonController.__init__(self, root)

        self.config = self.root.config

        self._controllers = {
            'PodcastDirectory': None
        }

        self._controllersCreationArgs = {
            'PodcastDirectory': [self.addSubscriptions]
        }

    def getController(self, viewFileName):
        viewFileName = viewFileName.split(".qml", 1)[0]

        if viewFileName not in self._controllers:
            self._controllers[viewFileName] = None

        if self._controllers[viewFileName] is None:
            args = []
            if viewFileName in self._controllersCreationArgs:
                args = self._controllersCreationArgs[viewFileName]

            moduleName = CONTROLLERS_SEARCH_MODULE + viewFileName.lower()
            classObject = classForName(moduleName, viewFileName)

            if classObject is None:
                classObject = BasicController

            self._controllers[viewFileName] = classObject(self, *args)

        self._controllers[viewFileName].deleteMe.connect(self.deleteController)

        return self._controllers[viewFileName]

    @Slot(QObject, unicode)
    def createWindow(self, owner, filename):
        engine = self.root.qmlEngine

        controller = self.getController(filename)
        context = QDeclarativeContext(engine.rootContext(), controller)

        context.setContextProperty("myController", controller)
        controller.registerProperties(context)

        controller.view = createQmlComponent(
            filename, engine, context, controller
        )
        controller.view.setVisible(True)

    @Slot(QObject)
    def deleteController(self, controller):
        for key, value in self._controllers.iteritems():
            if value == controller:
                self._controllers[key] = None
                del controller
                break

    @Slot(QObject)
    def playback_selected_episodes(self, episode):
        self.playback_episodes([episode])

    def playback_episodes(self, episodes):
        # We need to create a list, because we run through it more than once
        episodes = list(Model.sort_episodes_by_pubdate(e for e in episodes if \
               e.was_downloaded(and_exists=True) or self.streaming_possible()))

        try:
            self.playback_episodes_for_real(episodes)
        except Exception, e:
            logger.error('Error in playback!', exc_info=True)
            self.root.show_message(
                _('Please check your media player settings in the preferences dialog.'),
                _('Error opening player'), widget=self.root.toolPreferences
            )

        channel_urls = set()
        episode_urls = set()
        for episode in episodes:
            channel_urls.add(episode.channel.url)
            episode_urls.add(episode.url)
#        self.update_episode_list_icons(episode_urls)
#        self.update_podcast_list_model(channel_urls)

    def playback_episodes_for_real(self, episodes):
        groups = collections.defaultdict(list)
        for episode in episodes:
            file_type = episode.file_type()
            if file_type == 'video' and self.config.videoplayer and \
                    self.config.videoplayer != 'default':
                player = self.config.videoplayer
            elif file_type == 'audio' and self.config.player and \
                    self.config.player != 'default':
                player = self.config.player
            else:
                player = 'default'

            # Mark episode as played in the database
            episode.playback_mark()
            self.root.mygpo_client.on_playback([episode])

            fmt_ids = youtube.get_fmt_ids(self.config.youtube)

            allow_partial = (player != 'default')
            filename = episode.get_playback_url(fmt_ids, allow_partial)

            # Determine the playback resume position - if the file
            # was played 100%, we simply start from the beginning
            resume_position = episode.current_position
            if resume_position == episode.total_time:
                resume_position = 0

            # If Panucci is configured, use D-Bus to call it
            if player == 'panucci':
                try:
                    PANUCCI_NAME = 'org.panucci.panucciInterface'
                    PANUCCI_PATH = '/panucciInterface'
                    PANUCCI_INTF = 'org.panucci.panucciInterface'
                    o = gpodder.dbus_session_bus.get_object(
                        PANUCCI_NAME, PANUCCI_PATH
                    )
                    i = dbus.Interface(o, PANUCCI_INTF)

                    def on_reply(*args):
                        pass

                    def error_handler(filename, err):
                        logger.error('Exception in D-Bus call: %s', str(err))

                        # Fallback: use the command line client
                        for command in util.format_desktop_command('panucci', \
                                [filename]):
                            logger.info('Executing: %s', repr(command))
                            subprocess.Popen(command)

                    on_error = lambda err: error_handler(filename, err)

                    # This method only exists in Panucci > 0.9 ('new Panucci')
                    i.playback_from(filename, resume_position, \
                            reply_handler=on_reply, error_handler=on_error)

                    continue  # This file was handled by the D-Bus call
                except Exception, e:
                    logger.error('Calling Panucci using D-Bus', exc_info=True)

            # flattr episode if auto-flattr is enabled
            if (episode.payment_url and self.config.flattr.token and
                    self.config.flattr.flattr_on_play):
                success, message = self.flattr.flattr_url(episode.payment_url)
                self.show_message(message, title=_('Flattr status'),
                        important=not success)

            groups[player].append(filename)

        # Open episodes with system default player
        if 'default' in groups:
            for filename in groups['default']:
                logger.debug('Opening with system default: %s', filename)
                util.gui_open(filename)
            del groups['default']

        # For each type now, go and create play commands
        for group in groups:
            for command in util.format_desktop_command(
                            group, groups[group], resume_position
                            ):
                logger.debug('Executing: %s', repr(command))
                subprocess.Popen(command)

        # Persist episode status changes to the database
        self.root.db.commit()

        # Flush updated episode status
        self.root.mygpo_client.flush()

    @Slot(str)
    def setEpisodeFilter(self, pattern):
        self.root.episodeProxyModel.setFilterFixedString(pattern)


class qtPodder(QmlCommonQtPodder):
    def __init__(self, args, gpodder_core, dbus_bus_name):
        QmlCommonQtPodder.__init__(self, args, gpodder_core, dbus_bus_name)

        self.controller = Controller(self)
        self.media_buttons_handler = helper.MediaButtonsHandler()
        self.tracker_miner_config = helper.TrackerMinerConfig()
        self.podcast_model = qml.model.gPodderPodcastListModel()
        self.episode_model = desktopModel.gPodderEpisodeListModel(self.config)
        self.last_episode = None

        # A dictionary of episodes that are currently active
        # in some way (i.e. playing back or downloading)
        self.active_episode_wrappers = {}

        # Add the cover art image provider
        self.cover_provider = images.LocalCachedImageProvider()

        # TODO: clear it, only for debug
        try:
            self._create_qml_gui('MainWindow.qml')

            # Proxy to the "main" QML mainWindow
            # for direct access to Qt Properties
            self.main = QObjectProxy(self.mainWindow.object)

        except AttributeError as ex:
            print "main: ", type(ex)
            print ex.args
            return

        self.main.podcastModel = self._create_model_filter(self.podcast_model)
        self.main.episodeModel = self._create_model_filter(self.episode_model)

        self.mainWindow.setVisible(True)

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
        self.mainWindow = createQmlComponent(
            filename, self.qmlEngine, context, self
        )
#        self.view.setWindowTitle('gPodder')

    def _create_model_filter(self, model):
        sortFilterProxyModel = desktopModel.SortFilterProxyModel(self)

        sortFilterProxyModel.setSourceModel(model)
        sortFilterProxyModel.setDynamicSortFilter(True)

        return sortFilterProxyModel

    quit = Signal()

    def on_quit(self):
        # Make sure the audio playback is stopped immediately
#        self.main.togglePlayback(None)
        self.save_pending_data()
        self.mainWindow.setVisible(True)
        del self.mainWindow
        self.core.shutdown()
        self.app.quit()

    do_start_progress = Signal(str, int)

    @Slot(str, int)
    def on_start_progress(self, text, value):
        self.main.startProgress(text, value)

    def start_progress(self, text=_('Please wait...'), progress=0):
        self.do_start_progress.emit(text, progress)
