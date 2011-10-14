# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2012 Thomas Perl and the gPodder Team
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


from gi.repository import Gtk

from gpodder import util

import urllib

class OpmlListModel(Gtk.ListStore):
    C_SELECTED, C_DESCRIPTION_MARKUP, C_URL = range(3)

    def __init__(self, importer):
        Gtk.ListStore.__init__(self, bool, str, str)
        for channel in importer.items:
            self.append([False, self._format_channel(channel), channel['url']])

    def _format_channel(self, channel):
        title = util.safe_escape(urllib.unquote_plus(channel['title']))
        description = util.safe_escape(channel['description'])
        return '<b>%s</b>\n<span size="small">%s</span>' % (title, description)

