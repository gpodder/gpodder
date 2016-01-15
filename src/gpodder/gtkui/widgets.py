#!/usr/bin/python
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


#
#  widgets.py -- Additional widgets for gPodder
#  Thomas Perl <thp@gpodder.org> 2009-03-31
#

import gtk
import gobject
import pango

import cgi

class SimpleMessageArea(gtk.HBox):
    """A simple, yellow message area. Inspired by gedit.

    Original C source code:
    http://svn.gnome.org/viewvc/gedit/trunk/gedit/gedit-message-area.c
    """
    def __init__(self, message, buttons=()):
        gtk.HBox.__init__(self, spacing=6)
        self.set_border_width(6)
        self.__in_style_set = False
        self.connect('style-set', self.__style_set)
        self.connect('expose-event', self.__expose_event)

        self.__label = gtk.Label()
        self.__label.set_alignment(0.0, 0.5)
        self.__label.set_line_wrap(False)
        self.__label.set_ellipsize(pango.ELLIPSIZE_END)
        self.__label.set_markup('<b>%s</b>' % cgi.escape(message))
        self.pack_start(self.__label, expand=True, fill=True)

        hbox = gtk.HBox()
        for button in buttons:
            hbox.pack_start(button, expand=True, fill=False)
        self.pack_start(hbox, expand=False, fill=False)

    def set_markup(self, markup, line_wrap=True, min_width=3, max_width=100):
        # The longest line should determine the size of the label
        width_chars = max(len(line) for line in markup.splitlines())

        # Enforce upper and lower limits for the width
        width_chars = max(min_width, min(max_width, width_chars))

        self.__label.set_width_chars(width_chars)
        self.__label.set_markup(markup)
        self.__label.set_line_wrap(line_wrap)

    def __style_set(self, widget, previous_style):
        if self.__in_style_set:
            return

        w = gtk.Window(gtk.WINDOW_POPUP)
        w.set_name('gtk-tooltip')
        w.ensure_style()
        style = w.get_style()

        self.__in_style_set = True
        self.set_style(style)
        self.__label.set_style(style)
        self.__in_style_set = False

        w.destroy()

        self.queue_draw()

    def __expose_event(self, widget, event):
        style = widget.get_style()
        rect = widget.get_allocation()
        style.paint_flat_box(widget.window, gtk.STATE_NORMAL,
                gtk.SHADOW_OUT, None, widget, "tooltip",
                rect.x, rect.y, rect.width, rect.height)
        return False


class SpinningProgressIndicator(gtk.Image):
    # Progress indicator loading inspired by glchess from gnome-games-clutter
    def __init__(self, size=32):
        gtk.Image.__init__(self)

        self._frames = []
        self._frame_id = 0

        # Load the progress indicator
        icon_theme = gtk.icon_theme_get_default()

        try:
            icon = icon_theme.load_icon('process-working', size, 0)
            width, height = icon.get_width(), icon.get_height()
            if width < size or height < size:
                size = min(width, height)
            for row in range(height/size):
                for column in range(width/size):
                    frame = icon.subpixbuf(column*size, row*size, size, size)
                    self._frames.append(frame)
            # Remove the first frame (the "idle" icon)
            if self._frames:
                self._frames.pop(0)
            self.step_animation()
        except:
            # FIXME: This is not very beautiful :/
            self.set_from_stock(gtk.STOCK_EXECUTE, gtk.ICON_SIZE_BUTTON)

    def step_animation(self):
        if len(self._frames) > 1:
            self._frame_id += 1
            if self._frame_id >= len(self._frames):
                self._frame_id = 0
            self.set_from_pixbuf(self._frames[self._frame_id])

