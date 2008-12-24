# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2008 Thomas Perl and the gPodder Team
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
#  nokiavideocenter.py -- Import subscriptions from Nokia Video Center
#  Thomas Perl <thp@gpodder.org> 2008-12-24
#

"""Import podcast subscriptions from Nokia Video Center

This module imports (audio and video) podcast subscriptions
from Nokia's Video Center for Internet Tablets, available at
http://videocenter.garage.maemo.org/.

The result of the import is saved as an OPML file that can
then be imported in the gPodder GUI.
"""


try:
    from sqlite3 import dbapi2 as sqlite
except ImportError:
    from pysqlite2 import dbapi2 as sqlite

from gpodder import opml
import os.path

class VCChannel(object):
    """
    Fake podcastChannel-like object to allow
    opml's Exporter class to write an OPML file.
    """
    def __init__(self, title, description, url):
        self.title = title
        self.description = description
        self.url = url

class UpgradeFromVideocenter(object):
    def __init__(self):
        self.dbfile = os.path.expanduser('~/videocenter/primary.db')
        self.opmlfile = os.path.expanduser('~/videocenter/exported.opml')

    def db2opml(self):
        if os.path.exists(self.dbfile):
            db = sqlite.connect(self.dbfile)
            cur = db.cursor()
            cur.execute('SELECT title, description, link FROM channel')
            exporter = opml.Exporter(self.opmlfile)
            return exporter.write([VCChannel(t, d, u) for t, d, u in cur])

        return False


if __name__ == '__main__':
    upgrade = UpgradeFromVideocenter()
    if upgrade.db2opml():
        print 'Converted: %s' % (upgrade.opmlfile)
    else:
        print 'Not converted (%s missing?)' % (upgrade.dbfile)

