#!/usr/bin/python
# gPodder Qt demo app in 100 lines of Python (line width < 80)
# Thomas Perl <thpinfo.com>; 2010-01-15

from PySide.QtGui import *
from PySide.QtCore import *

import sys
import os
import gpodder

from gpodder import model
from gpodder import dbsqlite
from gpodder import config
from gpodder import util

class gPodderListModel(QAbstractListModel):
    def __init__(self, objects):
        QAbstractListModel.__init__(self)
        self._objects = objects

    def get_object(self, index):
        return self._objects[index.row()]

    def rowCount(self, parent=QModelIndex()):
        return len(self._objects)

    def data(self, index, role):
        if index.isValid() and role == Qt.DisplayRole:
            return self._format(self.get_object(index))
        return None

    def _format(self, o):
        return o.title.decode('utf-8')

class EpisodeModel(gPodderListModel):
    def _format(self, episode):
        title = episode.title.decode('utf-8')
        if episode.was_downloaded(and_exists=True):
            return u'[DL] ' + title
        return title

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

class qtPodder(QApplication):
    def __init__(self, args, config, db):
        QApplication.__init__(self, args)

        podcasts = model.PodcastChannel.load_from_db(db, config.download_dir)

        self.podcast_list = gPodderListView(self.on_podcast_selected)
        self.podcast_list.setModel(gPodderListModel(podcasts))

        self.podcast_window = QMainWindow()
        self.podcast_window.setWindowTitle('gPodder Podcasts in Qt')
        self.podcast_window.setCentralWidget(self.podcast_list)
        self.podcast_window.show()

    def on_podcast_selected(self, podcast):
        self.episode_list = gPodderListView(self.on_episode_selected)
        self.episode_list.setModel(EpisodeModel(podcast.get_all_episodes()))

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

if __name__ == '__main__':
    config = config.Config(gpodder.config_file)
    db = dbsqlite.Database(gpodder.database_file)

    if os.path.exists('/etc/event.d/hildon-desktop'):
        gpodder.ui.fremantle = True
    else:
        gpodder.ui.desktop = True

    gui = qtPodder(sys.argv, config, db)
    sys.exit(gui.exec_())

