# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
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
#  gpodder.escapist - Escapist Videos download magic
#  somini <somini29@yandex.com>; 2014-09-14
#


import gpodder

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

# This matches the more reliable URL
ESCAPIST_NUMBER_RE = re.compile(r'http://www.escapistmagazine.com/videos/view/(\d+)', re.IGNORECASE)
# This matches regular URL, mainly those that come in the RSS feeds
ESCAPIST_REGULAR_RE = re.compile(r'http://www.escapistmagazine.com/videos/view/([\w-]+)/(\d+)-', re.IGNORECASE)
# This finds the RSS for a given URL
DATA_RSS_RE = re.compile(r'http://www.escapistmagazine.com/rss/videos/list/([1-9][0-9]*)\.xml')
# This matches the flash player's configuration. It's a JSON, but it's always malformed
DATA_CONFIG_RE = re.compile(r'name="flashvars".*config=(http.*\.js)', re.IGNORECASE)
# This matches the actual MP4 url, inside the "JSON"
DATA_CONFIG_DATA_RE = re.compile(r'http[:/\w.?&-]*\.mp4')
# This matches the cover art for an RSS. We shouldn't parse XML with regex.
DATA_COVERART_RE = re.compile(r'<url>(http:.+\.jpg)</url>')

class EscapistError(BaseException): pass

def get_real_download_url(url):
    logger.info('Download: %s', url)
    video_id = get_escapist_id(url)
    if video_id is None:
        return url

    web_data = get_escapist_web(video_id)

    data_config_frag = DATA_CONFIG_RE.search(web_data)

    if data_config_frag is None:
        raise EscapistError('Cannot get flashvars URL from The Escapist')

    data_config_url = data_config_frag.group(1)

    data_config_data = util.urlopen(data_config_url).read().decode('utf-8')
    data_config_data_frag = DATA_CONFIG_DATA_RE.search(data_config_data)
    if data_config_data_frag is None:
        raise EscapistError('Cannot get configuration JS from The Escapist')
    real_url = data_config_data_frag.group(0)
    if real_url is None:
        raise EscapistError('Cannot get MP4 URL from The Escapist')
    return real_url

def get_escapist_id(url):
    result = ESCAPIST_NUMBER_RE.match(url)
    if result is not None:
        return result.group(1)

    result = ESCAPIST_REGULAR_RE.match(url)
    if result is not None:
        return result.group(2)

    return None

def is_video_link(url):
    return (get_escapist_id(url) is not None)

def get_real_channel_url(url):
    video_id = get_escapist_id(url)
    web_data = get_escapist_web(video_id)

    data_config_frag = DATA_RSS_RE.search(web_data)
    if data_config_frag is None:
        raise EscapistError('Cannot get RSS URL from The Escapist')
    return data_config_frag.group(0)

def get_real_cover(url):
    rss_url = get_real_channel_url(url)
    if rss_url is None:
        return None
    
    rss_data = util.urlopen(rss_url).read()
    rss_data_frag = DATA_COVERART_RE.search(rss_data)

    if rss_data_frag is None:
        return None

    return rss_data_frag.group(1)

def get_escapist_web(video_id):
    if video_id is None:
        return None

    web_url = 'http://www.escapistmagazine.com/videos/view/%s' % video_id
    return util.urlopen(web_url).read()

