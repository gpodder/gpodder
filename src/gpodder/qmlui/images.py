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
from PySide.QtGui import *
from PySide.QtDeclarative import *

from gpodder import youtube
from gpodder import util

from gpodder.liblogger import log

import os
import urllib

class LocalCachedImageProvider(QDeclarativeImageProvider):
    IMAGE_TYPE = QDeclarativeImageProvider.ImageType.Image

    def __init__(self):
        QDeclarativeImageProvider.__init__(self, self.IMAGE_TYPE)
        self._cache = {}

    def requestImage(self, id, size, requestedSize):
        if id in self._cache:
            return self._cache[id]

        filename, cover_url, url = (urllib.unquote(x) for x in id.split('|'))

        if 'undefined' in (filename, cover_url, url):
            return QImage()

        data = None

        if os.path.exists(filename):
            data = open(filename, 'rb').read()

        if data is None or data == '':
            try:
                yt_url = youtube.get_real_cover(url)
                if yt_url is not None:
                    cover_url = yt_url
                data = util.urlopen(cover_url).read()
            except Exception, e:
                log('Error downloading cover: %s', e, sender=self)
                data = ''
            fp = open(filename, 'wb')
            fp.write(data)
            fp.close()

        image = QImage()
        image.loadFromData(data)
        if image.isNull():
            return image
        else:
            self._cache[id] = image.scaled(requestedSize, \
                    Qt.KeepAspectRatioByExpanding, \
                    Qt.SmoothTransformation)
            return self._cache[id]

