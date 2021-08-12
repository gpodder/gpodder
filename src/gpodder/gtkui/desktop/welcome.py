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

import gpodder
from gpodder.gtkui.interface.common import BuilderWidget

_ = gpodder.gettext


class gPodderWelcome(BuilderWidget):

    def new(self):
        self.gPodderWelcome.set_transient_for(self.parent_widget)

    def on_btnCancel_clicked(self, button):
        self.main_window.response(Gtk.ResponseType.CANCEL)
