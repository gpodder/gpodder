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
import hildon
import gobject

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


class FancyProgressBar(object):
    """An animated progress bar with cancel button (bling bling!)

    This is a helper class coordinating some widgets that are needed for the
    feed update progress bar. It takes care of hooking up and resizing an event
    box (to be used in the main window), of creating the progress bar and
    cancel button widgets and of controlling the show/hide animation as well
    as reacting to the click on the cancel button (by means of the event box).

    In short, this provides all the necessary hooks to create a nice, sliding
    progress bar using hildon.AnimationActor while hiding the plumbing.

    Usage:

    Create a new object, where parent is the hildon.StackableWindow on which
    this progress bar should be shown. The on_cancel should be a callback with
    one parameter (will be the FancyProgressBar instance from which it is
    called) or None. It will be called when the cancel button is clicked.

    The using code should then take the "event_box" attribute and place it at
    the bottom of the parent window (e.g. as last item in a gtk.VBox). After
    that, calling "show()" and "hide()" will take care of hiding and showing
    both the "contents" (progress bar) and the event box. The contents will be
    slided in and out using a nice animation.

    You can get the progress bar from the "progress_bar" attribute and use it
    in your code to update the contents (it's a simple gtk.ProgressBar object).
    """

    SHOW, HIDE = range(2)
    FREMANTLE_TITLE_BAR_SIZE = 56
    STEP = 10

    def __init__(self, parent, on_cancel=None):
        self.parent = parent
        self.on_cancel = on_cancel
        self.state = FancyProgressBar.HIDE
        self.offset = float(1)

        self.progress_bar = gtk.ProgressBar()
        image = gtk.image_new_from_icon_name('general_stop', \
                gtk.ICON_SIZE_LARGE_TOOLBAR)
        self.cancel_button = gtk.ToolButton(image)
        self.hbox_animation_actor = gtk.HBox()
        self.hbox_inner = gtk.HBox()
        self.hbox_animation_actor.pack_start(self.hbox_inner)
        self.hbox_animation_actor.child_set(self.hbox_inner, 'padding', 12)
        self.hbox_inner.pack_start(self.progress_bar)
        self.hbox_inner.pack_start(self.cancel_button, False)
        self.animation_actor = hildon.AnimationActor()
        self.animation_actor.set_parent(self.parent)
        self.animation_actor.add(self.hbox_animation_actor)
        self.animation_actor.show_all()
        self.height, self.width = self.cancel_button.size_request()
        self.event_box = gtk.EventBox()
        self.event_box.connect('button-release-event', self.on_button_release)
        self.event_box.set_size_request(-1, self.height)
        self.offset = float(self.height)
        self.relayout()

    def on_button_release(self, widget, event):
        if event.x > self.cancel_button.get_allocation().x:
            if self.on_cancel is not None:
                self.on_cancel(self)

    def relayout(self):
        width, height = self.parent.get_size()
        self.animation_actor.resize(width, self.height)
        x, y = 0, FancyProgressBar.FREMANTLE_TITLE_BAR_SIZE
        y += height + int(self.offset)
        y -= self.height
        self.animation_actor.set_position(x, y)
        return False

    def show(self):
        if self.state != FancyProgressBar.SHOW:
            self.state = FancyProgressBar.SHOW
            self.hbox_animation_actor.show()
            self.offset = float(self.height)
            gobject.timeout_add(FancyProgressBar.STEP, self.on_timeout)

    def hide(self):
        if self.state != FancyProgressBar.HIDE:
            self.event_box.hide()
            self.state = FancyProgressBar.HIDE
            self.offset = float(1.)
            gobject.timeout_add(FancyProgressBar.STEP, self.on_timeout)

    def on_timeout(self):
        result = True

        if self.state == FancyProgressBar.SHOW:
            self.offset *= .9
            if self.offset < 2:
                self.event_box.show()
                self.offset = 0.
                result = False
        elif self.state == FancyProgressBar.HIDE:
            self.offset *= 1.1
            if self.offset >= self.height:
                self.offset = float(self.height)
                self.hbox_animation_actor.hide()
                result = False

        self.relayout()

        return result

