#!/usr/bin/python
# gPodder Qt demo app in 100 lines of Python (line width < 80)
# Thomas Perl <thp@gpodder.org>; 2010-01-15

from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtDeclarative import *
from PySide.QtOpenGL import *

import sys
import os
import gpodder

from gpodder.qmlui import model
from gpodder.qmlui import helper
from gpodder import dbsqlite
from gpodder import config
from gpodder import util


# Generate a QObject subclass with notifyable properties
UiData = helper.AutoQObject(
    ('episodeListTitle', unicode),
    name='UiData'
)

class Controller(QObject):
    def __init__(self, root, uidata):
        QObject.__init__(self)
        self.root = root
        self.uidata = uidata
        self.context_menu_actions = []

    @Slot(QObject)
    def podcastSelected(self, podcast):
        print 'selected:', podcast.qtitle
        self.uidata.episodeListTitle = podcast.qtitle
        self.root.podcast_window.setWindowTitle(self.uidata.episodeListTitle)
        self.root.select_podcast(podcast)

    @Slot(QObject)
    def podcastContextMenu(self, podcast):
        print 'context menu:', podcast.qtitle
        self.show_context_menu([
                helper.Action('Update all', 'update_all', podcast),
                helper.Action('Update', 'update', podcast),
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
        elif action.action == 'update_all':
            for podcast in self.root.podcast_model.get_objects():
                podcast.qupdate()
        if action.action == 'unsubscribe':
            print 'would unsubscribe from', action.target.title
        elif action.action == 'episode-toggle-new':
            action.target.mark(is_played=action.target.is_new)
            action.target.changed.emit()

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

    @Slot(str)
    def action(self, action):
        print 'action requested:', action
        if action == 'refresh':
            self.root.reload_podcasts()

    @Slot()
    def quit(self):
        self.root.deleteLater() # XXX

    @Slot()
    def switcher(self):
        # FIXME: ugly
        os.system('dbus-send /com/nokia/hildon_desktop '+
                'com.nokia.hildon_desktop.exit_app_view')


class gPodderListModel(QAbstractListModel):
    COLUMNS = ['object',]

    def __init__(self, objects=None):
        QAbstractListModel.__init__(self)
        if objects is None:
            objects = []
        self._objects = objects
        self.setRoleNames(dict(enumerate(self.COLUMNS)))

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
        if index.isValid() and role == 0:
            return self.get_object(index)
        return None

class gPodderPodcastModel(gPodderListModel):
    COLUMNS = ['podcast',]

class gPodderEpisodeModel(gPodderListModel):
    COLUMNS = ['episode',]

def QML(filename):
    for folder in gpodder.ui_folders:
        filename = os.path.join(folder, filename)
        if os.path.exists(filename):
            return filename

class qtPodder(QApplication):
    def __init__(self, args, config, db):
        QApplication.__init__(self, args)
        self._config = config
        self._db = db

        self.uidata = UiData()
        self.controller = Controller(self, self.uidata)

        self.qml_view = QDeclarativeView()
        self.glw = QGLWidget()
        self.qml_view.setViewport(self.glw)
        self.qml_view.setResizeMode(QDeclarativeView.SizeRootObjectToView)

        rc = self.qml_view.rootContext()
        self.podcast_model = gPodderPodcastModel()
        self.episode_model = gPodderEpisodeModel()
        rc.setContextProperty('podcastModel', self.podcast_model)
        rc.setContextProperty('episodeModel', self.episode_model)
        rc.setContextProperty('controller', self.controller)
        rc.setContextProperty('uidata', self.uidata)
        self.qml_view.setSource(QML('main.qml'))

        self.podcast_window = QMainWindow()
        if gpodder.ui.fremantle:
            self.podcast_window.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
        self.podcast_window.setWindowTitle('gPodder Podcasts in Qt')
        self.podcast_window.setCentralWidget(self.qml_view)
        self.podcast_window.resize(480, 800)
        if gpodder.ui.fremantle:
            self.podcast_window.showFullScreen()
        else:
            self.podcast_window.show()

        self.reload_podcasts()

    def set_state(self, state):
        root = self.qml_view.rootObject()
        root.setProperty('state', state)

    def open_context_menu(self, items):
        root = self.qml_view.rootObject()
        root.openContextMenu(items)

    def reload_podcasts(self):
        self.podcast_model.set_objects(model.Model.get_podcasts(self._db))

    def select_podcast(self, podcast):
        self.episode_model.set_objects(podcast.get_all_episodes())
        self.set_state('episodes')

    def select_episode(self, episode):
        self.qml_view.rootObject().setCurrentEpisode(episode)

def main():
    gpodder.load_plugins()
    cfg = config.Config(gpodder.config_file)
    db = dbsqlite.Database(gpodder.database_file)
    gui = qtPodder(sys.argv, cfg, db)
    return gui.exec_()

