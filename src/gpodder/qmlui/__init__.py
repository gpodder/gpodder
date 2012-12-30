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


from PySide.QtGui import QApplication
from PySide.QtCore import Qt, QObject, Signal, Slot, Property, QUrl
from PySide.QtCore import QAbstractListModel, QModelIndex
from PySide.QtDeclarative import QDeclarativeView

import os
import signal
import functools
import itertools
import subprocess

import dbus
import dbus.service

from dbus.mainloop.glib import DBusGMainLoop


import gpodder

_ = gpodder.gettext
N_ = gpodder.ngettext

from gpodder import core
from gpodder import util
from gpodder import my
from gpodder import query
from gpodder import common

from gpodder.model import Model

from gpodder.qmlui import model
from gpodder.qmlui import helper
from gpodder.qmlui import images

import logging
logger = logging.getLogger("qmlui")


EPISODE_LIST_FILTERS = [
    # (UI label, EQL expression)
    (_('All'), None),
    (_('Hide deleted'), 'not deleted'),
    (_('New'), 'new or downloading'),
    (_('Downloaded'), 'downloaded or downloading'),
    (_('Deleted'), 'deleted'),
    (_('Finished'), 'finished'),
    (_('Archived'), 'downloaded and archive'),
    (_('Videos'), 'video'),
    (_('Partially played'), 'downloaded and played and not finished'),
    (_('Unplayed downloads'), 'downloaded and not played'),
]

EPISODE_LIST_LIMIT = 200

def grouped(iterable, n):
    return itertools.izip(*[iter(iterable)]*n)

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


class Controller(QObject):
    def __init__(self, root):
        QObject.__init__(self)
        self.root = root
        self.context_menu_actions = []
        self.episode_list_title = u''
        self.current_input_dialog = None
        self.root.config.add_observer(self.on_config_changed)
        self._flattr = self.root.core.flattr
        self.flattr_button_text = u''
        self._busy = False
        self.updating_podcasts = 0

    def on_config_changed(self, name, old_value, new_value):
        logger.info('Config changed: %s (%s -> %s)', name,
                old_value, new_value)
        if name == 'mygpo.enabled':
            self.myGpoEnabledChanged.emit()
        elif name == 'mygpo.username':
            self.myGpoUsernameChanged.emit()
        elif name == 'mygpo.password':
            self.myGpoPasswordChanged.emit()
        elif name == 'mygpo.device.caption':
            self.myGpoDeviceCaptionChanged.emit()

    busyChanged = Signal()

    def getBusy(self):
        return self._busy

    def setBusy(self, busy):
        if self._busy != busy:
            self._busy = busy
            self.busyChanged.emit()

    busy = Property(bool, getBusy, setBusy, notify=busyChanged)

    episodeListTitleChanged = Signal()

    def setEpisodeListTitle(self, title):
        if self.episode_list_title != title:
            self.episode_list_title = title
            self.episodeListTitleChanged.emit()

    def getEpisodeListTitle(self):
        return self.episode_list_title

    episodeListTitle = Property(unicode, getEpisodeListTitle, \
            setEpisodeListTitle, notify=episodeListTitleChanged)

    flattrButtonTextChanged = Signal()

    def setFlattrButtonText(self, flattr_button_text):
        if self.flattr_button_text != flattr_button_text:
            self.flattr_button_text = flattr_button_text
            self.flattrButtonTextChanged.emit()

    def getFlattrButtonText(self):
        return self.flattr_button_text

    flattrButtonText = Property(unicode, getFlattrButtonText,
            setFlattrButtonText, notify=flattrButtonTextChanged)

    @Slot(QObject)
    def onPlayback(self, qepisode):
        if (qepisode.payment_url and self.root.config.flattr.token and
                self.root.config.flattr.flattr_on_play):
            success, message = self._flattr.flattr_url(qepisode.payment_url)
            if not success:
                logger.warn('Flattr message on playback action: %s', message)

    @Slot(QObject)
    def updateFlattrButtonText(self, qepisode):
        self.setFlattrButtonText('')

        if qepisode is None:
            return

        episode = qepisode._episode

        if not episode.payment_url:
            return
        if not self._flattr.has_token():
            self.setFlattrButtonText(_('Sign in'))
            return

        @util.run_in_background
        def get_flattr_info():
            flattrs, flattred = self._flattr.get_thing_info(episode.payment_url)

            if flattred:
                self.setFlattrButtonText(_('Flattred (%(count)d)') % {
                    'count': flattrs
                })
            else:
                self.setFlattrButtonText(_('Flattr this (%(count)d)') % {
                    'count': flattrs
                })

    @Slot(QObject)
    def flattrEpisode(self, qepisode):
        if not qepisode:
            return

        episode = qepisode._episode

        if not episode.payment_url:
            return
        if not self._flattr.has_token():
            self.root.show_message(_('Sign in to Flattr in the settings.'))
            return

        self.root.start_progress(_('Flattring episode...'))

        @util.run_in_background
        def flattr_episode():
            try:
                success, message = self._flattr.flattr_url(episode.payment_url)
                if success:
                    self.updateFlattrButtonText(qepisode)
                else:
                    self.root.show_message(message)
            finally:
                self.root.end_progress()

    @Slot(result=str)
    def getFlattrLoginURL(self):
        return self._flattr.get_auth_url()

    @Slot(result=str)
    def getFlattrCallbackURL(self):
        return self._flattr.CALLBACK

    @Slot(str)
    def processFlattrCode(self, url):
        if not self._flattr.process_retrieved_code(url):
            self.root.show_message(_('Could not log in to Flattr.'))

    @Slot(result='QStringList')
    def getEpisodeListFilterNames(self):
        return [caption for caption, eql in EPISODE_LIST_FILTERS]

    @Slot('QVariant', str)
    def multiEpisodeAction(self, selected, action):
        if not selected:
            return

        count = len(selected)
        episodes = map(self.root.episode_model.get_object_by_index, selected)

        def delete():
            for episode in episodes:
                if not episode.qarchive:
                    episode.delete_episode()
            self.update_subset_stats()
            self.root.mygpo_client.on_delete(episodes)
            self.root.mygpo_client.flush()
            for episode in episodes:
                self.root.on_episode_deleted(episode)
            self.root.episode_model.sort()

        if action == 'delete':
            msg = N_('Delete %(count)d episode?', 'Delete %(count)d episodes?', count) % {'count':count}
            self.confirm_action(msg, _('Delete'), delete)
        elif action == 'download':
            for episode in episodes:
                if episode.qdownloaded:
                    print '    XXX     already downloaded'
                    continue
                episode.qdownload(self.root.config, self.update_subset_stats)
            self.root.mygpo_client.on_download(episodes)
            self.root.mygpo_client.flush()
        elif action == 'play':
            for episode in episodes:
                self.root.enqueue_episode(episode)

    @Slot(str, result=str)
    def translate(self, x):
        return _(x)

    @Slot(str, str, int, result=str)
    def ntranslate(self, singular, plural, count):
        return N_(singular, plural, count)

    @Slot(str, int, result=str)
    def formatCount(self, template, count):
        return template % {'count': count}

    @Slot(result=str)
    def getVersion(self):
        return gpodder.__version__

    @Slot(result=str)
    def getReleased(self):
        return gpodder.__date__

    @Slot(result=unicode)
    def getCredits(self):
        credits_file = os.path.join(gpodder.prefix, 'share', 'gpodder', 'credits.txt')
        return util.convert_bytes(open(credits_file).read())

    @Slot(result=unicode)
    def getCopyright(self):
        return util.convert_bytes(gpodder.__copyright__)

    @Slot(result=str)
    def getLicense(self):
        return gpodder.__license__

    @Slot(result=str)
    def getURL(self):
        return gpodder.__url__

    @Slot()
    def loadLastEpisode(self):
        self.root.load_last_episode()

    @Slot(QObject, int, int)
    def storePlaybackAction(self, episode, start, end):
        self.root.main.episodeUpdated(episode.id)
        if end - 5 < start:
            logger.info('Ignoring too short playback action.')
            return
        total = episode.qduration
        self.root.mygpo_client.on_playback_full(episode, start, end, total)
        self.root.mygpo_client.flush()

    @Slot(QObject)
    def playVideo(self, episode):
        """Video Playback on MeeGo 1.2 Harmattan"""
        if episode.qnew:
            episode.toggle_new()
            self.update_subset_stats()

        url = episode.get_playback_url()
        if gpodder.ui.harmattan:
            subprocess.Popen(['video-suite', url])
        else:
            util.gui_open(url)

        self.root.mygpo_client.on_playback([episode])
        self.root.mygpo_client.flush()

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

    @Slot()
    def myGpoUploadList(self):
        def upload_proc(self):
            self.root.start_progress(_('Uploading subscriptions...'))

            try:
                try:
                    self.root.mygpo_client.set_subscriptions([podcast.url
                        for podcast in self.root.podcast_model.get_podcasts()])
                except Exception, e:
                    self.root.show_message('\n'.join((_('Error on upload:'), unicode(e))))
            finally:
                self.root.end_progress()

        util.run_in_background(lambda: upload_proc(self))

    @Slot()
    def saveMyGpoSettings(self):
        # Update the device settings and upload changes
        self.root.mygpo_client.create_device()
        self.root.mygpo_client.flush(now=True)

    myGpoEnabledChanged = Signal()

    def getMyGpoEnabled(self):
        return self.root.config.mygpo.enabled

    def setMyGpoEnabled(self, enabled):
        self.root.config.mygpo.enabled = enabled

    myGpoEnabled = Property(bool, getMyGpoEnabled,
            setMyGpoEnabled, notify=myGpoEnabledChanged)

    myGpoUsernameChanged = Signal()

    def getMyGpoUsername(self):
        return model.convert(self.root.config.mygpo.username)

    def setMyGpoUsername(self, username):
        self.root.config.mygpo.username = username

    myGpoUsername = Property(unicode, getMyGpoUsername,
            setMyGpoUsername, notify=myGpoUsernameChanged)

    myGpoPasswordChanged = Signal()

    def getMyGpoPassword(self):
        return model.convert(self.root.config.mygpo.password)

    def setMyGpoPassword(self, password):
        self.root.config.mygpo.password = password

    myGpoPassword = Property(unicode, getMyGpoPassword,
            setMyGpoPassword, notify=myGpoPasswordChanged)

    myGpoDeviceCaptionChanged = Signal()

    def getMyGpoDeviceCaption(self):
        return model.convert(self.root.config.mygpo.device.caption)

    def setMyGpoDeviceCaption(self, caption):
        self.root.config.mygpo.device.caption = caption

    myGpoDeviceCaption = Property(unicode, getMyGpoDeviceCaption,
            setMyGpoDeviceCaption, notify=myGpoDeviceCaptionChanged)

    @Slot(QObject)
    def podcastContextMenu(self, podcast):
        menu = []

        if isinstance(podcast, model.EpisodeSubsetView):
            menu.append(helper.Action(_('Update all'), 'update-all', podcast))
        else:
            menu.append(helper.Action(_('Update'), 'update', podcast))
            menu.append(helper.Action(_('Mark episodes as old'), 'mark-as-read', podcast))
            menu.append(helper.Action(_('Rename'), 'rename-podcast', podcast))
            menu.append(helper.Action(_('Change section'), 'change-section', podcast))
            menu.append(helper.Action(_('Unsubscribe'), 'unsubscribe', podcast))

        #menu.append(helper.Action('Force update all', 'force-update-all', podcast))
        #menu.append(helper.Action('Force update', 'force-update', podcast))

        self.show_context_menu(menu)

    def show_context_menu(self, actions):
        if gpodder.ui.harmattan:
            actions = filter(lambda a: a.caption != '', actions)
        self.context_menu_actions = actions
        self.root.open_context_menu(self.context_menu_actions)

    def finished_update(self):
        if self.updating_podcasts > 0:
            self.updating_podcasts = self.updating_podcasts - 1
            if self.updating_podcasts == 0:
                self.setBusy(False)
        self.update_subset_stats()

    def update_subset_stats(self):
        # This should be called when an episode changes state,
        # so that all subset views (e.g. "All episodes") can
        # update its status (i.e. download/new counts, etc..)
        for podcast in self.root.podcast_model.get_objects():
            if isinstance(podcast, model.EpisodeSubsetView):
                podcast.qupdate()

    def find_episode(self, podcast_url, episode_url):
        for podcast in self.root.podcast_model.get_podcasts():
            if podcast.url == podcast_url:
                for episode in podcast.get_all_episodes():
                    if episode.url == episode_url:
                        return episode
        return None

    @Slot()
    def updateAllPodcasts(self):
        self.setBusy(True)
        if not self.request_connection():
            self.setBusy(False)
            return

        # Process episode actions received from gpodder.net
        def merge_proc(self):
            self.root.start_progress(_('Merging episode actions...'))

            def find_episode(podcast_url, episode_url, counter):
                counter['x'] += 1
                self.root.start_progress(_('Merging episode actions (%d)')
                        % counter['x'])
                return self.find_episode(podcast_url, episode_url)

            try:
                d = {'x': 0} # Used to "remember" the counter inside find_episode
                self.root.mygpo_client.process_episode_actions(lambda x, y:
                        find_episode(x, y, d))
            finally:
                self.root.end_progress()
                
        util.run_in_background(lambda: merge_proc(self))

        for podcast in self.root.podcast_model.get_objects():
            if not podcast.pause_subscription and not podcast.qupdating:
                if podcast.qtitle != 'All episodes':
                    self.updating_podcasts = self.updating_podcasts + 1
                podcast.qupdate(finished_callback=self.finished_update)
        if self.updating_podcasts == 0:
            self.setBusy(False)

    def request_connection(self):
        """Request an internet connection

        Returns True if a connection is available, False otherwise
        """
        if not util.connection_available():
            # TODO: Try to request the network connection dialog, and wait
            # for a connection - if a connection is available, return True

            self.root.show_message('\n\n'.join((_('No network connection'),
                _('Please connect to a network, then try again.'))))
            return False

        return True

    @Slot(int)
    def contextMenuResponse(self, index):
        assert index < len(self.context_menu_actions)
        action = self.context_menu_actions[index]
        if action.action == 'update':
            if not self.request_connection():
                return
            podcast = action.target
            if not podcast.pause_subscription:
                podcast.qupdate(finished_callback=self.update_subset_stats)
        elif action.action == 'force-update':
            action.target.qupdate(force=True, \
                    finished_callback=self.update_subset_stats)
        elif action.action == 'update-all':
            self.updateAllPodcasts()
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
            self.root.main.episodeUpdated(action.target.id)
            self.update_subset_stats()
        elif action.action == 'episode-toggle-archive':
            action.target.toggle_archive()
            self.root.main.episodeUpdated(action.target.id)
            self.update_subset_stats()
        elif action.action == 'episode-delete':
            self.deleteEpisode(action.target)
        elif action.action == 'episode-enqueue':
            self.root.enqueue_episode(action.target)
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

    def confirm_action(self, message, affirmative, callback,
            negative_callback=None):
        def confirm(message, affirmative, callback, negative_callback):
            args = (message, '', affirmative, _('Cancel'), False)
            if (yield args):
                callback()
            elif negative_callback is not None:
                negative_callback()

        self.start_input_dialog(confirm(message, affirmative, callback,
            negative_callback))

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
        episode.qdownload(self.root.config, self.update_subset_stats,
                self.root.episodeUpdated.emit)
        self.root.mygpo_client.on_download([episode])
        self.root.mygpo_client.flush()

    @Slot(QObject)
    def cancelDownload(self, episode):
        episode.download_task.cancel()
        episode.download_task.removed_from_list()
        self.root.main.episodeUpdated(episode.id)

    @Slot(QObject)
    def deleteEpisode(self, episode):
        def delete():
            episode.delete_episode()
            self.root.main.episodeUpdated(episode.id)
            self.update_subset_stats()
            self.root.mygpo_client.on_delete([episode])
            self.root.mygpo_client.flush()
            self.root.on_episode_deleted(episode)
            self.root.episode_model.sort()

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

        if episode.state != gpodder.STATE_DELETED:
            menu.append(helper.Action(_('Delete'), 'episode-delete', episode))

        menu.append(helper.Action(_('Add to play queue'), 'episode-enqueue', episode))

        self.show_context_menu(menu)

    @Slot('QVariant')
    def addSubscriptions(self, urls):
        def not_yet_subscribed(url):
            for podcast in self.root.podcast_model.get_objects():
                if isinstance(podcast, model.EpisodeSubsetView):
                    continue

                if podcast.url == url:
                    logger.info('Already subscribed: %s', url)
                    return False

            return True

        urls = map(util.normalize_feed_url, urls)
        urls = filter(not_yet_subscribed, urls)

        def subscribe_proc(self, urls):
            self.root.start_progress(_('Adding podcasts...'))
            try:
                for idx, url in enumerate(urls):
                    print idx, url
                    self.root.start_progress(_('Adding podcasts...') + ' (%d/%d)' % (idx, len(urls)))
                    try:
                        podcast = self.root.model.load_podcast(url=url, create=True,
                                max_episodes=self.root.config.max_episodes_per_feed)
                        podcast.save()
                        self.root.insert_podcast(model.QPodcast(podcast))
                    except Exception, e:
                        logger.warn('Cannot add pocast: %s', e)
                        # XXX: Visual feedback in the QML UI
            finally:
                self.root.end_progress()

        util.run_in_background(lambda: subscribe_proc(self, urls))

    @Slot()
    def currentEpisodeChanging(self):
        self.root.save_pending_data()

    @Slot()
    def quit(self):
        self.root.quit.emit()

    @Slot()
    def switcher(self):
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
        return len(self.get_objects())

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

class gPodderEpisodeListModel(gPodderListModel):
    def __init__(self, config, root):
        gPodderListModel.__init__(self)
        self._filter = config.ui.qml.state.episode_list_filter
        self._filtered = []
        self._processed = []
        self._is_subset_view = False

        self._config = config
        self._root = root
        config.add_observer(self._on_config_changed)

    is_subset_view_changed = Signal()

    def get_is_subset_view(self):
        return self._is_subset_view

    def set_is_subset_view(self, is_subset_view):
        if is_subset_view != self.is_subset_view:
            self._is_subset_view = is_subset_view
            self.is_subset_view_changed.emit()

    is_subset_view = Property(bool, get_is_subset_view,
            set_is_subset_view, notify=is_subset_view_changed)

    def _on_config_changed(self, name, old_value, new_value):
        if name == 'ui.qml.state.episode_list_filter':
            self._filter = new_value
            self.sort()

    def sort(self):
        self._root.main.clearEpisodeListModel()

        @util.run_in_background
        def filter_and_load_episodes():
            caption, eql = EPISODE_LIST_FILTERS[self._filter]

            if eql is None:
                self._filtered = self._objects
            else:
                eql = query.EQL(eql)
                match = lambda episode: eql.match(episode._episode)
                self._filtered = filter(match, self._objects)

            def to_dict(episode):
                return {
                    'episode_id': episode._episode.id,

                    'episode': episode,

                    'title': episode.qtitle,
                    'podcast': episode.qpodcast,
                    'cover_url': episode.qpodcast.qcoverart,
                    'filetype': episode.qfiletype,

                    'duration': episode.qduration,
                    'downloading': episode.qdownloading,
                    'position': episode.qposition,
                    'progress': episode.qprogress,
                    'downloaded': episode.qdownloaded,
                    'isnew': episode.qnew,
                    'archive': episode.qarchive,
                }

            processed = map(to_dict, self._filtered[:EPISODE_LIST_LIMIT])
            self._root.setEpisodeListModel.emit(processed)

            # Keep a reference here to avoid crashes
            self._processed = processed

    def get_objects(self):
        return self._filtered

    def get_object(self, index):
        return self._filtered[index.row()]

    @Slot(int, result=QObject)
    def get_object_by_index(self, index):
        return self._filtered[int(index)]

    @Slot(result=int)
    def getFilter(self):
        return self._filter

    @Slot(int)
    def setFilter(self, filter_index):
        self._config.ui.qml.state.episode_list_filter = filter_index


def QML(filename):
    for folder in gpodder.ui_folders:
        filename = os.path.join(folder, filename)
        if os.path.exists(filename):
            return filename

import time

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

class qtPodder(QObject):
    def __init__(self, args, gpodder_core, dbus_bus_name):
        QObject.__init__(self)

        self.dbus_bus_name = dbus_bus_name
        # TODO: Expose the same D-Bus API as the Gtk UI D-Bus object (/gui)
        # TODO: Create a gpodder.dbusproxy.DBusPodcastsProxy object (/podcasts)

        self.app = QApplication(args)
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        self.quit.connect(self.on_quit)
        self.episodeUpdated.connect(self.on_episode_updated)
        self.setEpisodeListModel.connect(self.on_set_episode_list_model)

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

        self.view = DeclarativeView()
        self.view.closing.connect(self.on_quit)
        self.view.setResizeMode(QDeclarativeView.SizeRootObjectToView)

        self.controller = Controller(self)
        self.media_buttons_handler = helper.MediaButtonsHandler()
        self.tracker_miner_config = helper.TrackerMinerConfig()
        self.podcast_model = gPodderPodcastListModel()
        self.episode_model = gPodderEpisodeListModel(self.config, self)
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
        self.main = helper.QObjectProxy(self.view.rootObject().property('main'))

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

