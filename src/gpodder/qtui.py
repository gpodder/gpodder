#!/usr/bin/python
# gPodder Qt demo app in 100 lines of Python (line width < 80)
# Thomas Perl <thp@gpodder.org>; 2010-01-15

from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtDeclarative import *

import sys
import os
import gpodder

from gpodder.qmlui import model
from gpodder import dbsqlite
from gpodder import config
from gpodder import util

class gPodderListModel(QAbstractListModel):
    COLUMNS = ['podcast',]

    def __init__(self, objects):
        QAbstractListModel.__init__(self)
        self._objects = objects
        self.setRoleNames(dict(enumerate(self.COLUMNS)))

    def get_object(self, index):
        return self._objects[index.row()]

    def rowCount(self, parent=QModelIndex()):
        return len(self._objects)

    def data(self, index, role):
        if index.isValid() and role == self.COLUMNS.index('podcast'):
            return self.get_object(index)
        return None

class gPodderListView(QListView):
    def __init__(self, on_item_selected):
        QListView.__init__(self)
        self.setProperty('FingerScrollable', True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._on_item_selected = on_item_selected
        QObject.connect(self, SIGNAL('activated(QModelIndex)'), self._row_cb)

    def _row_cb(self, index):
        if index.isValid():
            model = self.model()
            self._on_item_selected(model.get_object(index))

def QML(filename):
    for folder in gpodder.ui_folders:
        filename = os.path.join(folder, filename)
        if os.path.exists(filename):
            return filename

class qtPodder(QApplication):
    def __init__(self, args, config, db):
        QApplication.__init__(self, args)

        podcasts = model.Model.get_podcasts(db)

        self.podcast_list = QDeclarativeView()
        self.podcast_list.setResizeMode(QDeclarativeView.SizeRootObjectToView)

        rc = self.podcast_list.rootContext()
        self.podcast_model = gPodderListModel(podcasts)
        rc.setContextProperty('podcastModel', self.podcast_model)
        self.podcast_list.setSource(QML('podcastList.qml'))

        self.podcast_window = QMainWindow()
        if gpodder.ui.fremantle:
            self.podcast_window.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
        self.podcast_window.setWindowTitle('gPodder Podcasts in Qt')
        self.podcast_window.setCentralWidget(self.podcast_list)
        self.podcast_window.resize(800, 480)
        self.podcast_window.show()

    def on_podcast_selected(self, podcast):
        self.episode_list = gPodderListView(self.on_episode_selected)
        self.episode_list.setModel(gPodderListModel(podcast.get_all_episodes()))

        self.episode_window = QMainWindow(self.podcast_window)
        window_title = u'Episodes in %s' % podcast.title.decode('utf-8')
        self.episode_window.setWindowTitle(window_title)
        self.episode_window.setCentralWidget(self.episode_list)
        self.episode_window.show()

    def on_episode_selected(self, episode):
        if episode.was_downloaded(and_exists=True):
            util.gui_open(episode.local_filename(create=False))
        else:
            dialog = QMessageBox()
            dialog.setWindowTitle(episode.title.decode('utf-8'))
            dialog.setText('Episode not yet downloaded')
            dialog.exec_()


def main():
    cfg = config.Config(gpodder.config_file)
    db = dbsqlite.Database(gpodder.database_file)
    gui = qtPodder(sys.argv, cfg, db)
    return gui.exec_()

