# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2013 Thomas Perl and the gPodder Team
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

class OpmlListModel(gtk.ListStore):
    C_SELECTED, C_TITLE, C_DESCRIPTION_MARKUP, C_URL = range(4)

    def __init__(self, importer):
        gtk.ListStore.__init__(self, bool, str, str, str)
        for channel in importer.items:
            self.append([False, channel['title'],
                self._format_channel(channel), channel['url']])

    def _format_channel(self, channel):
        title = cgi.escape(urllib.unquote_plus(channel['title']))
        description = cgi.escape(channel['description'])
        return '<b>%s</b>\n%s' % (title, description)

