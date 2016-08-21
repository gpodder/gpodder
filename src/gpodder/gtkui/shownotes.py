# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2016 Thomas Perl and the gPodder Team
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
import gobject
import pango
import os
import cgi


import gpodder

_ = gpodder.gettext

import logging
logger = logging.getLogger(__name__)

from gpodder import util
from gpodder.gtkui.draw import draw_text_box_centered


class gPodderShownotes:
    def __init__(self, shownotes_pane):
        self.shownotes_pane = shownotes_pane

        self.scrolled_window = gtk.ScrolledWindow()
        self.scrolled_window.set_shadow_type(gtk.SHADOW_IN)
        self.scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolled_window.add(self.init())
        self.scrolled_window.show_all()

        self.da_message = gtk.DrawingArea()
        self.da_message.connect('expose-event', \
                                    self.on_shownotes_message_expose_event)
        self.shownotes_pane.add(self.da_message)
        self.shownotes_pane.add(self.scrolled_window)

        self.set_complain_about_selection(True)
        self.hide_pane()

    # Either show the shownotes *or* a message, 'Please select an episode'
    def set_complain_about_selection(self, message=True):
        if message:
            self.scrolled_window.hide()
            self.da_message.show()
        else:
            self.da_message.hide()
            self.scrolled_window.show()

    def set_episodes(self, selected_episodes):
        if self.pane_is_visible:
            if len(selected_episodes) == 1:
                episode = selected_episodes[0]
                heading = episode.title
                subheading = _('from %s') % (episode.channel.title)
                self.update(heading, subheading, episode)
                self.set_complain_about_selection(False)
            else:
                self.set_complain_about_selection(True)

    def show_pane(self, selected_episodes):
        self.pane_is_visible = True
        self.set_episodes(selected_episodes)
        self.shownotes_pane.show()

    def hide_pane(self):
        self.pane_is_visible = False
        self.shownotes_pane.hide()

    def toggle_pane_visibility(self, selected_episodes):
        if self.pane_is_visible:
            self.hide_pane()
        else:
            self.show_pane(selected_episodes)

    def on_shownotes_message_expose_event(self, drawingarea, event):
        ctx = event.window.cairo_create()
        ctx.rectangle(event.area.x, event.area.y, \
                      event.area.width, event.area.height)
        ctx.clip()

        # paint the background white
        colormap = event.window.get_colormap()
        gc = event.window.new_gc(foreground=colormap.alloc_color('white'))
        event.window.draw_rectangle(gc, True, event.area.x, event.area.y, \
                                    event.area.width, event.area.height)

        x, y, width, height, depth = event.window.get_geometry()
        text = _('Please select an episode')
        draw_text_box_centered(ctx, drawingarea, width, height, text, None, None)
        return False


class gPodderShownotesText(gPodderShownotes):
    def init(self):
        self.text_view = gtk.TextView()
        self.text_view.set_wrap_mode(gtk.WRAP_WORD_CHAR)
        self.text_view.set_border_width(10)
        self.text_view.set_editable(False)
        self.text_view.connect('button-release-event', self.on_button_release)
        self.text_view.connect('key-press-event', self.on_key_press)
        self.text_buffer = gtk.TextBuffer()
        self.text_buffer.create_tag('heading', scale=pango.SCALE_LARGE, weight=pango.WEIGHT_BOLD)
        self.text_buffer.create_tag('subheading', scale=pango.SCALE_SMALL)
        self.text_buffer.create_tag('hyperlink', foreground="#0000FF", underline=pango.UNDERLINE_SINGLE)
        self.text_view.set_buffer(self.text_buffer)
        self.text_view.modify_bg(gtk.STATE_NORMAL,
                gtk.gdk.color_parse('#ffffff'))
        return self.text_view

    def update(self, heading, subheading, episode):
        hyperlinks = [(0, None)]
        self.text_buffer.set_text('')
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(), heading, 'heading')
        self.text_buffer.insert_at_cursor('\n')
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(), subheading, 'subheading')
        self.text_buffer.insert_at_cursor('\n\n')
        for target, text in util.extract_hyperlinked_text(episode.description):
            hyperlinks.append((self.text_buffer.get_char_count(), target))
            if target:
                self.text_buffer.insert_with_tags_by_name(
                    self.text_buffer.get_end_iter(), text, 'hyperlink')
            else:
                self.text_buffer.insert(
                    self.text_buffer.get_end_iter(), text)
        hyperlinks.append((self.text_buffer.get_char_count(), None))
        self.hyperlinks = [(start, end, url) for (start, url), (end, _) in zip(hyperlinks, hyperlinks[1:]) if url]
        self.text_buffer.place_cursor(self.text_buffer.get_start_iter())

    def on_button_release(self, widget, event):
        if event.button == 1:
            self.activate_links()

    def on_key_press(self, widget, event):
        if gtk.gdk.keyval_name(event.keyval) == 'Return':
            self.activate_links()
            return True

        return False

    def activate_links(self):
        if self.text_buffer.get_selection_bounds() == ():
            pos = self.text_buffer.props.cursor_position
            target = next((url for start, end, url in self.hyperlinks if start < pos < end), None)
            if target is not None:
                util.open_website(target)
