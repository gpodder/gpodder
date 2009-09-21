# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
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
import gtk.gdk
import pango
import urllib2
import threading

from xml.sax import saxutils

import gpodder

_ = gpodder.gettext

from gpodder import util

from gpodder.gtkui.interface.common import BuilderWidget
from gpodder.gtkui.interface.shownotes import gPodderShownotesBase

class gPodderShownotes(gPodderShownotesBase):
    def on_create_window(self):
        self.text_buffer = gtk.TextBuffer()
        self.text_buffer.create_tag('heading', scale=pango.SCALE_LARGE, \
                weight=pango.WEIGHT_BOLD)
        self.text_buffer.create_tag('subheading', scale=pango.SCALE_SMALL)
        self.textview.set_buffer(self.text_buffer)
        # Create the menu and set it for this window (Maybe move
        # this to the .ui file if GtkBuilder allows this)

        import hildon
        appmenu = hildon.AppMenu()
        for action in (self.action_play, \
                       self.action_delete, \
                       self.action_download, \
                       self.action_pause, \
                       self.action_resume, \
                       self.action_cancel, \
                       self.action_mark_as_new, \
                       self.action_mark_as_old, \
                       self.action_visit_website):
            button = gtk.Button()
            action.connect_proxy(button)
            appmenu.append(button)
        appmenu.show_all()
        self.main_window.set_app_menu(appmenu)


    def _on_key_press_event(self, widget, event):
        # Override to provide support for all hardware keys
        if gPodderShownotesBase._on_key_press_event(self, widget, event):
            return True

        if event.keyval == gtk.keysyms.Escape:
            self.on_close_button_clicked()
        elif event.keyval == gtk.keysyms.F7:
            self.on_scroll_down()
        elif event.keyval == gtk.keysyms.F8:
            self.on_scroll_up()
        else:
            return False

        return True

    def on_scroll_down(self):
        if not hasattr(self.scrolled_window, 'get_vscrollbar'):
            return
        vsb = self.scrolled_window.get_vscrollbar()
        vadj = vsb.get_adjustment()
        step = vadj.step_increment
        vsb.set_value(vsb.get_value() + step)

    def on_scroll_up(self):
        if not hasattr(self.scrolled_window, 'get_vscrollbar'):
            return
        vsb = self.scrolled_window.get_vscrollbar()
        vadj = vsb.get_adjustment()
        step = vadj.step_increment
        vsb.set_value(vsb.get_value() - step)

    def on_show_window(self):
        self.download_progress.set_fraction(0)
        self.download_progress.set_text('')
        self.main_window.set_title(self.episode.title)

    def on_display_text(self):
        heading = self.episode.title
        subheading = _('from %s') % (self.episode.channel.title)
        description = self.episode.description

        self.text_buffer.insert_with_tags_by_name(\
                self.text_buffer.get_end_iter(), heading, 'heading')
        self.text_buffer.insert_at_cursor('\n')
        self.text_buffer.insert_with_tags_by_name(\
                self.text_buffer.get_end_iter(), subheading, 'subheading')
        self.text_buffer.insert_at_cursor('\n\n')
        self.text_buffer.insert(self.text_buffer.get_end_iter(), \
                util.remove_html_tags(description))
        self.text_buffer.place_cursor(self.text_buffer.get_start_iter())

    def on_hide_window(self):
        self.episode = None
        self.text_buffer.set_text('')

    def on_episode_status_changed(self):
        downloaded = self.episode.was_downloaded(and_exists=True)
        downloading = self.task is not None and self.task.status in \
                (self.task.QUEUED, self.task.DOWNLOADING, self.task.PAUSED)
        can_set_new_mark = not downloaded and not downloading

        self.download_progress.set_property('visible', \
                self.task is not None and \
                self.task.status != self.task.CANCELLED)
        self.action_play.set_visible(downloaded)
        self.action_delete.set_visible(downloaded)
        self.action_download.set_visible(\
                (self.task is None and not downloaded) or \
                (self.task is not None and \
                 self.task.status in (self.task.CANCELLED, self.task.FAILED)))
        self.action_pause.set_visible(self.task is not None and \
                self.task.status in (self.task.QUEUED, self.task.DOWNLOADING))
        self.action_resume.set_visible(self.task is not None and \
                self.task.status == self.task.PAUSED)
        self.action_cancel.set_visible(downloading)
        self.action_mark_as_new.set_visible(can_set_new_mark and not self.episode_is_new())
        self.action_mark_as_old.set_visible(can_set_new_mark and self.episode_is_new())
        self.action_visit_website.set_visible(self.episode is not None and \
                self.episode.link is not None and \
                self.episode.link != self.episode.url)

    def on_download_status_progress(self):
        if self.task:
            self.download_progress.set_fraction(self.task.progress)
            self.download_progress.set_text('%s: %d%% (%s/s)' % ( \
                    self.task.STATUS_MESSAGE[self.task.status], \
                    100.*self.task.progress, \
                    util.format_filesize(self.task.speed)))

