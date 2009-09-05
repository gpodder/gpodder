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

import gpodder

_ = gpodder.gettext

from gpodder import util

from gpodder.gtkui.interface.common import BuilderWidget

from gpodder.gtkui.interface.configeditor import gPodderConfigEditor

class gPodderPreferences(BuilderWidget):
    finger_friendly_widgets = ['btn_close', 'btn_advanced']
    audio_players = [
            ('default', 'Media Player'),
            ('panucci', 'Panucci'),
    ]
    video_players = [
            ('default', 'Media Player'),
            ('mplayer', 'MPlayer'),
    ]
    
    def new(self):
        self._config.connect_gtk_togglebutton('on_quit_ask', self.check_ask_on_quit)
        self._config.connect_gtk_togglebutton('maemo_enable_gestures', self.check_enable_gestures)
        self._config.connect_gtk_togglebutton('enable_fingerscroll', self.check_enable_fingerscroll)

        self.main_window.connect('destroy', lambda w: self.callback_finished())

        for item in self.audio_players:
            command, caption = item
            if util.find_command(command) is None and command != 'default':
                self.audio_players.remove(item)

        for item in self.video_players:
            command, caption = item
            if util.find_command(command) is None and command != 'default':
                self.video_players.remove(item)

        # Set up the audio player combobox
        found = False
        self.userconfigured_player = None
        for id, audio_player in enumerate(self.audio_players):
            command, caption = audio_player
            self.combo_player_model.append([caption])
            if self._config.player == command:
                self.combo_player.set_active(id)
                found = True
        if not found:
            self.combo_player_model.append(['User-configured (%s)' % self._config.player])
            self.combo_player.set_active(len(self.combo_player_model)-1)
            self.userconfigured_player = self._config.player

        # Set up the video player combobox
        found = False
        self.userconfigured_videoplayer = None
        for id, video_player in enumerate(self.video_players):
            command, caption = video_player
            self.combo_videoplayer_model.append([caption])
            if self._config.videoplayer == command:
                self.combo_videoplayer.set_active(id)
                found = True
        if not found:
            self.combo_videoplayer_model.append(['User-configured (%s)' % self._config.videoplayer])
            self.combo_videoplayer.set_active(len(self.combo_videoplayer_model)-1)
            self.userconfigured_videoplayer = self._config.videoplayer

        self.gPodderPreferences.show()

    def on_combo_player_changed(self, combobox):
        index = combobox.get_active()
        if index < len(self.audio_players):
            self._config.player = self.audio_players[index][0]
        elif self.userconfigured_player is not None:
            self._config.player = self.userconfigured_player

    def on_combo_videoplayer_changed(self, combobox):
        index = combobox.get_active()
        if index < len(self.video_players):
            self._config.videoplayer = self.video_players[index][0]
        elif self.userconfigured_videoplayer is not None:
            self._config.videoplayer = self.userconfigured_videoplayer

    def on_btn_advanced_clicked(self, widget):
        gPodderConfigEditor(self.gPodderPreferences, _config=self._config)
        self.gPodderPreferences.destroy()

    def on_btn_close_clicked(self, widget):
        self.gPodderPreferences.destroy()

