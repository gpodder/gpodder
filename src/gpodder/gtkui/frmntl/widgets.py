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
import hildon

class EditToolbarDeluxe(hildon.EditToolbar):
    """HildonEditToolbar with sensitivity and AppMenu action

    * Public method to set the button sensitivity
    * Open the parent window's AppMenu when touching titlebar

    (Enhancement requests filed as Maemo bugs #5166 and #5167)
    """
    def __init__(self, label_text, button_text):
        hildon.EditToolbar.__init__(self, label_text, button_text)

        alignment, separator, close_button = self.get_children()
        hbox = alignment.get_child()
        label, image, button = hbox.get_children()
        self._action_button = button

        expand, fill, padding, pack_type = hbox.query_child_packing(label)
        event_box = gtk.EventBox()
        event_box.connect('expose-event', self._on_expose_event)
        label.reparent(event_box)
        event_box.connect('button-release-event', self._on_label_clicked)
        hbox.add(event_box)
        hbox.reorder_child(event_box, 0)
        hbox.set_child_packing(event_box, expand, fill, padding, pack_type)
        self._label = label

    def set_button_sensitive(self, sensitivity):
        self._action_button.set_sensitive(sensitivity)

    def _on_expose_event(self, widget, event):
        # Based on hildon_edit_toolbar_expose() in hildon-edit-toolbar.c
        # in order to get the same style background for the EventBox widget
        style = self.get_style()
        style.paint_flat_box(widget.window, \
                gtk.STATE_NORMAL, \
                gtk.SHADOW_NONE, \
                event.area, widget, 'edit-toolbar', \
                0, 0, \
                widget.allocation.width, widget.allocation.height)
        # Propagate the expose event to the child (our label)
        child = widget.get_child()
        widget.propagate_expose(child, event)
        return True

    def _on_label_clicked(self, widget, event):
        parent = self.get_parent()
        app_menu = parent.get_app_menu()
        if app_menu is not None:
            app_menu.popup(parent)

