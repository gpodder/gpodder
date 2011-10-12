# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
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


from PySide.QtGui import QApplication
from PySide.QtCore import Qt, QObject, Signal, Slot, Property
from PySide.QtCore import QAbstractListModel, QModelIndex
from PySide.QtDeclarative import QDeclarativeView

import os
import threading
import signal
import functools
import gpodder

_ = gpodder.gettext
N_ = gpodder.ngettext

from gpodder import core
from gpodder import util

from gpodder.model import Model

from gpodder.qmlui import model
from gpodder.qmlui import helper
from gpodder.qmlui import images

from gpodder.plugins import woodchuck

import logging
logger = logging.getLogger("qmlui")

class Controller(QObject):
    def __init__(self, root):
        QObject.__init__(self)
        self.root = root
        self.context_menu_actions = []
        self.episode_list_title = u''
        self.current_input_dialog = None

    episodeListTitleChanged = Signal()

    def setEpisodeListTitle(self, title):
        if self.episode_list_title != title:
            self.episode_list_title = title
            self.episodeListTitleChanged.emit()

    def getEpisodeListTitle(self):
        return self.episode_list_title

    episodeListTitle = Property(unicode, getEpisodeListTitle, \
            setEpisodeListTitle, notify=episodeListTitleChanged)

    @Slot(str, result=str)
    def translate(self, x):
        return _(x)

    @Slot(str, str, int, result=str)
    def ntranslate(self, singular, plural, count):
        return N_(singular, plural, count)

    @Slot()
    def loadLastEpisode(self):
        self.root.load_last_episode()

    @Slot(QObject)
    def podcastSelected(self, podcast):
        self.setEpisodeListTitle(podcast.qtitle)
        self.root.select_podcast(podcast)

    windowTitleChanged = Signal()

    def getWindowTitle(self):
        return self.root.view.windowTitle()

    def setWindowTitle(self, windowTitle):
        self.root.view.setWindowTitle(windowTitle)

    windowTitle = Property(unicode, getWindowTitle,
            setWindowTitle, notify=windowTitleChanged)

    @Slot(QObject)
    def podcastContextMenu(self, podcast):
        menu = []

        if isinstance(podcast, model.EpisodeSubsetView):
            menu.append(helper.Action(_('Update all'), 'update-all', podcast))
        else:
            menu.append(helper.Action(_('Update'), 'update', podcast))
            menu.append(helper.Action(_('Mark episodes as old'), 'mark-as-read', podcast))
            menu.append(helper.Action('', '', None))
            menu.append(helper.Action(_('Rename'), 'rename-podcast', podcast))
            menu.append(helper.Action(_('Change section'), 'change-section', podcast))
            menu.append(helper.Action('', '', None))
            menu.append(helper.Action(_('Unsubscribe'), 'unsubscribe', podcast))

        #menu.append(helper.Action('Force update all', 'force-update-all', podcast))
        #menu.append(helper.Action('Force update', 'force-update', podcast))

        self.show_context_menu(menu)

    def show_context_menu(self, actions):
        self.context_menu_actions = actions
        self.root.open_context_menu(self.context_menu_actions)

    def update_subset_stats(self):
        # This should be called when an episode changes state,
        # so that all subset views (e.g. "All episodes") can
        # update its status (i.e. download/new counts, etc..)
        for podcast in self.root.podcast_model.get_objects():
            if isinstance(podcast, model.EpisodeSubsetView):
                podcast.qupdate()

    @Slot(int)
    def contextMenuResponse(self, index):
        assert index < len(self.context_menu_actions)
        action = self.context_menu_actions[index]
        if action.action == 'update':
            action.target.qupdate(finished_callback=self.update_subset_stats)
        elif action.action == 'force-update':
            action.target.qupdate(force=True, \
                    finished_callback=self.update_subset_stats)
        elif action.action == 'update-all':
            for podcast in self.root.podcast_model.get_objects():
                podcast.qupdate(finished_callback=self.update_subset_stats)
        elif action.action == 'force-update-all':
            for podcast in self.root.podcast_model.get_objects():
                podcast.qupdate(force=True, finished_callback=self.update_subset_stats)
        if action.action == 'unsubscribe':
            def unsubscribe():
                action.target.remove_downloaded()
                action.target.delete()
                self.root.remove_podcast(action.target)

            self.confirm_action(_('Remove this podcast and episodes?'),
                    _('Unsubscribe'), unsubscribe)
        elif action.action == 'episode-toggle-new':
            action.target.toggle_new()
            self.update_subset_stats()
        elif action.action == 'episode-toggle-archive':
            action.target.toggle_archive()
            self.update_subset_stats()
        elif action.action == 'mark-as-read':
            for episode in action.target.get_all_episodes():
                if not episode.was_downloaded(and_exists=True):
                    episode.mark(is_played=True)
            action.target.changed.emit()
            self.update_subset_stats()
        elif action.action == 'change-section':
            def section_changer(podcast):
                section = yield (_('New section name:'), podcast.section,
                        _('Rename'))
                if section and section != podcast.section:
                    podcast.set_section(section)
                    self.root.resort_podcast_list()

            self.start_input_dialog(section_changer(action.target))
        elif action.action == 'rename-podcast':
            def title_changer(podcast):
                title = yield (_('New name:'), podcast.title,
                        _('Rename'))
                if title and title != podcast.title:
                    podcast.rename(title)
                    self.root.resort_podcast_list()

            self.start_input_dialog(title_changer(action.target))

    def confirm_action(self, message, affirmative, callback):
        def confirm(message, affirmative, callback):
            args = (message, '', affirmative, _('Cancel'), False)
            if (yield args):
                callback()

        self.start_input_dialog(confirm(message, affirmative, callback))

    def start_input_dialog(self, generator):
        """Carry out an input dialog with the UI

        This function takes a generator function as argument
        which should yield a tuple of arguments for the
        "show_input_dialog" function (i.e. message, default
        value, accept and reject message - only the message
        is mandatory, the other arguments have default values).

        The generator will receive the user's response as a
        result of the yield expression. If the user accepted
        the dialog, a string is returned (the value that has
        been input), otherwise None is returned.

        Example usage:

        def some_function():
            result = yield ('A simple message', 'default value')
            if result is None:
                # user has rejected the dialog
            else:
                # user has accepted, new value in "result"

        start_input_dialog(some_function())
        """
        assert self.current_input_dialog is None
        self.current_input_dialog = generator
        args = generator.next()
        self.root.show_input_dialog(*args)

    @Slot(bool, str, bool)
    def inputDialogResponse(self, accepted, value, is_text):
        if not is_text:
            value = accepted
        elif not accepted:
            value = None

        try:
            self.current_input_dialog.send(value)
        except StopIteration:
            # This is expected, as the generator
            # should only have one yield statement
            pass

        self.current_input_dialog = None

    @Slot(QObject)
    def downloadEpisode(self, episode):
        episode.qdownload(self.root.config, self.update_subset_stats)

    @Slot(QObject)
    def cancelDownload(self, episode):
        episode.download_task.cancel()
        episode.download_task.removed_from_list()

    @Slot(QObject)
    def deleteEpisode(self, episode):
        def delete():
            episode.delete_episode()
            self.update_subset_stats()

        self.confirm_action(_('Delete this episode?'), _('Delete'), delete)

    @Slot(QObject)
    def acquireEpisode(self, episode):
        self.root.add_active_episode(episode)

    @Slot(QObject)
    def releaseEpisode(self, episode):
        self.root.remove_active_episode(episode)

    @Slot()
    def contextMenuClosed(self):
        self.context_menu_actions = []

    @Slot(QObject)
    def episodeContextMenu(self, episode):
        menu = []

        toggle_new = _('Mark as old') if episode.is_new else _('Mark as new')
        menu.append(helper.Action(toggle_new, 'episode-toggle-new', episode))

        toggle_archive = _('Allow deletion') if episode.archive else _('Archive')
        menu.append(helper.Action(toggle_archive, 'episode-toggle-archive', episode))

        self.show_context_menu(menu)

    @Slot(str)
    def addSubscription(self, url):
        url = util.normalize_feed_url(url)

        for podcast in self.root.podcast_model.get_objects():
            if isinstance(podcast, model.EpisodeSubsetView):
                continue

            if podcast.url == url:
                self.root.show_message(_('Podcast already added'))
                self.podcastSelected(podcast)
                return

        def subscribe_proc(self, url):
            # TODO: Show progress indicator
            podcast = self.root.model.load_podcast(url=url, \
                    create=True, \
                    max_episodes=self.root.config.max_episodes_per_feed, \
                    mimetype_prefs=self.root.config.mimetype_prefs)
            podcast.save()
            self.root.insert_podcast(model.QPodcast(podcast))
            # TODO: Present the podcast to the user

        t = threading.Thread(target=subscribe_proc, args=[self, url])
        t.start()

    @Slot()
    def currentEpisodeChanging(self):
        self.root.save_pending_data()

    @Slot()
    def quit(self):
        self.root.quit.emit()

    @Slot()
    def switcher(self):
        if gpodder.ui.harmattan:
            self.root.view.showMinimized()
        elif gpodder.ui.fremantle:
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

    def sort(self):
        # Unimplemented for the generic list model
        self.reset()

    def insert_object(self, o):
        self._objects.append(o)
        self.sort()

    def remove_object(self, o):
        self._objects.remove(o)
        self.reset()

    def set_objects(self, objects):
        self._objects = objects
        self.sort()

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

class gPodderPodcastListModel(gPodderListModel):
    def set_podcasts(self, db, podcasts):
        views = [
            model.EpisodeSubsetView(db, self, _('All episodes'), ''),
        ]
        self.set_objects(views + podcasts)

    def get_podcasts(self):
        return filter(lambda podcast: isinstance(podcast, model.QPodcast),
                self.get_objects())

    def sort(self):
        self._objects = sorted(self._objects, key=model.QPodcast.sort_key)
        self.reset()

def QML(filename):
    for folder in gpodder.ui_folders:
        filename = os.path.join(folder, filename)
        if os.path.exists(filename):
            return filename

class DeclarativeView(QDeclarativeView):
    def __init__(self):
        QDeclarativeView.__init__(self)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.viewport().setAttribute(Qt.WA_OpaquePaintEvent)
        self.viewport().setAttribute(Qt.WA_NoSystemBackground)

    closing = Signal()

    def closeEvent(self, event):
        self.closing.emit()
        event.ignore()

class qtPodder(QObject):
    def __init__(self, args, gpodder_core):
        QObject.__init__(self)

        # Enable OpenGL rendering without requiring QtOpenGL
        # On Harmattan we let the system choose the best graphicssystem
        if '-graphicssystem' not in args and not gpodder.ui.harmattan:
            args += ['-graphicssystem', 'opengl']

        self.app = QApplication(args)
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        self.quit.connect(self.on_quit)

        self.core = gpodder_core
        self.config = self.core.config
        self.db = self.core.db
        self.model = self.core.model

        self.view = DeclarativeView()
        self.view.closing.connect(self.on_quit)
        self.view.setResizeMode(QDeclarativeView.SizeRootObjectToView)

        self.controller = Controller(self)
        self.media_buttons_handler = helper.MediaButtonsHandler()
        self.podcast_model = gPodderPodcastListModel()
        self.episode_model = gPodderListModel()
        self.last_episode = None

        # A dictionary of episodes that are currently active
        # in some way (i.e. playing back or downloading)
        self.active_episode_wrappers = {}

        engine = self.view.engine()

        # Maemo 5: Experimental Qt Mobility packages are installed in /opt
        if gpodder.ui.fremantle:
            for path in ('/opt/qtm11/imports', '/opt/qtm12/imports'):
                engine.addImportPath(path)

        # Add the cover art image provider
        self.cover_provider = images.LocalCachedImageProvider()
        engine.addImageProvider('cover', self.cover_provider)

        root_context = self.view.rootContext()
        root_context.setContextProperty('controller', self.controller)
        root_context.setContextProperty('mediaButtonsHandler',
                self.media_buttons_handler)

        # Load the QML UI (this could take a while...)
        if gpodder.ui.harmattan:
            self.view.setSource(QML('main_harmattan.qml'))
        else:
            self.view.setSource(QML('main_default.qml'))

        # Proxy to the "main" QML object for direct access to Qt Properties
        self.main = helper.QObjectProxy(self.view.rootObject().property('main'))

        self.main.podcastModel = self.podcast_model
        self.main.episodeModel = self.episode_model

        self.view.setWindowTitle('gPodder')

        if gpodder.ui.harmattan:
            self.view.showFullScreen()
        elif gpodder.ui.fremantle:
            self.view.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            self.view.showFullScreen()
        else:
            self.view.show()

        self.load_podcasts()

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

    def run(self):
        return self.app.exec_()

    quit = Signal()

    def on_quit(self):
        self.save_pending_data()
        self.core.shutdown()
        self.app.quit()

    def show_message(self, message):
        self.main.showMessage(message)

    def show_input_dialog(self, message, value='', accept=_('OK'),
            reject=_('Cancel'), is_text=True):
        self.main.showInputDialog(message, value, accept, reject, is_text)

    def open_context_menu(self, items):
        self.main.openContextMenu(items)

    def resort_podcast_list(self):
        self.podcast_model.sort()

    def insert_podcast(self, podcast):
        self.podcast_model.insert_object(podcast)

    def remove_podcast(self, podcast):
        self.podcast_model.remove_object(podcast)

    def load_podcasts(self):
        podcasts = map(model.QPodcast, self.model.get_podcasts())
        self.podcast_model.set_podcasts(self.db, podcasts)

        woodchuck.init(podcasts, self.woodchuck_channel_update_cb,
                       self.woodchuck_episode_download_cb)

    def wrap_episode(self, podcast, episode):
        try:
            return self.active_episode_wrappers[episode.id]
        except KeyError:
            return model.QEpisode(self, podcast, episode)

    def select_podcast(self, podcast):
        if isinstance(podcast, model.QPodcast):
            # Normal QPodcast instance
            wrap = functools.partial(self.wrap_episode, podcast)
            objects = podcast.get_all_episodes()
        else:
            # EpisodeSubsetView
            wrap = lambda args: self.wrap_episode(*args)
            objects = podcast.get_all_episodes_with_podcast()

        self.episode_model.set_objects(map(wrap, objects))
        self.main.state = 'episodes'

    def save_pending_data(self):
        current_ep = self.main.currentEpisode
        if isinstance(current_ep, model.QEpisode):
            current_ep.save()

    def woodchuck_channel_update_cb(self, channel):
        logger.debug ("woodchuck_channel_update_cb(%s)" % (str (channel),))
        channel.qupdate(finished_callback=self.controller.update_subset_stats)

    def woodchuck_episode_download_cb(self, episode):
        logger.debug ("woodchuck_episode_download_cb(%s)" % (str (episode),))
        episode.qdownload(self.config, self.contoller.update_subset_stats)

def main(args):
    gui = qtPodder(args, core.Core())
    return gui.run()

