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
import gtk.gdk
import pango

import gpodder

_ = gpodder.gettext

from gpodder import util

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
        menu = gtk.Menu()
        menu.append(self.action_play.create_menu_item())
        menu.append(self.action_delete.create_menu_item())
        menu.append(gtk.SeparatorMenuItem())
        menu.append(self.action_download.create_menu_item())
        menu.append(self.action_pause.create_menu_item())
        menu.append(self.action_resume.create_menu_item())
        menu.append(self.action_cancel.create_menu_item())
        menu.append(gtk.SeparatorMenuItem())
        menu.append(self.action_copy_text.create_menu_item())
        menu.append(self.action_visit_website.create_menu_item())
        self.main_window.set_menu(self.set_finger_friendly(menu))

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

    def on_copy_text_button_clicked(self, widget):
        clip_selection = gtk.Clipboard(selection='PRIMARY')
        def receive_selection_text(clipboard, text, data=None):
            if text:
                clip_clipboard = gtk.Clipboard(selection='CLIPBOARD')
                clip_clipboard.set_text(text)
                self.show_message(_('Text copied to clipboard.'))
            else:
                self.show_message(_('Selection is empty.'))
        clip_selection.request_text(receive_selection_text)

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
        subheading = '; '.join((self.episode.cute_pubdate(), \
                self.episode.get_filesize_string(), \
                self.episode.channel.title))
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
        self.download_progress.set_property('visible', \
                self.task is not None and \
                self.task.status != self.task.CANCELLED)
        self.action_play.set_sensitive(\
                (self.task is None and \
                 self.episode.was_downloaded(and_exists=True)) or \
                (self.task is not None and self.task.status in \
                 (self.task.DONE, self.task.CANCELLED)) or \
                 self._streaming_possible)
        self.action_delete.set_sensitive(\
                self.episode.was_downloaded(and_exists=True))
        self.action_download.set_sensitive((self.task is None and not \
                self.episode.was_downloaded(and_exists=True)) or \
                (self.task is not None and \
                 self.task.status in (self.task.CANCELLED, self.task.FAILED)))
        self.action_pause.set_sensitive(self.task is not None and \
                self.task.status in (self.task.QUEUED, self.task.DOWNLOADING))
        self.action_resume.set_sensitive(self.task is not None and \
                self.task.status == self.task.PAUSED)
        self.action_cancel.set_sensitive(self.task is not None and \
                self.task.status in (self.task.QUEUED, self.task.DOWNLOADING, \
                    self.task.PAUSED))
        self.action_visit_website.set_sensitive(self.episode is not None and \
                self.episode.link is not None)

    def on_download_status_progress(self):
        if self.task:
            self.download_progress.set_fraction(self.task.progress)
            self.download_progress.set_text('%s: %d%% (%s/s)' % ( \
                    self.task.STATUS_MESSAGE[self.task.status], \
                    100.*self.task.progress, \
                    util.format_filesize(self.task.speed)))

