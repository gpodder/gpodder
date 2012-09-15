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
#  gpodder.youtube - YouTube and related magic
#  Justin Forest <justin.forest@gmail.com> 2008-10-13
#


import gpodder

from gpodder import util

import logging
logger = logging.getLogger(__name__)

try:
    import simplejson as json
except ImportError:
    import json

import re
import urllib
import urlparse

# See http://en.wikipedia.org/wiki/YouTube#Quality_and_codecs
# Currently missing: 3GP profile
supported_formats = [
    (37, '37/1920x1080/9/0/115', '1920x1080 (HD)'),
    (22, '22/1280x720/9/0/115', '1280x720 (HD)'),
    (35, '35/854x480/9/0/115', '854x480'),
    (34, '34/640x360/9/0/115', '640x360'),
    (18, '18/640x360/9/0/115', '640x360 (iPod)'),
    (18, '18/480x360/9/0/115', '480x360 (iPod)'),
    (5, '5/320x240/7/0/0', '320x240 (FLV)'),

    # WebM formats have lower priority, because "most" players are still less
    # compatible with WebM than their equivalent MP4 formats above (bug 1336)
    # If you really want WebM files, set the preferred fmt_id to any of these:
    (45, '45/1280x720/99/0/0', 'WebM 720p'),
    (44, '44/854x480/99/0/0', 'WebM 480p'),
    (43, '43/640x360/99/0/0', 'WebM 360p'),
]

class YouTubeError(Exception): pass

def get_real_download_url(url, preferred_fmt_id=None):
    # Default fmt_id when none preferred
    if preferred_fmt_id is None:
        preferred_fmt_id = 18

    vid = get_youtube_id(url)
    if vid is not None:
        page = None
        url = 'http://www.youtube.com/get_video_info?&video_id=' + vid

        while page is None:
            req = util.http_request(url, method='GET')
            if 'location' in req.msg:
                url = req.msg['location']
            else:
                page = req.read()

        # Try to find the best video format available for this video
        # (http://forum.videohelp.com/topic336882-1800.html#1912972)
        def find_urls(page):
            r4 = re.search('.*&url_encoded_fmt_stream_map=([^&]+)&.*', page)
            if r4 is not None:
                fmt_url_map = urllib.unquote(r4.group(1))
                for fmt_url_encoded in fmt_url_map.split(','):
                    video_info = urlparse.parse_qs(fmt_url_encoded)
                    yield int(video_info['itag'][0]), video_info['url'][0]

        fmt_id_url_map = sorted(find_urls(page), reverse=True)
        # Default to the highest fmt_id if we don't find a match below
        if fmt_id_url_map:
            default_fmt_id, default_url = fmt_id_url_map[0]
        else:
            raise YouTubeError('fmt_url_map not found for video ID "%s"' % vid)

        formats_available = set(fmt_id for fmt_id, url in fmt_id_url_map)
        fmt_id_url_map = dict(fmt_id_url_map)

        if gpodder.ui.harmattan:
            # This provides good quality video, seems to be always available
            # and is playable fluently in Media Player
            if preferred_fmt_id == 5:
                fmt_id = 5
            else:
                fmt_id = 18
        else:
            # As a fallback, use fmt_id 18 (seems to be always available)
            fmt_id = 18

            # This will be set to True if the search below has already "seen"
            # our preferred format, but has not yet found a suitable available
            # format for the given video.
            seen_preferred = False

            for id, wanted, description in supported_formats:
                # If we see our preferred format, accept formats below
                if id == preferred_fmt_id:
                    seen_preferred = True

                # If the format is available and preferred (or lower),
                # use the given format for our fmt_id
                if id in formats_available and seen_preferred:
                    logger.info('Found YouTube format: %s (fmt_id=%d)',
                            description, id)
                    fmt_id = id
                    break

        url = fmt_id_url_map.get(fmt_id, None)
        if url is None:
            url = default_url

    return url

def get_youtube_id(url):
    r = re.compile('http://(?:[a-z]+\.)?youtube\.com/v/(.*)\.swf', re.IGNORECASE).match(url)
    if r is not None:
        return r.group(1)

    r = re.compile('http://(?:[a-z]+\.)?youtube\.com/watch\?v=([^&]*)', re.IGNORECASE).match(url)
    if r is not None:
        return r.group(1)

    r = re.compile('http://(?:[a-z]+\.)?youtube\.com/v/(.*)[?]', re.IGNORECASE).match(url)
    if r is not None:
        return r.group(1)

    return None

def is_video_link(url):
    return (get_youtube_id(url) is not None)

def is_youtube_guid(guid):
    return guid.startswith('tag:youtube.com,2008:video:')

def get_real_channel_url(url):
    r = re.compile('http://(?:[a-z]+\.)?youtube\.com/user/([a-z0-9]+)', re.IGNORECASE)
    m = r.match(url)

    if m is not None:
        next = 'http://www.youtube.com/rss/user/'+ m.group(1) +'/videos.rss'
        logger.debug('YouTube link resolved: %s => %s', url, next)
        return next

    r = re.compile('http://(?:[a-z]+\.)?youtube\.com/profile?user=([a-z0-9]+)', re.IGNORECASE)
    m = r.match(url)

    if m is not None:
        next = 'http://www.youtube.com/rss/user/'+ m.group(1) +'/videos.rss'
        logger.debug('YouTube link resolved: %s => %s', url, next)
        return next

    return url

def get_real_cover(url):
    r = re.compile('http://www\.youtube\.com/rss/user/([^/]+)/videos\.rss', \
            re.IGNORECASE)
    m = r.match(url)

    if m is not None:
        username = m.group(1)
        api_url = 'http://gdata.youtube.com/feeds/api/users/%s?v=2' % username
        data = util.urlopen(api_url).read()
        match = re.search('<media:thumbnail url=[\'"]([^\'"]+)[\'"]/>', data)
        if match is not None:
            logger.debug('YouTube userpic for %s is: %s', url, match.group(1))
            return match.group(1)

    return None

def find_youtube_channels(string):
    url = 'http://gdata.youtube.com/feeds/api/videos?alt=json&q=%s' % urllib.quote(string, '')
    data = json.load(util.urlopen(url))

    class FakeImporter(object):
        def __init__(self):
            self.items = []

    result = FakeImporter()

    seen_users = set()
    for entry in data['feed']['entry']:
        user = entry['author'][0]['name']['$t']
        title = entry['title']['$t']
        url = 'http://www.youtube.com/rss/user/%s/videos.rss' % user
        if user not in seen_users:
            result.items.append({
                'title': user,
                'url': url,
                'description': title
            })
            seen_users.add(user)

    return result

