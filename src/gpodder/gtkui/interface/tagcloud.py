# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2018 The gPodder Team
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


from gi.repository import Gtk
from gi.repository import GObject
import cgi

class TagCloud(Gtk.Layout):
    __gsignals__ = {
            'selected': (GObject.SignalFlags.RUN_LAST, None,
                           (GObject.TYPE_STRING,))
    }


    def __init__(self, min_size=20, max_size=36):
        Gtk.Layout.__init__(self)
        self._min_weight = 0
        self._max_weight = 0
        self._min_size = min_size
        self._max_size = max_size
        self._size = 0, 0
        self._alloc_id = self.connect('size-allocate', self._on_size_allocate)
        self._in_relayout = False

    def clear_tags(self):
        for child in self.get_children():
            self.remove(child)

    def set_tags(self, tags):
        tags = list(tags)
        self._min_weight = min(weight for tag, weight in tags)
        self._max_weight = max(weight for tag, weight in tags)

        for tag, weight in tags:
            label = Gtk.Label()
            markup = '<span size="%d">%s</span>' % (1000*self._scale(weight), cgi.escape(tag))
            label.set_markup(markup)
            button = Gtk.ToolButton(label)
            button.connect('clicked', lambda b, t: self.emit('selected', t), tag)
            self.put(button, 1, 1)
            button.show_all()

        self.relayout()

    def _on_size_allocate(self, widget, allocation):
        self._size = (allocation.width, allocation.height)
        if not self._in_relayout:
            self.relayout()

    def _scale(self, weight):
        weight_range = self._max_weight-self._min_weight
        ratio = (weight-self._min_weight)/weight_range
        return int(self._min_size + (self._max_size-self._min_size)*ratio)

    def relayout(self):
        self._in_relayout = True
        x, y, max_h = 0, 0, 0
        current_row = []
        pw, ph = self._size
        def fixup_row(widgets, x, y, max_h):
            residue = (pw - x)
            x = int(residue//2)
            for widget in widgets:
                cw, ch = widget.size_request()
                self.move(widget, x, y+max(0, int(max_h-ch)//2))
                x += cw + 10
        for child in self.get_children():
            w, h = child.size_request()
            if x + w > pw:
                fixup_row(current_row, x, y, max_h)
                y += max_h + 10
                max_h, x = 0, 0
                current_row = []

            self.move(child, x, y)
            x += w + 10
            max_h = max(max_h, h)
            current_row.append(child)
        fixup_row(current_row, x, y, max_h)
        self.set_size(pw, y+max_h)
        def unrelayout():
            self._in_relayout = False
            return False
        GObject.idle_add(unrelayout)


GObject.type_register(TagCloud)

