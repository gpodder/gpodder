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

# gpodder.qmlui - gPodder's QML interface
# Thomas Perl <thp@gpodder.org>; 2011-02-06

import functools
import itertools
import os
import signal
import subprocess
import time

from dbus.mainloop.glib import DBusGMainLoop
import dbus.service

from PySide.QtCore import QUrl
from PySide.QtCore import Qt
from PySide.QtCore import Signal
from PySide.QtCore import Slot
from PySide.QtDeclarative import QDeclarativeView

import gpodder

from gpodder import common
from gpodder import core
from gpodder import my
from gpodder import util

from gpodder import qml
from gpodder.qml import helper
from gpodder.qml import images
from gpodder.qml.common import EPISODE_LIST_FILTERS
from gpodder.qml.common import QML
from gpodder.qml.common import QObjectProxy
from gpodder.qml.common import _, N_
from gpodder.qml.configproxy import ConfigProxy
from gpodder.qml.controller import CommonController as QmlCommonController
from gpodder.qml.controller import CommonQtPodder as QmlCommonQtPodder
from gpodder.qml.mobile import model

import logging
logger = logging.getLogger("qmlui")


def grouped(iterable, n):
    return itertools.izip(*[iter(iterable)] * n)


class Controller(QmlCommonController):
    def __init__(self, root):
        QmlCommonController.__init__(self, root)


class DeclarativeView(QDeclarativeView):
    def __init__(self):
        QDeclarativeView.__init__(self)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.viewport().setAttribute(Qt.WA_OpaquePaintEvent)
        self.viewport().setAttribute(Qt.WA_NoSystemBackground)

#    def paintEvent(self, event):
#        old = time.time()
#        QDeclarativeView.paintEvent(self, event)
#        fps = 1. / (time.time() - old)
#        if fps < 60:
#            print 'FPS: %2.0f' % fps

    closing = Signal()

    def closeEvent(self, event):
        self.closing.emit()
        event.ignore()


class qtPodder(QmlCommonQtPodder):
    def __init__(self, args, gpodder_core, dbus_bus_name):
        QmlCommonQtPodder.__init__(self, args, gpodder_core, dbus_bus_name)

        self.episodeUpdated.connect(self.on_episode_updated)
        self.setEpisodeListModel.connect(self.on_set_episode_list_model)

        self.view = DeclarativeView()
        self.view.closing.connect(self.on_quit)
        self.view.setResizeMode(QDeclarativeView.SizeRootObjectToView)

        self.controller = Controller(self)
        self.media_buttons_handler = helper.MediaButtonsHandler()
        self.tracker_miner_config = helper.TrackerMinerConfig()
        self.podcast_model = qml.model.gPodderPodcastListModel()
        self.episode_model = model.gPodderEpisodeListModel(self.config, self)
        self.last_episode = None

        # A dictionary of episodes that are currently active
        # in some way (i.e. playing back or downloading)
        self.active_episode_wrappers = {}

        engine = self.view.engine()

        # Add the cover art image provider
        self.cover_provider = images.LocalCachedImageProvider()
        engine.addImageProvider('cover', self.cover_provider)

        root_context = self.view.rootContext()
        root_context.setContextProperty('controller', self.controller)
        root_context.setContextProperty('configProxy', self.config_proxy)
        root_context.setContextProperty('mediaButtonsHandler',
                self.media_buttons_handler)
        root_context.setContextProperty('trackerMinerConfig',
                self.tracker_miner_config)

        # Load the QML UI (this could take a while...)
        self.view.setSource(QUrl.fromLocalFile(QML('main_default.qml')))

        # Proxy to the "main" QML object for direct access to Qt Properties
        self.main = QObjectProxy(self.view.rootObject().property('main'))

        self.main.podcastModel = self.podcast_model
        self.main.episodeModel = self.episode_model

        self.view.setWindowTitle('gPodder')

        if gpodder.ui.harmattan:
            self.view.showFullScreen()
        else:
            # On the Desktop, scale to fit my small laptop screen..
            desktop = self.app.desktop()
            if desktop.height() < 1000:
                FACTOR = .8
                self.view.scale(FACTOR, FACTOR)
                size = self.view.size()
                size *= FACTOR
                self.view.resize(size)
            self.view.show()

        self.do_start_progress.connect(self.on_start_progress)
        self.do_end_progress.connect(self.on_end_progress)
        self.do_show_message.connect(self.on_show_message)

        podcasts = self.load_podcasts()

        self.resumable_episodes = None
        self.do_offer_download_resume.connect(self.on_offer_download_resume)
        util.run_in_background(self.find_partial_downloads(podcasts))

    quit = Signal()

    def on_quit(self):
        # Make sure the audio playback is stopped immediately
        self.main.togglePlayback(None)
        self.save_pending_data()
        self.view.hide()
        self.core.shutdown()
        self.app.quit()

    episodeUpdated = Signal(int)

    def on_episode_updated(self, episode_id):
        self.main.episodeUpdated(episode_id)

    setEpisodeListModel = Signal(object)

    def on_set_episode_list_model(self, prepared):
        self.main.setEpisodeListModel(prepared)

    do_start_progress = Signal(str)

    @Slot(str)
    def on_start_progress(self, text):
        self.main.startProgress(text)

    def start_progress(self, text=_('Please wait...')):
        self.do_start_progress.emit(text)


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
