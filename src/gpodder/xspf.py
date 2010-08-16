#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2010 Thomas Perl and the gPodder Team
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

# XSPF playlist parser module for gPodder
# Thomas Perl <thpinfo.com>; 2010-08-07


# Currently, this is restricted to FM4 On Demand content, as the XSPF parser
# here isn't generic enough to parse all other feeds reliably. Please get in
# touch if you want support for other feeds - you can use the existing parser
# as a template for your own! :)
#
# See http://fm4.orf.at/radio/stories/audio for available feeds


import gpodder

_ = gpodder.gettext

from gpodder import model
from gpodder import util

import os
import time

import re
import feedparser

from xml.dom import minidom


def get_metadata(url):
    """Get file download metadata

    Returns a (size, type, name) from the given download
    URL. Will use the network connection to determine the
    metadata via the HTTP header fields.
    """
    track_fp = util.urlopen(url)
    headers = track_fp.info()
    filesize = headers['content-length'] or '0'
    filetype = headers['content-type'] or 'application/octet-stream'

    if 'last-modified' in headers:
        parsed_date = feedparser._parse_date(headers['last-modified'])
        filedate = time.mktime(parsed_date)
    else:
        filedate = None

    filename = os.path.basename(os.path.dirname(url))
    track_fp.close()
    return filesize, filetype, filedate, filename


class FM4OnDemandPlaylist(object):
    URL_REGEX = re.compile('http://onapp1\.orf\.at/webcam/fm4/fod/([^/]+)\.xspf$')
    CONTENT = {
            'spezialmusik': (
                'FM4 Sendungen',
                'http://onapp1.orf.at/webcam/fm4/fod/SOD_Bild_Spezialmusik.jpg',
                'http://fm4.orf.at/',
                'Sendungen jeweils sieben Tage zum Nachhören.',
            ),
            'unlimited': (
                'FM4 Unlimited',
                'http://onapp1.orf.at/webcam/fm4/fod/SOD_Bild_Unlimited.jpg',
                'http://fm4.orf.at/unlimited',
                'Montag bis Freitag (14-15 Uhr)',
            ),
            'soundpark': (
                'FM4 Soundpark',
                'http://onapp1.orf.at/webcam/fm4/fod/SOD_Bild_Soundpark.jpg',
                'http://fm4.orf.at/soundpark',
                'Nacht von Sonntag auf Montag (1-6 Uhr)',
            ),
    }

    @classmethod
    def handle_url(cls, url):
        m = cls.URL_REGEX.match(url)
        if m is not None:
            category = m.group(1)
            return cls(url, category)

    @classmethod
    def get_text_contents(cls, node):
        if hasattr(node, '__iter__'):
            return u''.join(cls.get_text_contents(x) for x in node)
        elif node.nodeType == node.TEXT_NODE:
            return node.data
        else:
            return u''.join(cls.get_text_contents(c) for c in node.childNodes)

    def __init__(self, url, category):
        self.url = url
        self.category = category
        # TODO: Use proper caching of contents with support for
        #       conditional GETs (If-Modified-Since, ETag, ...)
        self.data = minidom.parse(util.urlopen(url))
        self.playlist = self.data.getElementsByTagName('playlist')[0]

    def get_title(self):
        title = self.playlist.getElementsByTagName('title')[0]
        default = self.get_text_contents(title)
        return self.CONTENT.get(self.category, \
                (default, None, None, None))[0]

    def get_image(self):
        return self.CONTENT.get(self.category, \
                (None, None, None, None))[1]

    def get_link(self):
        return self.CONTENT.get(self.category, \
                (None, None, 'http://fm4.orf.at/', None))[2]

    def get_description(self):
        return self.CONTENT.get(self.category, \
                (None, None, None, 'XSPF playlist'))[3]

    def get_new_episodes(self, channel, guids):
        tracks = []

        for track in self.playlist.getElementsByTagName('track'):
            title = self.get_text_contents(track.getElementsByTagName('title'))
            url = self.get_text_contents(track.getElementsByTagName('location'))
            if url in guids:
                continue

            filesize, filetype, filedate, filename = get_metadata(url)
            episode = model.PodcastEpisode(channel)
            episode.update_from_dict({
                'title': title,
                'link': None,
                'description': '',
                'url': url,
                'length': int(filesize),
                'mimetype': filetype,
                'guid': url,
                'pubDate': filedate,
            })
            episode.save()
            tracks.append(episode)

        return len(tracks)


# Register our URL handlers
model.register_custom_handler(FM4OnDemandPlaylist)

