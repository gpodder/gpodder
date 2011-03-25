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

# gpodder.qmlui - gPodder's QML interface
# Thomas Perl <thp@gpodder.org>; 2011-02-06


from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtDeclarative import *
from PySide.QtOpenGL import *

import os
import gpodder

from gpodder import core

from gpodder.qmlui import model
from gpodder.qmlui import helper
from gpodder.qmlui import images


# Generate a QObject subclass with notifyable properties
UiData = helper.AutoQObject(
    ('episodeListTitle', unicode),
    name='UiData'
)

class Controller(UiData):
    def __init__(self, root):
        UiData.__init__(self)
        self.root = root
        self.context_menu_actions = []

    @Slot(QObject)
    def podcastSelected(self, podcast):
        print 'selected:', podcast.qtitle
        self.episodeListTitle = podcast.qtitle
        self.root.select_podcast(podcast)

    @Slot(str)
    def titleChanged(self, title):
        self.root.view.setWindowTitle(title)

    @Slot(QObject)
    def podcastContextMenu(self, podcast):
        print 'context menu:', podcast.qtitle
        self.show_context_menu([
                helper.Action('Update all', 'update_all', podcast),
                helper.Action('Update', 'update', podcast),
                helper.Action('Force update', 'force-update', podcast),
                helper.Action('Unsubscribe', 'unsubscribe', podcast),
                helper.Action('Be cool', 'be_cool', podcast),
                helper.Action('Sing a song', 'sing_a_song', podcast),
        ])

    def show_context_menu(self, actions):
        self.context_menu_actions = actions
        self.root.open_context_menu(self.context_menu_actions)

    @Slot(int)
    def contextMenuResponse(self, index):
        print 'context menu response:', index
        assert index < len(self.context_menu_actions)
        action = self.context_menu_actions[index]
        if action.action == 'update':
            action.target.qupdate()
        elif action.action == 'force-update':
            action.target.qupdate(force=True)
        elif action.action == 'update_all':
            for podcast in self.root.podcast_model.get_objects():
                podcast.qupdate()
        if action.action == 'unsubscribe':
            print 'would unsubscribe from', action.target.title
        elif action.action == 'episode-toggle-new':
            action.target.mark(is_played=action.target.is_new)
            action.target.changed.emit()
            action.target.channel.changed.emit()

    @Slot()
    def contextMenuClosed(self):
        print 'context menu closed'
        self.context_menu_actions = []

    @Slot(QObject)
    def episodeSelected(self, episode):
        print 'selected:', episode.qtitle
        self.root.select_episode(episode)

    @Slot(QObject)
    def episodeContextMenu(self, episode):
        print 'context menu:', episode.qtitle
        self.show_context_menu([
            helper.Action('Info', 'info', episode),
            helper.Action('Toggle new', 'episode-toggle-new', episode),
        ])

    @Slot()
    def searchButtonClicked(self):
        self.show_context_menu([
            helper.Action('Search podcasts', 'search-podcasts'),
            helper.Action('Filter current list', 'filter-list'),
        ])

    @Slot()
    def quit(self):
        self.root.quit()

    @Slot()
    def switcher(self):
        if gpodder.ui.fremantle:
            os.system('dbus-send /com/nokia/hildon_desktop '+
                    'com.nokia.hildon_desktop.exit_app_view')
        else:
            self.root.view.showMinimized()


class gPodderListModel(QAbstractListModel):
    def __init__(self, objects=None):
        QAbstractListModel.__init__(self)
        if objects is None:
            objects = []
        self._objects = objects
        self.setRoleNames({0: 'modelData', 1: 'section'})

    def set_objects(self, objects):
        self._objects = objects
        self.reset()

    def get_objects(self):
        return self._objects

    def get_object(self, index):
        return self._objects[index.row()]

    def rowCount(self, parent=QModelIndex()):
        return len(self._objects)

    def data(self, index, role):
        if index.isValid():
            if role == 0:
                return self.get_object(index)
            elif role == 1:
                return self.get_object(index).qsection
        return None

def QML(filename):
    for folder in gpodder.ui_folders:
        filename = os.path.join(folder, filename)
        if os.path.exists(filename):
            return filename

class qtPodder(object):
    def __init__(self, args, gpodder_core):
        self.app = QApplication(args)

        self.core = gpodder_core
        self.config = self.core.config
        self.db = self.core.db

        self.view = QDeclarativeView()
        self.glw = QGLWidget()
        self.view.setViewport(self.glw)
        self.view.setResizeMode(QDeclarativeView.SizeRootObjectToView)

        self.controller = Controller(self)
        self.podcast_model = gPodderListModel()
        self.episode_model = gPodderListModel()

        engine = self.view.engine()

        # Maemo 5: Experimental Qt Mobility packages are installed in /opt
        if gpodder.ui.fremantle:
            for path in ('/opt/qtm11/imports', '/opt/qtm12/imports'):
                engine.addImportPath(path)

        # Add the cover art image provider
        self.cover_provider = images.LocalCachedImageProvider()
        engine.addImageProvider('cover', self.cover_provider)

        # Load the QML UI (this could take a while...)
        self.view.setSource(QML('main.qml'))

        # Proxy to the "main" QML object for direct access to Qt Properties
        self.main = helper.QObjectProxy(self.view.rootObject())

        self.main.podcastModel = self.podcast_model
        self.main.episodeModel = self.episode_model
        self.main.controller = self.controller

        self.view.setWindowTitle('gPodder')

        if gpodder.ui.fremantle:
            self.view.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            self.view.showFullScreen()
        else:
            self.view.show()

        self.reload_podcasts()

    def run(self):
        return self.app.exec_()

    def quit(self):
        self.save_pending_data()
        self.core.shutdown()
        self.view.setSource('')
        self.app.quit()

    def open_context_menu(self, items):
        root = self.view.rootObject()
        root.openContextMenu(items)

    def reload_podcasts(self):
        podcasts = sorted(model.Model.get_podcasts(self.db), key=lambda p: p.qsection)
        self.podcast_model.set_objects(podcasts)

    def select_podcast(self, podcast):
        # If the currently-playing episode exists in the podcast,
        # use it instead of the object from the database
        current_ep = self.main.currentEpisode
        if not isinstance(current_ep, model.QEpisode):
            setattr(current_ep, 'id', -1)
        episodes = [x if x.id != current_ep.id else current_ep \
                for x in podcast.get_all_episodes()]

        self.episode_model.set_objects(episodes)
        self.main.state = 'episodes'

    def save_pending_data(self):
        current_ep = self.main.currentEpisode
        if isinstance(current_ep, model.QEpisode):
            current_ep.save()

    def select_episode(self, episode):
        self.save_pending_data()
        episode.playback_mark()
        episode.changed.emit()
        episode.channel.changed.emit()
        self.main.currentEpisode = episode
        self.main.setCurrentEpisode()

def main(args):
    gui = qtPodder(args, core.Core())
    return gui.run()

