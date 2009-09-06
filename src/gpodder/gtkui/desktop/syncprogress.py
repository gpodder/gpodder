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

from xml.sax import saxutils

import gpodder

_ = gpodder.gettext

from gpodder import util

from gpodder.gtkui.interface.common import BuilderWidget


class gPodderSyncProgress(BuilderWidget):
    def new(self):
        self.device.register('progress', self.on_progress)
        self.device.register('sub-progress', self.on_sub_progress)
        self.device.register('status', self.on_status)
        self.device.register('done', self.on_done)
    
    def on_progress(self, pos, max, text=None):
        if text is None:
            text = _('%d of %d done') % (pos, max)
        util.idle_add(self.progressbar.set_fraction, float(pos)/float(max))
        util.idle_add(self.progressbar.set_text, text)

    def on_sub_progress(self, percentage):
        util.idle_add(self.progressbar.set_text, _('Processing (%d%%)') % (percentage))

    def on_status(self, status):
        util.idle_add(self.status_label.set_markup, '<i>%s</i>' % saxutils.escape(status))

    def on_done(self):
        util.idle_add(self.gPodderSyncProgress.destroy)

    def on_gPodderSyncProgress_destroy(self, widget, *args):
        self.device.unregister('progress', self.on_progress)
        self.device.unregister('sub-progress', self.on_sub_progress)
        self.device.unregister('status', self.on_status)
        self.device.unregister('done', self.on_done)
        self.device.cancel()

    def on_cancel_button_clicked(self, widget, *args):
        self.device.cancel()


