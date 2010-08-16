# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2010 Thomas Perl and the gPodder Team
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
import hildon

import gpodder

_ = gpodder.gettext

class ProgressIndicator(object):
    # Delayed time until window is shown (for short operations)
    DELAY = 500

    def __init__(self, title, subtitle=None, cancellable=False, parent=None):
        self.title = title
        self.subtitle = subtitle
        self.cancellable = cancellable
        self.parent = parent
        self.dialog = None
        self.indicator = None
        self._progress_set = False
        self._progress = 0.
        self._message_set = False
        self._message = ''
        self.source_id = gobject.timeout_add(self.DELAY, self._create_progress)

    def _create_progress(self):
        self.dialog = hildon.hildon_banner_show_animation(self.parent, \
                'qgn_indi_pball_a', self.title)
        self._update_label()

        gobject.source_remove(self.source_id)
        self.source_id = None
        return False

    def _update_label(self):
        if self.dialog is not None:
            text = []
            text.append(self.title)
            if self._message_set:
                text.append('\n')
                text.append(self._message)
            if self._progress_set:
                text.append(' (%.0f%%)' % (self._progress*100.,))
            self.dialog.set_text(''.join(text))

    def on_message(self, message):
        self._message_set = True
        self._message = message
        self._update_label()

    def on_progress(self, progress):
        self._progress_set = True
        self._progress = progress
        self._update_label()

    def on_finished(self):
        if self.dialog is not None:
            self.dialog.destroy()

        if self.source_id is not None:
            gobject.source_remove(self.source_id)

