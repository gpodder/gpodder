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

class Controller(UiData):
    def __init__(self, root):
        UiData.__init__(self)
        self.root = root
        self.context_menu_actions = []

    @Slot(QObject)
    def podcastSelected(self, podcast):
        print 'selected:', podcast.qtitle
        self.episodeListTitle = podcast.qtitle
        self.root.podcast_window.setWindowTitle(self.episodeListTitle)
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

    @Slot()
    def searchButtonClicked(self):
        self.show_context_menu([
            helper.Action('Search podcasts', 'search-podcasts'),
            helper.Action('Filter current list', 'filter-list'),
        ])

    @Slot()
    def quit(self):
        self.root.save_pending_data()
        self.root._db.close() # store db
        self.root.qml_view.setSource('')
        self.root._app.quit()

    @Slot()
    def switcher(self):
        # FIXME: ugly
        os.system('dbus-send /com/nokia/hildon_desktop '+
                'com.nokia.hildon_desktop.exit_app_view')


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
    def __init__(self, args, config, db):
        self._app = QApplication(args)
        self._config = config
        self._db = db

        self.controller = Controller(self)

        self.qml_view = QDeclarativeView()
        self.glw = QGLWidget()
        self.qml_view.setViewport(self.glw)
        self.qml_view.setResizeMode(QDeclarativeView.SizeRootObjectToView)

        self.podcast_model = gPodderListModel()
        self.episode_model = gPodderListModel()

        self.qml_view.setSource(QML('main.qml'))
        ro = self.qml_view.rootObject()
        ro.setProperty('podcastModel', self.podcast_model)
        ro.setProperty('episodeModel', self.episode_model)
        ro.setProperty('controller', self.controller)

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
        podcasts = sorted(model.Model.get_podcasts(self._db), key=lambda p: p.qsection)
        self.podcast_model.set_objects(podcasts)

    def select_podcast(self, podcast):
        # If the currently-playing episode exists in the podcast,
        # use it instead of the object from the database
        current_ep = self.qml_view.rootObject().property('currentEpisode')
        if not isinstance(current_ep, model.QEpisode):
            setattr(current_ep, 'id', -1)
        episodes = [x if x.id != current_ep.id else current_ep \
                for x in podcast.get_all_episodes()]

        self.episode_model.set_objects(episodes)
        self.set_state('episodes')

    def save_pending_data(self):
        current_ep = self.qml_view.rootObject().property('currentEpisode')
        if isinstance(current_ep, model.QEpisode):
            current_ep.save()

    def select_episode(self, episode):
        self.save_pending_data()
        episode.mark(is_played=True)
        episode.changed.emit()
        self.qml_view.rootObject().setProperty('currentEpisode', episode)
        self.qml_view.rootObject().setCurrentEpisode()

def main():
    gpodder.load_plugins()
    cfg = config.Config(gpodder.config_file)
    db = dbsqlite.Database(gpodder.database_file)
    gui = qtPodder(sys.argv, cfg, db)
    result = gui._app.exec_()
    db.close()
    print 'main finished'
    return result

