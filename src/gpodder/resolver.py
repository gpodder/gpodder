# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2008 Thomas Perl and the gPodder Team
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
#  resolver.py -- YouTube and related magic
#  Justin Forest <justin.forest@gmail.com> 2008-10-13
#
# TODO:
#
#   * Channel covers.
#   * Support for Vimeo, maybe blip.tv and others.

import re
import urllib2
from gpodder.liblogger import log
from gpodder.util import proxy_request

rr = {}

def get_real_download_url(url, proxy=None):
    if 'youtube-episode' not in rr:
        rr['youtube-episode'] = re.compile('http://(?:[a-z]+\.)?youtube\.com/v/.*\.swf', re.IGNORECASE)

    if rr['youtube-episode'].match(url):
        req = proxy_request(url, proxy)

        if 'location' in req.msg:
            id, tag = (None, None)

            for part in req.msg['location'].split('&'):
                if part.startswith('video_id='):
                    id = part[9:]
                elif part.startswith('t='):
                    tag = part[2:]

            if id is not None and tag is not None:
                next = 'http://www.youtube.com/get_video?video_id='+ id +'&t='+ tag +'&fmt=18'
                log('YouTube link resolved: %s => %s', url, next)
                return next

    return url

def get_real_channel_url(url):
    r = re.compile('http://(?:[a-z]+\.)?youtube\.com/user/([a-z0-9]+)', re.IGNORECASE)
    m = r.match(url)

    if m is not None:
        next = 'http://www.youtube.com/rss/user/'+ m.group(1) +'/videos.rss'
        log('YouTube link resolved: %s => %s', url, next)
        return next

    r = re.compile('http://(?:[a-z]+\.)?youtube\.com/profile?user=([a-z0-9]+)', re.IGNORECASE)
    m = r.match(url)

    if m is not None:
        next = 'http://www.youtube.com/rss/user/'+ m.group(1) +'/videos.rss'
        log('YouTube link resolved: %s => %s', url, next)
        return next

    return url

def get_real_cover(url):
    log('Cover: %s', url)

    r = re.compile('http://www\.youtube\.com/rss/user/([a-z0-9]+)/videos\.rss', re.IGNORECASE)
    m = r.match(url)

    if m is not None:
        data = urllib2.urlopen('http://www.youtube.com/user/'+ m.group(1)).read()
        data = data[data.find('id="user-profile-image"'):]
        data = data[data.find('src="') + 5:]

        next = data[:data.find('"')]

        if next.strip() == '':
            return None

        log('YouTube userpic for %s is: %s', url, next)
        return next

    return None

def get_real_episode_length(episode):
    url = get_real_download_url(episode.url)

    if url != episode.url:
        try:
            info = urllib2.urlopen(url).info()
            if 'content-length' in info:
                return info['content-length']
        except HTTPError:
            pass

    return 0
