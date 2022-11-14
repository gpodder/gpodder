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
#  gpodder.vimeo - Vimeo download magic
#  Thomas Perl <thp@gpodder.org>; 2012-01-03
#


import logging
import re

import gpodder
from gpodder import registry, util

_ = gpodder.gettext

logger = logging.getLogger(__name__)


VIMEOCOM_RE = re.compile(r'http[s]?://vimeo\.com/(channels/[^/]+|\d+)$', re.IGNORECASE)
VIMEOCOM_VIDEO_RE = re.compile(r'http[s]?://vimeo.com/channels/(?:[^/])+/(\d+)$', re.IGNORECASE)
MOOGALOOP_RE = re.compile(r'http[s]?://vimeo\.com/moogaloop\.swf\?clip_id=(\d+)$', re.IGNORECASE)
SIGNATURE_RE = re.compile(r'"timestamp":(\d+),"signature":"([^"]+)"')

# List of qualities, from lowest to highest
FILEFORMAT_RANKING = ['270p', '360p', '720p', '1080p']

FORMATS = tuple((x, x) for x in FILEFORMAT_RANKING)


class VimeoError(BaseException): pass


@registry.download_url.register
def vimeo_real_download_url(config, episode, allow_partial):
    fmt = config.vimeo.fileformat if config else None
    res = get_real_download_url(episode.url, preferred_fileformat=fmt)
    return None if res == episode.url else res


def get_real_download_url(url, preferred_fileformat=None):
    video_id = get_vimeo_id(url)

    if video_id is None:
        return url

    data_config_url = 'https://player.vimeo.com/video/%s/config' % (video_id,)

    def get_urls(data_config_url):
        data_config = util.urlopen(data_config_url).json()
        for fileinfo in list(data_config['request']['files'].values()):
            if not isinstance(fileinfo, list):
                continue

            for item in fileinfo:
                yield (item['quality'], item['url'])

    fileformat_to_url = dict(get_urls(data_config_url))

    if preferred_fileformat is not None and preferred_fileformat in fileformat_to_url:
        logger.debug('Picking preferred format: %s', preferred_fileformat)
        return fileformat_to_url[preferred_fileformat]

    def fileformat_sort_key_func(fileformat):
        if fileformat in FILEFORMAT_RANKING:
            return FILEFORMAT_RANKING.index(fileformat)

        return 0

    for fileformat in sorted(fileformat_to_url, key=fileformat_sort_key_func, reverse=True):
        logger.debug('Picking best format: %s', fileformat)
        return fileformat_to_url[fileformat]

    return url


def get_vimeo_id(url):
    result = MOOGALOOP_RE.match(url)
    if result is not None:
        return result.group(1)

    result = VIMEOCOM_RE.match(url)
    if result is not None:
        return result.group(1)

    result = VIMEOCOM_VIDEO_RE.match(url)
    if result is not None:
        return result.group(1)

    return None


def is_video_link(url):
    return (get_vimeo_id(url) is not None)


def get_real_channel_url(url):
    result = VIMEOCOM_RE.match(url)
    if result is not None:
        return 'http://vimeo.com/%s/videos/rss' % result.group(1)

    return url


def get_real_cover(url):
    return None
