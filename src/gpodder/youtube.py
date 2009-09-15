# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
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
from gpodder.liblogger import log

import re
import urllib
import urllib2

from xml.sax import saxutils

def get_real_download_url(url, proxy=None):
    vid = get_youtube_id(url)
    if vid is not None:
        page = None
        url = 'http://www.youtube.com/watch?v=' + vid

        while page is None:
            req = util.proxy_request(url, proxy, method='GET')
            if 'location' in req.msg:
                url = req.msg['location']
            else:
                page = req.read()

        # Try to find the best video format available for this video
        # (http://forum.videohelp.com/topic336882-1800.html#1912972)
        r3 = re.compile('.*"fmt_map"\:\s+"([^"]+)".*').search(page)
        if r3:
            formats_available = urllib.unquote(r3.group(1)).split(',')
        else:
            formats_available = []

        # This is the proritized list of formats that gPodder will
        # use, depending on what is available from top to bottom.
        format_priorities = [
                '22/2000000/9/0/115', # 1280x720
                '35/640000/9/0/115',  # 640x360
                '18/512000/9/0/115',  # 480x270
                '34/0/9/0/115',       # 320x180
                '5/0/7/0/0',          # 320x180
        ]

        # FIXME: Don't use HD on Fremantle??

        fmt_id = 5
        for wanted in format_priorities:
            if wanted in formats_available:
                format, rest_ = wanted.split('/', 1)
                fmt_id = int(format)
                break

        # Hardcode fmt_id 5 for Maemo (for performance reasons) - we could
        # also use 13 and 17 here, but the quality is very low then. There
        # seems to also be a 6, but I could not find a video with that yet.
        if gpodder.ui.diablo:
            fmt_id = 5

        r2 = re.compile('.*"t"\:\s+"([^"]+)".*').search(page)
        if r2:
            next = 'http://www.youtube.com/get_video?video_id=' + vid + '&t=' + r2.group(1) + '&fmt=%d' % fmt_id
            log('YouTube link resolved: %s => %s', url, next)
            return next

    return url

def get_youtube_id(url):
    r = re.compile('http://(?:[a-z]+\.)?youtube\.com/v/(.*)\.swf', re.IGNORECASE).match(url)
    if r is not None:
        return r.group(1)

    r = re.compile('http://(?:[a-z]+\.)?youtube\.com/watch\?v=([^&]*)', re.IGNORECASE).match(url)
    if r is not None:
        return r.group(1)

    return None

def is_video_link(url):
    return (get_youtube_id(url) is not None)

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
    r = re.compile('http://www\.youtube\.com/rss/user/([^/]+)/videos\.rss', \
            re.IGNORECASE)
    m = r.match(url)

    if m is not None:
        username = m.group(1)
        api_url = 'http://gdata.youtube.com/feeds/api/users/%s?v=2' % username
        data = urllib2.urlopen(api_url).read()
        match = re.search('<media:thumbnail url=[\'"]([^\'"]+)[\'"]/>', data)
        if match is not None:
            log('YouTube userpic for %s is: %s', url, match.group(1))
            return match.group(1)

    return None

def get_real_episode_length(episode):
    url = get_real_download_url(episode.url)

    if url != episode.url:
        try:
            info = urllib2.urlopen(url).info()
            if 'content-length' in info:
                return info['content-length']
        except urllib2.HTTPError:
            pass

    return 0

def find_youtube_channels(string):
    # FIXME: Make proper use of the YouTube API instead
    # of screen-scraping the YouTube website
    url = 'http://www.youtube.com/results?search_query='+ urllib.quote(string, '') +'&search_type=search_users&aq=f'

    r = re.compile('>\s+<')
    data = r.sub('><', urllib2.urlopen(url).read())

    r1 = re.compile('<a href="/user/([^"]+)"[^>]*>([^<]+)</a>')
    m1 = r1.findall(data)

    r2 = re.compile('\s+')

    class FakeImporter(object):
        def __init__(self):
            self.items = []

    result = FakeImporter()
    found_users = []
    for name, title in m1:
        if name not in found_users:
            found_users.append(name)
            link = 'http://www.youtube.com/rss/user/'+ name +'/videos.rss'
            result.items.append({'title': name, 'url': link, 'description': title})

    return result

