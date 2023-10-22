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


#
#  widgets.py -- Additional widgets for gPodder
#  Thomas Perl <thp@gpodder.org> 2009-03-31
#


from gi.repository import Gtk


class SpinningProgressIndicator(Gtk.Image):
    # Progress indicator loading inspired by glchess from gnome-games-clutter
    def __init__(self, size=32):
        Gtk.Image.__init__(self)

        self._frames = []
        self._frame_id = 0

        # Load the progress indicator
        icon_theme = Gtk.IconTheme.get_default()

        try:
            icon = icon_theme.load_icon('process-working', size, 0)
            width, height = icon.get_width(), icon.get_height()
            if width < size or height < size:
                size = min(width, height)
            for row in range(height // size):
                for column in range(width // size):
                    frame = icon.subpixbuf(column * size, row * size, size, size)
                    self._frames.append(frame)
            # Remove the first frame (the "idle" icon)
            if self._frames:
                self._frames.pop(0)
            self.step_animation()
        except:
            # FIXME: This is not very beautiful :/
            self.set_from_icon_name('system-run', Gtk.IconSize.BUTTON)

    def step_animation(self):
        if len(self._frames) > 1:
            self._frame_id += 1
            if self._frame_id >= len(self._frames):
                self._frame_id = 0
            self.set_from_pixbuf(self._frames[self._frame_id])
