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
#  gpodder.coverart - Unified cover art downloading module (2012-03-04)
#


import gpodder

import logging
logger = logging.getLogger(__name__)

from gpodder import util

from gpodder.plugins import youtube

import os

class CoverDownloader(object):
    # File name extension dict, lists supported cover art extensions
    # Values: functions that check if some data is of that file type
    SUPPORTED_EXTENSIONS = {
        '.png': lambda d: d.startswith(b'\x89PNG\r\n\x1a\n\x00'),
        '.jpg': lambda d: d.startswith(b'\xff\xd8'),
        '.gif': lambda d: d.startswith(b'GIF89a') or d.startswith(b'GIF87a'),
    }

    EXTENSIONS = list(SUPPORTED_EXTENSIONS.keys())

    # Low timeout to avoid unnecessary hangs of GUIs
    TIMEOUT = 5

    def __init__(self, core):
        self.core = core

    def get_cover(self, podcast, download=False):
        filename = podcast.cover_file
        cover_url = podcast.cover_url

        # Return already existing files
        for extension in self.EXTENSIONS:
            if os.path.exists(filename + extension):
                return filename + extension

        # If allowed to download files, do so here
        if download:
            # YouTube-specific cover art image resolver
            youtube_cover_url = youtube.get_real_cover(podcast.url)
            if youtube_cover_url is not None:
                cover_url = youtube_cover_url

            if not cover_url:
                return None

            # We have to add username/password, because password-protected
            # feeds might keep their cover art also protected (bug 1521)
            cover_url = util.url_add_authentication(cover_url,
                    podcast.auth_username, podcast.auth_password)

            try:
                logger.info('Downloading cover art: %s', cover_url)
                data = util.urlopen(cover_url, timeout=self.TIMEOUT).read()
            except Exception as e:
                logger.warn('Cover art download failed: %s', e)
                return None

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
                logger.warn('Cannot save cover art', exc_info=True)

        return None

