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


from PySide.QtCore import *

from gpodder import model
from gpodder import util

class QEpisode(QObject, model.PodcastEpisode):
    def __init__(self, *args, **kwargs):
        QObject.__init__(self)
        model.PodcastEpisode.__init__(self, *args, **kwargs)

class QPodcast(QObject, model.PodcastChannel):
    EpisodeClass = QEpisode

    def __init__(self, *args, **kwargs):
        QObject.__init__(self)
        model.PodcastChannel.__init__(self, *args, **kwargs)

    changed = Signal()

    def _title(self):
        return self.title

    qtitle = Property(unicode, _title, notify=changed)

    def _coverfile(self):
        return self.cover_file

    qcoverfile = Property(unicode, _coverfile, notify=changed)

    def _downloaded(self):
        return self.get_statistics()[3]

    qdownloaded = Property(int, _downloaded, notify=changed)

    def _description(self):
        return util.get_first_line(self.description).decode('utf-8')

    qdescription = Property(unicode, _description, notify=changed)



class Model(model.Model):
    PodcastClass = QPodcast

