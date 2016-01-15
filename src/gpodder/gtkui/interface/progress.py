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
import gobject
import pango

import gpodder

_ = gpodder.gettext

from gpodder.gtkui.widgets import SpinningProgressIndicator

class ProgressIndicator(object):
    # Delayed time until window is shown (for short operations)
    DELAY = 500

    # Time between GUI updates after window creation
    INTERVAL = 100

    def __init__(self, title, subtitle=None, cancellable=False, parent=None):
        self.title = title
        self.subtitle = subtitle
        self.cancellable = cancellable
        self.parent = parent
        self.dialog = None
        self.progressbar = None
        self.indicator = None
        self._initial_message = None
        self._initial_progress = None
        self._progress_set = False
        self.source_id = gobject.timeout_add(self.DELAY, self._create_progress)

    def _on_delete_event(self, window, event):
        if self.cancellable:
            self.dialog.response(gtk.RESPONSE_CANCEL)
        return True

    def _create_progress(self):
        self.dialog = gtk.MessageDialog(self.parent, \
                0, 0, gtk.BUTTONS_CANCEL, self.subtitle or self.title)
        self.dialog.set_modal(True)
        self.dialog.connect('delete-event', self._on_delete_event)
        self.dialog.set_title(self.title)
        self.dialog.set_deletable(self.cancellable)

        # Avoid selectable text (requires PyGTK >= 2.22)
        if hasattr(self.dialog, 'get_message_area'):
            for label in self.dialog.get_message_area():
                if isinstance(label, gtk.Label):
                    label.set_selectable(False)

        self.dialog.set_response_sensitive(gtk.RESPONSE_CANCEL, \
                self.cancellable)

        self.progressbar = gtk.ProgressBar()
        self.progressbar.set_ellipsize(pango.ELLIPSIZE_END)

        # If the window is shown after the first update, set the progress
        # info so that when the window appears, data is there already
        if self._initial_progress is not None:
            self.progressbar.set_fraction(self._initial_progress)
        if self._initial_message is not None:
            self.progressbar.set_text(self._initial_message)

        self.dialog.vbox.add(self.progressbar)
        self.indicator = SpinningProgressIndicator()
        self.dialog.set_image(self.indicator)
        self.dialog.show_all()

        gobject.source_remove(self.source_id)
        self.source_id = gobject.timeout_add(self.INTERVAL, self._update_gui)
        return False

    def _update_gui(self):
        if self.indicator:
            self.indicator.step_animation()
        if not self._progress_set and self.progressbar:
            self.progressbar.pulse()
        return True

    def on_message(self, message):
        if self.progressbar:
            self.progressbar.set_text(message)
        else:
            self._initial_message = message

    def on_progress(self, progress):
        self._progress_set = True
        if self.progressbar:
            self.progressbar.set_fraction(progress)
        else:
            self._initial_progress = progress

    def on_finished(self):
        if self.dialog is not None:
            self.dialog.destroy()
        gobject.source_remove(self.source_id)

