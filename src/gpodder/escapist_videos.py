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
import urllib

# This matches the more reliable URL
ESCAPIST_NUMBER_RE = re.compile(r'http://www.escapistmagazine.com/videos/view/(\d+)', re.IGNORECASE)
# This matches regular URL, mainly those that come in the RSS feeds
ESCAPIST_REGULAR_RE = re.compile(r'http://www.escapistmagazine.com/videos/view/([\w-]+)/(\d+)-', re.IGNORECASE)
# This finds the RSS for a given URL
DATA_RSS_RE = re.compile(r'http://www.escapistmagazine.com/rss/videos/list/([1-9][0-9]*)\.xml')
# This matches the "configuration". The important part is the JSON between the parens
DATA_CONFIG_RE = re.compile(r'imsVideo\.play\((.*)\)\;\<\/script\>', re.IGNORECASE)
# This matches the cover art for an RSS. We shouldn't parse XML with regex.
DATA_COVERART_RE = re.compile(r'<url>(http:.+\.jpg)</url>')

class EscapistError(BaseException): pass

def get_real_download_url(url):
    video_id = get_escapist_id(url)
    if video_id is None:
        return url

    web_data = get_escapist_web(video_id)

    data_config_frag = DATA_CONFIG_RE.search(web_data)

    data_config_url = get_escapist_config_url(data_config_frag.group(1))

    if data_config_url is None:
        raise EscapistError('Cannot parse configuration from the site')

    logger.debug('Config URL: %s', data_config_url)

    data_config_data = util.urlopen(data_config_url).read().decode('utf-8')

    #TODO: This second argument should get a real name
    real_url = get_escapist_real_url(data_config_data, data_config_frag.group(1))

    if real_url is None:
        raise EscapistError('Cannot get MP4 URL from The Escapist')
    elif "sales-marketing/" in real_url:
        raise EscapistError('Oops, seems The Escapist blocked this IP. Wait a few days/weeks to get it unblocked')
    else:
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
    if video_id is None:
        return url

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

def get_escapist_config_url(data):
    if data is None:
        return None

    query_string = urllib.urlencode(json.loads(data))

    return 'http://www.escapistmagazine.com/videos/vidconfig.php?%s' % query_string

def get_escapist_real_url(data, config_json):
    if data is None:
        return None

    config_data = json.loads(config_json)
    if config_data is None:
        return None

    ## The data is scrambled, unscramble
    ## Direct port from 'imsVideos.prototype.processRequest' from the file 'ims_videos.min.js'

    one_hash = config_data["hash"]
    # Turn the string into numbers
    hash_n = [ ord(x) for x in one_hash ]
    # Split the data into 2char strings
    hex_hashes = [ data[x:x+2] for x in range(0,len(data),2) ]
    # Turn the strings into numbers, considering the hex value
    num_hashes = [ int(h, 16) for h in hex_hashes ]
    # Characters again, from the value
    # str_hashes = [ unichr(n) for n in num_hashes ]

    # Bitwise XOR num_hashes and the hash
    result_num = []
    for idx in range(0,len(num_hashes)):
        result_num.append(num_hashes[idx]^hash_n[idx % len(hash_n)])

    # At last, Numbers back into characters
    result = ''.join([unichr(x) for x in result_num])
    # A wild JSON appears...
    # You use "Master Ball"...
    escapist_cfg = json.loads(result)
    # It's super effective!

    #TODO: There's a way to choose different video types, for now just pick MP4@480p
    return escapist_cfg["files"]["videos"][2]["src"]
