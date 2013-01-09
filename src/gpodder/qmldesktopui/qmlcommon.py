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

# Mikołaj Milej <mikolajmm@gmail.com>; 2013-01-02

import os
import gpodder
from gpodder import gettext, ngettext

_ = gettext
N_ = ngettext

EPISODE_LIST_FILTERS = [
    # (UI label, EQL expression)
    (_('All'), None),
    (_('Hide deleted'), 'not deleted'),
    (_('New'), 'new or downloading'),
    (_('Downloaded'), 'downloaded or downloading'),
    (_('Deleted'), 'deleted'),
    (_('Finished'), 'finished'),
    (_('Archived'), 'downloaded and archive'),
    (_('Videos'), 'video'),
    (_('Partially played'), 'downloaded and played and not finished'),
    (_('Unplayed downloads'), 'downloaded and not played'),
]
                
def QML(filename):
    for folder in gpodder.ui_folders:
        filename = os.path.join(folder, filename)
        if os.path.exists(filename):
            return filename
