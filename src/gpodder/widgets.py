#!/usr/bin/python
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


#
#  widgets.py -- Additional widgets for gPodder
#  Thomas Perl <thp@gpodder.org> 2009-03-31
#

import gtk

from xml.sax import saxutils

class SimpleMessageArea(gtk.HBox):
    """A simple, yellow message area. Inspired by gedit.

    Original C source code:
    http://svn.gnome.org/viewvc/gedit/trunk/gedit/gedit-message-area.c
    """
    def __init__(self, message):
        gtk.HBox.__init__(self, spacing=6)
        self.set_border_width(6)
        self.__in_style_set = False
        self.connect('style-set', self.__style_set)
        self.connect('expose-event', self.__expose_event)

        self.__label = gtk.Label()
        self.__label.set_alignment(0.0, 0.5)
        self.__label.set_line_wrap(False)
        self.__label.set_markup('<b>%s</b>' % saxutils.escape(message))
        self.pack_start(self.__label, expand=True, fill=True)

        self.__image = gtk.image_new_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_BUTTON)
        self.__button = gtk.ToolButton(self.__image)
        self.__button.set_border_width(0)
        self.__button.connect('clicked', self.__button_clicked)
        vbox = gtk.VBox()
        vbox.pack_start(self.__button, expand=True, fill=False)
        self.pack_start(vbox, expand=False, fill=False)

    def __style_set(self, widget, previous_style):
        if self.__in_style_set:
            return 

        w = gtk.Window(gtk.WINDOW_POPUP)
        w.set_name('gtk-tooltip')
        w.ensure_style()
        style = w.get_style()

        self.__in_style_set = True
        self.set_style(style)
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
    
    def __button_clicked(self, toolbutton):
        self.hide_all()

