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


#
#  gpodder.gtkui.opml - Module for displaying OPML feeds (2009-08-13)
#


import gtk

import cgi
import urllib

from gpodder.gtkui.frmntl import style

class OpmlListModel(gtk.ListStore):
    C_SELECTED, C_DESCRIPTION_MARKUP, C_URL = range(3)

    def __init__(self, importer):
        gtk.ListStore.__init__(self, bool, str, str)

        head_font = style.get_font_desc('SystemFont')
        head_color = style.get_color('ButtonTextColor')
        head = (head_font.to_string(), head_color.to_string())
        head = '<span font_desc="%s" foreground="%s">%%s</span>' % head

        sub_font = style.get_font_desc('SmallSystemFont')
        sub_color = style.get_color('SecondaryTextColor')
        sub = (sub_font.to_string(), sub_color.to_string())
        sub = '<span font_desc="%s" foreground="%s">%%s</span>' % sub
        self._markup_template = '\n'.join((head, sub))

        for channel in importer.items:
            self.append([False, self._format_channel(channel), channel['url']])

    def _format_channel(self, channel):
        title = cgi.escape(urllib.unquote_plus(channel['title']))
        description = cgi.escape(channel['description'])
        return self._markup_template % (title, description)

