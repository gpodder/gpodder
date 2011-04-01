# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
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
from PySide.QtGui import *

import gpodder

from gpodder.liblogger import log

from gpodder import model
from gpodder import util
from gpodder import youtube

import threading
import os

def convert(s):
    if isinstance(s, unicode):
        return s

    return s.decode('utf-8', 'ignore')


class QEpisode(QObject, model.PodcastEpisode):
    def __init__(self, *args, **kwargs):
        QObject.__init__(self)
        model.PodcastEpisode.__init__(self, *args, **kwargs)

        # Caching of YouTube URLs, so we don't need to resolve
        # it every time we update the podcast item (doh!)
        self._qt_yt_url = None

    changed = Signal()

    def _title(self):
        return convert(self.title)

    qtitle = Property(unicode, _title, notify=changed)

    def _sourceurl(self):
        if self.was_downloaded(and_exists=True):
            url = self.local_filename(create=False)
        elif self._qt_yt_url is not None:
            url = self._qt_yt_url
        else:
            url = youtube.get_real_download_url(self.url)
            self._qt_yt_url = url
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

    def _positiontext(self):
        return convert(self.get_play_info_string())

    qpositiontext = Property(unicode, _positiontext, notify=changed)

    def _position(self):
        return self.current_position

    def _set_position(self, position):
        current_position = int(position)
        if current_position == 0: return
        if current_position != self.current_position:
            self.current_position = current_position
            self.changed.emit()

    qposition = Property(int, _position, _set_position, notify=changed)

    def _duration(self):
        return self.total_time

    def _set_duration(self, duration):
        self.total_time = int(duration)
        self.changed.emit()

    qduration = Property(int, _duration, _set_duration, notify=changed)


class QPodcast(QObject, model.PodcastChannel):
    EpisodeClass = QEpisode

    def __init__(self, *args, **kwargs):
        QObject.__init__(self)
        self._updating = False
        self._section_cached = None
        model.PodcastChannel.__init__(self, *args, **kwargs)

    def qupdate(self, force=False):
        def t(self):
            self._updating = True
            self.changed.emit()
            if force:
                self.http_etag = None
                self.http_last_modified = None
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

    def _url(self):
        return convert(self.url)

    qurl = Property(unicode, _url, notify=changed)

    def _coverfile(self):
        return convert(self.cover_file)

    qcoverfile = Property(unicode, _coverfile, notify=changed)

    def _coverurl(self):
        return convert(self.cover_url)

    qcoverurl = Property(unicode, _coverurl, notify=changed)

    def _downloaded(self):
        return self.get_statistics()[3]

    qdownloaded = Property(int, _downloaded, notify=changed)

    def _new(self):
        return self.get_statistics()[2]

    qnew = Property(int, _new, notify=changed)

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

