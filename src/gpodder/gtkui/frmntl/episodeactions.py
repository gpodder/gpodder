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

import gtk
import hildon
import pango
import cgi

import gpodder

_ = gpodder.gettext

from gpodder.gtkui.interface.common import BuilderWidget
from gpodder.gtkui.frmntl import style
from gpodder.gtkui import download
from gpodder.download import DownloadTask

class gPodderEpisodeActions(BuilderWidget):
    BUTTON_HEIGHT = gtk.HILDON_SIZE_FINGER_HEIGHT
    CHOICE_MARK_NEW, CHOICE_MARK_OLD = range(2)
    MODE_NOT_DOWNLOADED, MODE_DOWNLOADING, MODE_DOWNLOADED = range(3)
    MODE_RESUME, MODE_PAUSE = range(2)

    def new(self):
        self.current_mode = -1
        self.pause_resume_mode = -1
        self.episode = None
        self.download_task_monitor = None
        self.action_table = None
        self.should_set_new_value = False
        self.new_keep_value = False

        sub_font = style.get_font_desc('SmallSystemFont')
        sub_color = style.get_color('SecondaryTextColor')
        sub = (sub_font.to_string(), sub_color.to_string())
        self._sub_markup = '<span font_desc="%s" foreground="%s">%%s</span>' % sub

        self.label_description = gtk.Label()
        self.label_description.set_ellipsize(pango.ELLIPSIZE_END)
        self.label_description.set_alignment(0., 0.)
        #self.vbox.pack_start(self.label_description)

    def show_episode(self, episode):
        self.episode = episode

        episode_details = [
                _('Size: %s') % self.episode.get_filesize_string(),
                _('released: %s') % self.episode.cute_pubdate(),
        ]
        episode_details = ', '.join((cgi.escape(x) for x in episode_details))
        self.label_description.set_markup(self._sub_markup % episode_details)

        self.update_action_table()
        self.should_set_new_value = False
        self.should_set_keep_value = False

        self.pause_resume_mode = self.MODE_PAUSE
        self.download_task_monitor = download.DownloadTaskMonitor(self.episode, \
                self.on_can_resume, \
                self.on_can_pause, \
                self.on_finished)
        self.add_download_task_monitor(self.download_task_monitor)

    def on_can_resume(self):
        if self.current_mode != self.MODE_DOWNLOADING:
            self.update_action_table()

        self.pause_resume_mode = self.MODE_RESUME
        self.action_pause_resume.set_property('label', _('Resume download'))
        self.main_window.set_title(self.episode.title)
        hildon.hildon_gtk_window_set_progress_indicator(self.main_window, False)

    def on_can_pause(self):
        if self.current_mode != self.MODE_DOWNLOADING:
            self.update_action_table()

        self.pause_resume_mode = self.MODE_PAUSE
        self.action_pause_resume.set_property('label', _('Pause download'))
        self.main_window.set_title(_('Downloading %s') % self.episode.title)
        hildon.hildon_gtk_window_set_progress_indicator(self.main_window, True)

    def on_finished(self):
        if self.current_mode != self.MODE_DOWNLOADED:
            self.update_action_table()

    def update_action_table(self):
        if self.action_table is not None:
            self.vbox.remove(self.action_table)

        if self.episode.was_downloaded(and_exists=True):
            self.current_mode = self.MODE_DOWNLOADED
            self.main_window.set_title(self.episode.title)
            hildon.hildon_gtk_window_set_progress_indicator(self.main_window, False)
            self.action_table = self.create_ui_downloaded()
        elif self.episode_is_downloading(self.episode):
            self.current_mode = self.MODE_DOWNLOADING
            self.main_window.set_title(_('Downloading %s') % self.episode.title)
            hildon.hildon_gtk_window_set_progress_indicator(self.main_window, True)
            self.action_table = self.create_ui_downloading()
        else:
            self.current_mode = self.MODE_NOT_DOWNLOADED
            self.main_window.set_title(self.episode.title)
            hildon.hildon_gtk_window_set_progress_indicator(self.main_window, False)
            self.action_table = self.create_ui_not_downloaded()
        self.vbox.pack_start(self.action_table)
        self.main_window.show_all()

    def create_ui_not_downloaded(self):
        download_button = hildon.Button(self.BUTTON_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        shownotes_button = hildon.Button(self.BUTTON_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        play_button = hildon.Button(self.BUTTON_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        mark_new_button = hildon.GtkRadioButton(gtk.HILDON_SIZE_FINGER_HEIGHT | gtk.HILDON_SIZE_AUTO_WIDTH)
        mark_old_button = hildon.GtkRadioButton(gtk.HILDON_SIZE_FINGER_HEIGHT | gtk.HILDON_SIZE_AUTO_WIDTH, mark_new_button)

        marknew_actions = gtk.HBox(homogeneous=True)
        for button in (mark_new_button, mark_old_button):
            button.set_mode(False)
            marknew_actions.add(button)

        self.action_play.set_property('label', _('Stream'))
        self.radio_action_mark_new.set_property('label', _('New episode'))
        self.radio_action_mark_old.set_property('label', _('Old episode'))

        self.action_download.connect_proxy(download_button)
        self.action_shownotes.connect_proxy(shownotes_button)
        self.action_play.connect_proxy(play_button)
        self.radio_action_mark_new.connect_proxy(mark_new_button)
        self.radio_action_mark_old.connect_proxy(mark_old_button)

        if self.episode.length > 0:
            download_button.set_title(self.action_download.props.label)
            download_button.set_value(self.episode.get_filesize_string())

        if self.episode.total_time > 0:
            play_button.set_title(self.action_play.props.label)

        mark_new_button.set_active(not self.episode.is_played)
        mark_old_button.set_active(self.episode.is_played)

        table = gtk.Table(2, 2, True)
        table.attach(download_button, 0, 1, 0, 1)
        table.attach(shownotes_button, 1, 2, 0, 1)
        table.attach(play_button, 0, 1, 1, 2)
        table.attach(marknew_actions, 1, 2, 1, 2)
        return table

    def create_ui_downloading(self):
        pause_button = hildon.Button(self.BUTTON_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        shownotes_button = hildon.Button(self.BUTTON_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        cancel_button = hildon.Button(self.BUTTON_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        downloads_button = hildon.Button(self.BUTTON_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)

        self.action_pause_resume.connect_proxy(pause_button)
        self.action_shownotes.connect_proxy(shownotes_button)
        self.action_cancel.connect_proxy(cancel_button)
        self.action_open_downloads.connect_proxy(downloads_button)

        table = gtk.Table(2, 2, True)
        table.attach(pause_button, 0, 1, 0, 1)
        table.attach(shownotes_button, 1, 2, 0, 1)
        table.attach(cancel_button, 0, 1, 1, 2)
        table.attach(downloads_button, 1, 2, 1, 2)
        return table

    def create_ui_downloaded(self):
        play_button = hildon.Button(self.BUTTON_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        shownotes_button = hildon.Button(self.BUTTON_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        delete_button = hildon.Button(self.BUTTON_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        keep_button = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT | gtk.HILDON_SIZE_AUTO_WIDTH)
        keep_button.set_label(_('Keep episode'))
        keep_button.connect('toggled', self.on_keep_toggled)

        self.action_play.set_property('label', _('Play'))
        self.radio_action_mark_new.set_property('label', _('Unplayed'))
        self.radio_action_mark_old.set_property('label', _('Played'))

        self.action_play.connect_proxy(play_button)
        self.action_shownotes.connect_proxy(shownotes_button)
        self.action_delete.connect_proxy(delete_button)

        if self.episode.total_time > 0:
            play_button.set_title(self.action_play.props.label)

        keep_button.set_active(self.episode.is_locked)
        self.new_keep_value = self.episode.is_locked

        self.action_delete.set_sensitive(not self.new_keep_value)

        table = gtk.Table(2, 2, True)
        table.attach(play_button, 0, 1, 0, 1)
        table.attach(shownotes_button, 1, 2, 0, 1)
        table.attach(delete_button, 0, 1, 1, 2)
        table.attach(keep_button, 1, 2, 1, 2)
        return table

    def on_cancel_button_clicked(self, button):
        self.for_each_episode_set_task_status((self.episode,), DownloadTask.CANCELLED)
        self.on_delete_event(button)

    def on_pause_resume_button_clicked(self, button):
        if self.pause_resume_mode == self.MODE_PAUSE:
            self.for_each_episode_set_task_status((self.episode,), DownloadTask.PAUSED)
        else:
            self.for_each_episode_set_task_status((self.episode,), DownloadTask.QUEUED)

    def on_delete_button_clicked(self, button):
        episodes = [self.episode]

        # on_delete_event means the "dialog delete event"
        self.on_delete_event(button)

        self.delete_episode_list(episodes)

    def on_shownotes_button_clicked(self, button):
        self.on_delete_event(button)
        self.show_episode_shownotes(self.episode)

    def on_download_button_clicked(self, button):
        self.on_delete_event(button)
        self.download_episode_list([self.episode])

    def on_play_button_clicked(self, button):
        self.on_delete_event(button)
        self.playback_episodes([self.episode])

    def on_open_downloads_button_clicked(self, button):
        self.on_delete_event(button)
        self.show_episode_in_download_manager(self.episode)

    def on_mark_new_changed(self, action, current):
        self.should_set_new_value = True

    def on_keep_toggled(self, action):
        self.new_keep_value = action.get_active()
        self.action_delete.set_sensitive(not self.new_keep_value)

    def on_delete_event(self, widget, event=None):
        try:
            self.remove_download_task_monitor(self.download_task_monitor)
        except KeyError:
            pass

        self.download_task_monitor = None

        self.main_window.hide()
        while gtk.events_pending():
            gtk.main_iteration(False)

        # Remove action<->widget proxy connections
        for action in (self.action_play, \
                       self.action_download, \
                       self.action_shownotes, \
                       self.action_pause_resume, \
                       self.action_cancel, \
                       self.action_open_downloads, \
                       self.radio_action_mark_new, \
                       self.radio_action_mark_old, \
                       self.action_delete):
            for proxy in action.get_proxies():
                action.disconnect_proxy(proxy)

        changed = False
        if self.should_set_new_value:
            value = self.radio_action_mark_new.get_current_value()
            if value == self.CHOICE_MARK_NEW and \
                    self.episode.is_played:
                self.episode.mark(is_played=False)
                changed = True
            elif value == self.CHOICE_MARK_OLD and \
                    not self.episode.is_played:
                self.episode.mark(is_played=True)
                changed = True
        if self.new_keep_value != self.episode.is_locked:
            self.episode.mark(is_locked=self.new_keep_value)
            changed = True

        if changed:
            self.episode_list_status_changed([self.episode])

        return True

