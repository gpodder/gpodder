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
    UPDATE_INTERVALS = (
            (0, _('manually')),
            (20, _('every %d minutes') % 20),
            (60, _('hourly')),
            (60*6, _('every %d hours') % 6),
            (60*24, _('daily')),
    )

    DOWNLOAD_METHODS = (
            ('never', _('Show episode list')),
            ('queue', _('Add to download list')),
#            ('wifi', _('Download when on Wi-Fi')),
            ('always', _('Download immediately')),
    )

    def new(self):
        self.main_window.connect('destroy', lambda w: self.callback_finished())

        self.touch_selector_orientation = hildon.TouchSelector(text=True)
        for caption in FremantleRotation.MODE_CAPTIONS:
            self.touch_selector_orientation.append_text(caption)
        self.touch_selector_orientation.set_active(0, self._config.rotation_mode)
        self.picker_orientation.set_selector(self.touch_selector_orientation)

        if not self._config.auto_update_feeds:
            self._config.auto_update_frequency = 0

        # Create a mapping from minute values to touch selector indices
        minute_index_mapping = dict((b, a) for a, b in enumerate(x[0] for x in self.UPDATE_INTERVALS))

        self.touch_selector_interval = hildon.TouchSelector(text=True)
        for value, caption in self.UPDATE_INTERVALS:
            self.touch_selector_interval.append_text(caption)
        interval = self._config.auto_update_frequency
        if interval in minute_index_mapping:
            self._custom_interval = 0
            self.touch_selector_interval.set_active(0, minute_index_mapping[interval])
        else:
            self._custom_interval = self._config.auto_update_frequency
            self.touch_selector_interval.append_text(_('every %d minutes') % interval)
            self.touch_selector_interval.set_active(0, len(self.UPDATE_INTERVALS))
        self.picker_interval.set_selector(self.touch_selector_interval)

        # Create a mapping from download methods to touch selector indices
        download_method_mapping = dict((b, a) for a, b in enumerate(x[0] for x in self.DOWNLOAD_METHODS))

        self.touch_selector_download = hildon.TouchSelector(text=True)
        for value, caption in self.DOWNLOAD_METHODS:
            self.touch_selector_download.append_text(caption)

        if self._config.auto_download not in (x[0] for x in self.DOWNLOAD_METHODS):
            self._config.auto_download = self.DOWNLOAD_METHODS[0][0]

        self.touch_selector_download.set_active(0, download_method_mapping[self._config.auto_download])
        self.picker_download.set_selector(self.touch_selector_download)

        # Work around Maemo bug #4718
        self.picker_orientation.set_name('HildonButton-finger')
        self.picker_interval.set_name('HildonButton-finger')
        self.picker_download.set_name('HildonButton-finger')

        self.picker_orientation.set_alignment(0.5, 0.5, .9, 0.)
        self.picker_interval.set_alignment(0.5, 0.5, .9, 0.)
        self.picker_download.set_alignment(0.5, 0.5, .9, 0.)

        self.gPodderPreferences.show()

    def on_picker_orientation_value_changed(self, *args):
        self._config.rotation_mode = self.touch_selector_orientation.get_active(0)

    def on_picker_interval_value_changed(self, *args):
        active_index = self.touch_selector_interval.get_active(0)
        if active_index < len(self.UPDATE_INTERVALS):
            new_frequency = self.UPDATE_INTERVALS[active_index][0]
        else:
            new_frequency = self._custom_interval

        if new_frequency == 0:
            self._config.auto_update_feeds = False
        self._config.auto_update_frequency = new_frequency
        if new_frequency > 0:
            self._config.auto_update_feeds = True

    def on_picker_download_value_changed(self, *args):
        active_index = self.touch_selector_download.get_active(0)
        new_value = self.DOWNLOAD_METHODS[active_index][0]
        self._config.auto_download = new_value

