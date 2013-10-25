#
# gpodder.plugins.xspf: XSPF playlist parser module for gPodder (2010-08-07)
# Copyright (c) 2010-2013, Thomas Perl <m@thp.io>
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


# Currently, this is restricted to FM4 On Demand content, as the XSPF parser
# here isn't generic enough to parse all other feeds reliably. Please get in
# touch if you want support for other feeds - you can use the existing parser
# as a template for your own! :)
#
# See http://fm4.orf.at/radio/stories/audio for available feeds


import gpodder

from gpodder import model
from gpodder import util

import podcastparser

import os
import time

import re

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
        filedate = podcastparser.parse_date(headers['last-modified'])
    else:
        filedate = None

    filename = os.path.basename(os.path.dirname(url))
    track_fp.close()
    return filesize, filetype, filedate, filename


class FM4OnDemandPlaylist(object):
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
    def get_text_contents(cls, node):
        if hasattr(node, '__iter__'):
            return ''.join(cls.get_text_contents(x) for x in node)
        elif node.nodeType == node.TEXT_NODE:
            return node.data
        else:
            return ''.join(cls.get_text_contents(c) for c in node.childNodes)

    def __init__(self, url, category):
        self.url = url
        self.category = category
        # TODO: Use proper caching of contents with support for
        #       conditional GETs (If-Modified-Since, ETag, ...)
        self.data = minidom.parse(util.urlopen(url))
        self.playlist = self.data.getElementsByTagName('playlist')[0]

    def was_updated(self):
        return True

    def get_etag(self, default):
        return default

    def get_modified(self, default):
        return default

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

    def get_payment_url(self):
        return None

    def get_new_episodes(self, channel):
        tracks = []
        existing_guids = [episode.guid for episode in channel.children]
        seen_guids = []

        for track in self.playlist.getElementsByTagName('track'):
            title = self.get_text_contents(track.getElementsByTagName('title'))
            url = self.get_text_contents(track.getElementsByTagName('location'))
            seen_guids.append(url)
            if url in existing_guids:
                continue

            filesize, filetype, filedate, filename = get_metadata(url)
            episode = channel.episode_factory({
                'title': title,
                'link': '',
                'description': '',
                'url': url,
                'file_size': int(filesize),
                'mime_type': filetype,
                'guid': url,
                'published': filedate,
            })
            episode.save()
            tracks.append(episode)

        return tracks, seen_guids

@model.register_custom_handler
def fm4_on_demand_playlist_handler(channel, max_episodes):
    m = re.match(r'http://onapp1\.orf\.at/webcam/fm4/fod/([^/]+)\.xspf$', channel.url)

    if m is not None:
        category = m.group(1)
        return FM4OnDemandPlaylist(channel.url, category)

