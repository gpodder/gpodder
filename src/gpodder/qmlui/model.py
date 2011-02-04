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

import gpodder

from gpodder import model
from gpodder import util
from gpodder import youtube

import threading

def convert(s):
    if isinstance(s, unicode):
        return s

    return s.decode('utf-8', 'ignore')


class QEpisode(QObject, model.PodcastEpisode):
    def __init__(self, *args, **kwargs):
        QObject.__init__(self)
        model.PodcastEpisode.__init__(self, *args, **kwargs)

    changed = Signal()

    def _title(self):
        return convert(self.title)

    qtitle = Property(unicode, _title, notify=changed)

    def _sourceurl(self):
        if self.was_downloaded(and_exists=True):
            url = self.local_filename(create=False)
        else:
            url = youtube.get_real_download_url(self.url)
        return convert(url)

    qsourceurl = Property(unicode, _sourceurl, notify=changed)

    def _filetype(self):
        return self.file_type() or 'download' # FIXME

    qfiletype = Property(unicode, _filetype, notify=changed)

    def _downloaded(self):
        return self.state == gpodder.STATE_DOWNLOADED

    qdownloaded = Property(bool, _downloaded, notify=changed)

    def _description(self):
        return convert(self.description)

    qdescription = Property(unicode, _description, notify=changed)

    def _new(self):
        return self.is_new

    qnew = Property(bool, _new, notify=changed)

    def _podcast(self):
        return self.channel

    qpodcast = Property(QObject, _podcast, notify=changed)


class QPodcast(QObject, model.PodcastChannel):
    EpisodeClass = QEpisode

    def __init__(self, *args, **kwargs):
        QObject.__init__(self)
        self._updating = False
        self._section_cached = None
        model.PodcastChannel.__init__(self, *args, **kwargs)

    def qupdate(self):
        def t(self):
            self._updating = True
            self.changed.emit()
            try:
                self.update()
            except Exception, e:
                # XXX: Handle exception (error message)!
                pass
            self._updating = False
            self.changed.emit()

        threading.Thread(target=t, args=[self]).start()

    changed = Signal()

    def _updating(self):
        return self._updating

    qupdating = Property(bool, _updating, notify=changed)

    def _title(self):
        return convert(self.title)

    qtitle = Property(unicode, _title, notify=changed)

    def _coverfile(self):
        return convert(self.cover_file)

    qcoverfile = Property(unicode, _coverfile, notify=changed)

    def _downloaded(self):
        return self.get_statistics()[3]

    qdownloaded = Property(int, _downloaded, notify=changed)

    def _description(self):
        return convert(util.get_first_line(self.description))

    qdescription = Property(unicode, _description, notify=changed)

    def _section(self):
        if self._section_cached is None:
            self._section_cached = convert(self._get_content_type())
        return self._section_cached

    qsection = Property(unicode, _section, notify=changed)




class Model(model.Model):
    PodcastClass = QPodcast

