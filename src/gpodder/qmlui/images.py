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

from PySide.QtCore import Qt
from PySide.QtGui import QImage
from PySide.QtDeclarative import QDeclarativeImageProvider

import gpodder

from gpodder import youtube
from gpodder import util

import logging
logger = logging.getLogger(__name__)

import os
import urllib

class LocalCachedImageProvider(QDeclarativeImageProvider):
    IMAGE_TYPE = QDeclarativeImageProvider.ImageType.Image

    def __init__(self):
        QDeclarativeImageProvider.__init__(self, self.IMAGE_TYPE)
        self._cache = {}

    def requestImage(self, id, size, requestedSize):
        key = (id, requestedSize)
        if key in self._cache:
            return self._cache[key]

        filename, cover_url, url, title = (urllib.unquote(x) for x in id.split('|'))

        if filename == 'gpodder:episode-subset-view':
            filename = util.podcast_image_filename('podcast-all.png', big=True)

        if '' in (filename, cover_url, url):
            if filename == '' or not os.path.exists(filename):
                filename = util.cover_fallback_filename(title, big=True)

        data = None

        if os.path.exists(filename):
            data = open(filename, 'rb').read()
            if data == '':
                util.delete_file(filename)
                filename = util.cover_fallback_filename(title, big=True)
                data = open(filename, 'rb').read()

        write_to_disk = True
        if data is None or data == '' and cover_url:
            try:
                yt_url = youtube.get_real_cover(url)
                if yt_url is not None:
                    cover_url = yt_url
                data = util.urlopen(cover_url).read()
            except Exception, e:
                logger.error('Error downloading cover: %s', e, exc_info=True)
                filename = util.cover_fallback_filename(title, big=True)
                data = open(filename, 'rb').read()
                write_to_disk = False

            if write_to_disk:
                fp = open(filename, 'wb')
                fp.write(data)
                fp.close()

        image = QImage()
        image.loadFromData(data)
        if image.isNull():
            return image
        else:
            self._cache[key] = image.scaled(requestedSize, \
                    Qt.KeepAspectRatioByExpanding, \
                    Qt.SmoothTransformation)
            return self._cache[key]

