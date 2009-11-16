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


#
#  gpodder.gtkui.frmntl.model -- Model customizations for Maemo 5 (2009-11-16)
#

import gpodder

_ = gpodder.gettext

from gpodder.gtkui import download
from gpodder.gtkui.frmntl import style

class DownloadStatusModel(download.DownloadStatusModel):
    def __init__(self):
        download.DownloadStatusModel.__init__(self)
        head_font = style.get_font_desc('SystemFont')
        head_color = style.get_color('ButtonTextColor')
        head = (head_font.to_string(), head_color.to_string())
        head = '<span font_desc="%s" foreground="%s">%%s</span>' % head
        sub_font = style.get_font_desc('SmallSystemFont')
        sub_color = style.get_color('SecondaryTextColor')
        sub = (sub_font.to_string(), sub_color.to_string())
        sub = '<span font_desc="%s" foreground="%s">%%s - %%s</span>' % sub
        self._markup_template = '\n'.join((head, sub))

    def _format_message(self, episode, message, podcast):
        return self._markup_template % (episode, message, podcast)

