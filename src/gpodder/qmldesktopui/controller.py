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

import os
import subprocess
from PySide.QtCore import QObject, Signal, Slot, Property

import gpodder
from gpodder import util
from qmlcommon import _, N_, EPISODE_LIST_FILTERS

import helper
import model

import logging
logger = logging.getLogger(__name__)

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
        if not self.request_connection():
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
            if not podcast.pause_subscription:
                podcast.qupdate(finished_callback=self.update_subset_stats)

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
            self.update_subset_stats()
        elif action.action == 'episode-toggle-archive':
            action.target.toggle_archive()
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
        episode.qdownload(self.root.config, self.update_subset_stats)
        self.root.mygpo_client.on_download([episode])
        self.root.mygpo_client.flush()

    @Slot(QObject)
    def cancelDownload(self, episode):
        episode.download_task.cancel()
        episode.download_task.removed_from_list()

    @Slot(QObject)
    def deleteEpisode(self, episode):
        def delete():
            episode.delete_episode()
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