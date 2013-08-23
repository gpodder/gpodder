# -*- coding: utf-8 -*-
#
# gpodder.plugins.vimeo: Vimeo download magic (2012-01-03)
# Copyright (c) 2012, 2013, Thomas Perl <m@thp.io>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.
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
    web_data = util.urlopen(web_url).read().decode('utf-8')
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

