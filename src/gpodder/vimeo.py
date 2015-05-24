# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2015 Thomas Perl and the gPodder Team
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


import gpodder

_ = gpodder.gettext

from gpodder import util

import logging
logger = logging.getLogger(__name__)

try:
    # For Python < 2.6, we use the "simplejson" add-on module
    import simplejson as json
except ImportError:
    # Python 2.6 already ships with a nice "json" module
    import json

import re

VIMEOCOM_RE = re.compile(r'http://vimeo\.com/(\d+)$', re.IGNORECASE)
MOOGALOOP_RE = re.compile(r'http://vimeo\.com/moogaloop\.swf\?clip_id=(\d+)$', re.IGNORECASE)
SIGNATURE_RE = re.compile(r'"timestamp":(\d+),"signature":"([^"]+)"')
DATA_CONFIG_RE = re.compile(r'data-config-url="([^"]+)"')

# List of qualities, from lowest to highest
FILEFORMAT_RANKING = ['mobile', 'sd', 'hd']

FORMATS = (
        ('mobile', _('Mobile')),
        ('sd', _('SD')),
        ('hd', _('HD')),
)


class VimeoError(BaseException): pass

def get_real_download_url(url, preferred_fileformat=None):
    video_id = get_vimeo_id(url)

    if video_id is None:
        return url

    web_url = 'http://vimeo.com/%s' % video_id
    web_data = util.urlopen(web_url).read()
    data_config_frag = DATA_CONFIG_RE.search(web_data)

    if data_config_frag is None:
        raise VimeoError('Cannot get data config from Vimeo')

    data_config_url = data_config_frag.group(1).replace('&amp;', '&')

    def get_urls(data_config_url):
        data_config_data = util.urlopen(data_config_url).read().decode('utf-8')
        data_config = json.loads(data_config_data)
        for fileinfo in data_config['request']['files'].values():
            if not isinstance(fileinfo, dict):
                continue

            for fileformat, keys in fileinfo.items():
                if not isinstance(keys, dict):
                    continue

                yield (fileformat, keys['url'])

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

def get_vimeo_id(url):
    result = MOOGALOOP_RE.match(url)
    if result is not None:
        return result.group(1)

    result = VIMEOCOM_RE.match(url)
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

