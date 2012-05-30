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

import gtk

import logging
logger = logging.getLogger(__name__)

import gpodder

_ = gpodder.gettext

from gpodder import util

from gpodder.gtkui.interface.common import BuilderWidget
from gpodder.gtkui.draw import draw_flattr_button

class gPodderShownotesBase(BuilderWidget):
    def new(self):
        setattr(self, 'episode', None)
        setattr(self, 'task', None)

        self._config.connect_gtk_window(self.main_window, \
                'episode_window', True)
        self.main_window.connect('delete-event', self._on_delete_event)
        self.main_window.connect('key-press-event', self._on_key_press_event)
        self.on_create_window()

    def _on_delete_event(self, widget, event):
        self.on_close_button_clicked()
        return True

    def _on_key_press_event(self, widget, event):
        if event.keyval in (gtk.keysyms.J, gtk.keysyms.j):
            self.on_scroll_down()
            return True
        elif event.keyval in (gtk.keysyms.K, gtk.keysyms.k):
            self.on_scroll_up()
            return True

        return False

    #############################################################

    def on_scroll_down(self):
        """Called when the shownotes should scroll down one unit"""
        pass

    def on_scroll_up(self):
        """Called when the shownotes should scroll up one unit"""
        pass

    def on_create_window(self):
        """Called when the window is created (only once!)"""
        pass

    def on_show_window(self):
        """Called when the window is about to be shown"""
        pass

    def on_display_text(self):
        """Called when the shownotes text should be loaded"""
        pass

    def on_hide_window(self):
        """Called when the window is about to be hidden"""
        pass

    def on_download_status_progress(self):
        """Called when the progress info should be updated"""
        pass

    def on_episode_status_changed(self):
        """Called when the episode/download status is changed"""
        pass
        
    #############################################################
    
    def set_flattr_information(self):
        if self.episode.flattr_url:
            flattrs, flattred = self._flattr.get_thing_info(self.episode.flattr_url)
        
            if flattred is None or not self._config.flattr.token:
                flattr_badge = self._flattr.IMAGE_FLATTR_GREY
                self.flattr_possible = False            
            elif flattred:
                flattr_badge = self._flattr.IMAGE_FLATTRED
                self.flattr_possible = False
            else:
                flattr_badge = self._flattr.IMAGE_FLATTR
                self.flattr_possible = True
            
            draw_flattr_button(self.flattr_image, flattr_badge, flattrs)
        
    def on_flattr_button_clicked(self, widget, event):
        if self.flattr_possible:
            status = self._flattr.flattr_url(self.episode.flattr_url)
            self.show_message(status, title='Flattr-Status')
            self.set_flattr_information()

    #############################################################

    def on_play_button_clicked(self, widget=None):
        if self.episode:
            self._playback_episodes([self.episode])

    def on_download_button_clicked(self, widget=None):
        if self.episode:
            self._download_episode_list([self.episode])

    def on_cancel_button_clicked(self, widget=None):
        if self.task:
            self._cancel_task_list([self.task])

    def on_delete_button_clicked(self, widget=None):
        if self.episode and self.episode.was_downloaded(and_exists=True):
            if self._delete_episode_list([self.episode]):
                self.on_episode_status_changed()
                self.on_close_button_clicked()

    def on_mark_as_new_button_clicked(self, widget=None):
        if self.episode:
            self.episode.mark_new()
            self._episode_list_status_changed([self.episode])
            self.on_episode_status_changed()

    def on_do_not_download_button_clicked(self, widget=None):
        if self.episode:
            self.episode.mark_old()
            self._episode_list_status_changed([self.episode])
            self.on_episode_status_changed()

    def on_visit_website_button_clicked(self, widget=None):
        if self.episode and self.episode.link:
            util.open_website(self.episode.link)

    def on_pause_download_button_clicked(self, widget=None):
        if self.task and self.task.status in \
                (self.task.DOWNLOADING, self.task.QUEUED):
            self.task.status = self.task.PAUSED

    def on_resume_download_button_clicked(self, widget=None):
        self.on_download_button_clicked()

    def on_close_button_clicked(self, widget=None):
        self.episode = None
        self.task = None
        self.on_hide_window()
        self.main_window.hide()

    #############################################################

    def _download_status_changed(self, task):
        """Called from main window for download status changes"""
        if self.main_window.get_property('visible'):
            self.task = task
            self.on_episode_status_changed()

    def _download_status_progress(self):
        """Called from main window for progress updates"""
        if self.main_window.get_property('visible'):
            self.on_download_status_progress()

    #############################################################

    def show(self, episode):
        if self.main_window.get_property('visible'):
            if episode == self.episode:
                return

            self.episode = None
            self.task = None
            self.on_hide_window()

        self.episode = episode

        self.on_show_window()
        self.on_episode_status_changed()
        self.main_window.show()
        self.main_window.present()

        # Make sure the window comes up quick
        while gtk.events_pending():
            gtk.main_iteration(False)

        # Load the shownotes into the UI
        self.on_display_text()

        # Set flattr information
        self.set_flattr_information()
