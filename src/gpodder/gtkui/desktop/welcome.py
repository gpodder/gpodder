# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2015 Thomas Perl and the gPodder Team
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

import gpodder

_ = gpodder.gettext

from gpodder.gtkui.interface.common import BuilderWidget

class gPodderWelcome(BuilderWidget):
    PADDING = 10

    def new(self):
        for widget in self.vbox_buttons.get_children():
            for child in widget.get_children():
                if isinstance(child, gtk.Alignment):
                    child.set_padding(self.PADDING, self.PADDING,
                        self.PADDING, self.PADDING)
                else:
                    child.set_padding(self.PADDING, self.PADDING)

    def on_btnCancel_clicked(self, button):
        self.main_window.response(gtk.RESPONSE_CANCEL)

