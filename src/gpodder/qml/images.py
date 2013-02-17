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

import urllib

from PySide.QtCore import Qt
from PySide.QtGui import QImage
from PySide.QtDeclarative import QDeclarativeImageProvider

from gpodder import util
from gpodder import coverart

import logging
logger = logging.getLogger(__name__)


class LocalCachedImageProvider(QDeclarativeImageProvider):
    IMAGE_TYPE = QDeclarativeImageProvider.ImageType.Image

    def __init__(self):
        QDeclarativeImageProvider.__init__(self, self.IMAGE_TYPE)
        self.downloader = coverart.CoverDownloader()
        self._cache = {}

    def requestImage(self, imageId, size, requestedSize):
        key = (imageId, requestedSize)
        if key in self._cache:
            return self._cache[key]

        cover_file, cover_url, podcast_url, podcast_title = (urllib.unquote(x)
                for x in imageId.split('|'))

        def get_filename():
            return self.downloader.get_cover(cover_file, cover_url,
                    podcast_url, podcast_title, None, None, True)

        filename = get_filename()

        image = QImage()
        if not image.load(filename):
            if filename.startswith(cover_file):
                logger.info('Deleting broken cover art: %s', filename)
                util.delete_file(filename)
                image.load(get_filename())

        if not image.isNull():
            self._cache[key] = image.scaled(requestedSize,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation)

        return self._cache[key]
