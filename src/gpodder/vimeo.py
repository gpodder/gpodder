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
#  gpodder.vimeo - Vimeo download magic
#  Thomas Perl <thp@gpodder.org>; 2012-01-03
#


import gpodder

from gpodder import util

import logging
logger = logging.getLogger(__name__)

import re

VIMEOCOM_RE = re.compile(r'http://vimeo\.com/(\d+)$', re.IGNORECASE)
MOOGALOOP_RE = re.compile(r'http://vimeo\.com/moogaloop\.swf\?clip_id=(\d+)$', re.IGNORECASE)
SIGNATURE_RE = re.compile(r'"timestamp":(\d+),"signature":"([^"]+)"')

class VimeoError(BaseException): pass

def get_real_download_url(url):
    quality = 'sd'
    codecs = 'H264,VP8,VP6'

    video_id = get_vimeo_id(url)

    if video_id is None:
        return url

    web_url = 'http://vimeo.com/%s' % video_id
    web_data = util.urlopen(web_url).read()
    sig_pair = SIGNATURE_RE.search(web_data)

    if sig_pair is None:
        raise VimeoError('Cannot get signature pair from Vimeo')

    timestamp, signature = sig_pair.groups()
    params = '&'.join('%s=%s' % i for i in [
        ('clip_id', video_id),
        ('sig', signature),
        ('time', timestamp),
        ('quality', quality),
        ('codecs', codecs),
        ('type', 'moogaloop_local'),
        ('embed_location', ''),
    ])
    player_url = 'http://player.vimeo.com/play_redirect?%s' % params
    return player_url

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

