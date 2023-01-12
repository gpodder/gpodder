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

import gi  # isort:skip
gi.require_version('Gtk', '3.0')  # isort:skip
from gi.repository import Gdk, GLib  # isort:skip


class SearchTree:
    """
        handle showing/hiding the search box for podcast or episode treeviews,
        as well as searching for text entered in the search entry.
        Automatically attaches to entry signals on creation.
    """
    def __init__(self, search_box, search_entry, tree, model, config):
        self.search_box = search_box
        self.search_entry = search_entry
        self.tree = tree
        self.model = model
        self.config = config
        self._search_timeout = None
        self.search_entry.connect('icon-press', self.hide_search)
        self.search_entry.connect('changed', self.on_entry_changed)
        self.search_entry.connect('key-press-event', self.on_entry_key_press)

    def set_search_term(self, text):
        self.model.set_search_term(text)
        self._search_timeout = None
        return False

    def on_entry_changed(self, editable):
        if self.search_box.get_property('visible'):
            if self._search_timeout is not None:
                GLib.source_remove(self._search_timeout)
            # use timeout_add, not util.idle_timeout_add, so it updates the TreeView before background tasks
            self._search_timeout = GLib.timeout_add(
                    self.config.ui.gtk.live_search_delay,
                    self.set_search_term, editable.get_chars(0, -1))

    def on_entry_key_press(self, editable, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide_search()
            return True

    def hide_search(self, *args):
        if self._search_timeout is not None:
            GLib.source_remove(self._search_timeout)
            self._search_timeout = None
        if not self.config.ui.gtk.search_always_visible:
            self.search_box.hide()
        self.search_entry.set_text('')
        self.model.set_search_term(None)
        self.tree.grab_focus()

    def show_search(self, input_char=None, grab_focus=True):
        self.search_box.show()
        if input_char:
            self.search_entry.insert_text(input_char, -1)
        if grab_focus:
            self.search_entry.grab_focus()
        self.search_entry.set_position(-1)
