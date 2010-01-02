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

import gpodder

_ = gpodder.gettext
N_ = gpodder.ngettext

from gpodder import util

from gpodder.gtkui.interface.common import BuilderWidget
from gpodder.gtkui.frmntl.portrait import FremantleRotation

import hildon

class gPodderPreferences(BuilderWidget):
    UPDATE_INTERVALS = (
            (0, _('manually')),
            (20, N_('every %d minute', 'every %d minutes', 20) % 20),
            (60, _('hourly')),
            (60*6, N_('every %d hour', 'every %d hours', 6) % 6),
            (60*24, _('daily')),
    )

    DOWNLOAD_METHODS = (
            ('never', _('Show episode list')),
            ('queue', _('Add to download list')),
#            ('wifi', _('Download when on Wi-Fi')),
            ('always', _('Download immediately')),
    )

    AUDIO_PLAYERS = (
            ('default', _('Media Player')),
            ('panucci', _('Panucci')),
    )

    VIDEO_PLAYERS = (
            ('default', _('Media Player')),
            ('mplayer', _('MPlayer')),
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

        # Create a mapping from audio players to touch selector indices
        audio_player_mapping = dict((b, a) for a, b in enumerate(x[0] for x in self.AUDIO_PLAYERS))

        self.touch_selector_audio_player = hildon.TouchSelector(text=True)
        for value, caption in self.AUDIO_PLAYERS:
            self.touch_selector_audio_player.append_text(caption)

        if self._config.player not in (x[0] for x in self.AUDIO_PLAYERS):
            self._config.player = self.AUDIO_PLAYERS[0][0]

        self.touch_selector_audio_player.set_active(0, audio_player_mapping[self._config.player])
        self.picker_audio_player.set_selector(self.touch_selector_audio_player)

        # Create a mapping from video players to touch selector indices
        video_player_mapping = dict((b, a) for a, b in enumerate(x[0] for x in self.VIDEO_PLAYERS))

        self.touch_selector_video_player = hildon.TouchSelector(text=True)
        for value, caption in self.VIDEO_PLAYERS:
            self.touch_selector_video_player.append_text(caption)

        if self._config.videoplayer not in (x[0] for x in self.VIDEO_PLAYERS):
            self._config.videoplayer = self.VIDEO_PLAYERS[0][0]

        self.touch_selector_video_player.set_active(0, video_player_mapping[self._config.videoplayer])
        self.picker_video_player.set_selector(self.touch_selector_video_player)

        self.update_button_mygpo()

        # Fix the styling and layout of the picker buttons
        for button in (self.picker_orientation, \
                       self.picker_interval, \
                       self.picker_download, \
                       self.picker_audio_player, \
                       self.picker_video_player, \
                       self.button_mygpo):
            # Work around Maemo bug #4718
            button.set_name('HildonButton-finger')
            # Fix alignment problems (Maemo bug #6205)
            button.set_alignment(.0, .5, 1., 0.)
            child = button.get_child()
            child.set_padding(0, 0, 12, 0)

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

    def on_picker_audio_player_value_changed(self, *args):
        active_index = self.touch_selector_audio_player.get_active(0)
        new_value = self.AUDIO_PLAYERS[active_index][0]
        self._config.player = new_value

    def on_picker_video_player_value_changed(self, *args):
        active_index = self.touch_selector_video_player.get_active(0)
        new_value = self.VIDEO_PLAYERS[active_index][0]
        self._config.videoplayer = new_value

    def update_button_mygpo(self):
        if self._config.my_gpodder_username:
            self.button_mygpo.set_value(self._config.my_gpodder_username)
        else:
            self.button_mygpo.set_value(_('Not logged in'))

    def on_button_mygpo_clicked(self, button):
        self.mygpo_login()
        self.update_button_mygpo()

