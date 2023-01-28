# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2018 The gPodder Team
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
#  gpodder.coverart - Unified cover art downloading module (2012-03-04)
#


import logging
import os
import shutil
import urllib.parse

import gpodder
from gpodder import util, youtube

_ = gpodder.gettext

logger = logging.getLogger(__name__)


class CoverDownloader(object):
    # File name extension dict, lists supported cover art extensions
    # Values: functions that check if some data is of that file type
    SUPPORTED_EXTENSIONS = {
        '.png': lambda d: d.startswith(b'\x89PNG\r\n\x1a\n\x00'),
        '.jpg': lambda d: d.startswith(b'\xff\xd8'),
        '.gif': lambda d: d.startswith(b'GIF89a') or d.startswith(b'GIF87a'),
        '.ico': lambda d: d.startswith(b'\0\0\1\0'),
        '.svg': lambda d: d.startswith(b'<svg '),
    }

    EXTENSIONS = list(SUPPORTED_EXTENSIONS.keys())
    ALL_EPISODES_ID = ':gpodder:all-episodes:'

    # Low timeout to avoid unnecessary hangs of GUIs
    TIMEOUT = 5

    def __init__(self):
        pass

    def get_cover_all_episodes(self):
        return self._default_filename('podcast-all.png')

    def get_cover(self, filename, cover_url, feed_url, title,
            username=None, password=None, download=False):
        # Detection of "all episodes" podcast
        if filename == self.ALL_EPISODES_ID:
            return self.get_cover_all_episodes()

        # Return already existing files
        for extension in self.EXTENSIONS:
            if os.path.exists(filename + extension):
                return filename + extension

        # Handle local files
        if cover_url is not None and cover_url.startswith('file://'):
            try:
                path = urllib.parse.unquote(cover_url).replace('file://', '')
                if not os.path.exists(path):
                    raise ValueError('Cover file not found: %s' % (path))

                extension = None
                with open(path, 'rb') as fp:
                    data = fp.read(512)
                    for filetype, check in list(self.SUPPORTED_EXTENSIONS.items()):
                        if check(data):
                            extension = filetype
                            break
                if extension is None:
                    raise ValueError(
                        'Unknown file type: %s (%r)' % (cover_url, data[:6]))

                # File is ok, copy it
                shutil.copyfile(path, filename + extension)
                return filename + extension
            except Exception as e:
                logger.warning('Setting cover art from file failed: %s', e)
                return self._fallback_filename(title)

        # If allowed to download files, do so here
        if download:
            # YouTube-specific cover art image resolver
            youtube_cover_url = youtube.get_cover(feed_url)
            if youtube_cover_url is not None:
                cover_url = youtube_cover_url

            if not cover_url:
                return self._fallback_filename(title)

            # We have to add username/password, because password-protected
            # feeds might keep their cover art also protected (bug 1521)
            if username is not None and password is not None:
                cover_url = util.url_add_authentication(cover_url,
                        username, password)

            try:
                logger.info('Downloading cover art: %s', cover_url)
                response = util.urlopen(cover_url, timeout=self.TIMEOUT)
                if response.status_code != 200:
                    msg = '%s returned status code %d' % (cover_url, response.status_code)
                    raise ValueError(msg)
                data = response.content
            except Exception as e:
                logger.warning('Cover art download failed: %s', e)
                return self._fallback_filename(title)

            try:
                extension = None

                for filetype, check in list(self.SUPPORTED_EXTENSIONS.items()):
                    if check(data):
                        extension = filetype
                        break

                if extension is None:
                    msg = 'Unknown file type: %s (%r)' % (cover_url, data[:6])
                    raise ValueError(msg)

                # Successfully downloaded the cover art - save it!
                fp = open(filename + extension, 'wb')
                fp.write(data)
                fp.close()

                return filename + extension
            except Exception as e:
                logger.warning('Cannot save cover art', exc_info=True)

        # Fallback to cover art based on the podcast title
        return self._fallback_filename(title)

    def _default_filename(self, basename):
        return os.path.join(gpodder.images_folder, basename)

    def _fallback_filename(self, title):
        return self._default_filename('podcast-%d.png' % (hash(title) % 5))
