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

import gpodder

_ = gpodder.gettext

from gpodder import util

from gpodder.gtkui.interface.common import BuilderWidget
from gpodder.gtkui.frmntl.portrait import FremantleRotation

import hildon

class gPodderPreferences(BuilderWidget):
    def new(self):
        self.main_window.connect('destroy', lambda w: self.callback_finished())

        self.touch_selector = hildon.TouchSelector(text=True)
        for caption in FremantleRotation.MODE_CAPTIONS:
            self.touch_selector.append_text(caption)
        self.touch_selector.set_active(0, self._config.rotation_mode)
        self.picker_orientation.set_selector(self.touch_selector)

        # Work around Maemo bug #4718
        self.picker_orientation.set_name('HildonButton-finger')

        self.gPodderPreferences.show()

    def on_picker_orientation_value_changed(self, *args):
        self._config.rotation_mode = self.touch_selector.get_active(0)

