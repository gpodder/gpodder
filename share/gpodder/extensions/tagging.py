#!/usr/bin/python
# -*- coding: utf-8 -*-
####
# 01/2011 Bernd Schlapsi <brot@gmx.info>
#
# This script is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
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
# Dependencies:
# * python-mutagen (Mutagen is a Python module to handle audio metadata)
#
# This extension script adds episode title and podcast title to the audio file
# The episode title is written into the title tag
# The podcast title is written into the album tag

import base64
import datetime
import mimetypes
import os

import gpodder
from gpodder import coverart

import logging
logger = logging.getLogger(__name__)

from mutagen import File
from mutagen.flac import Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4Cover

_ = gpodder.gettext

__title__ = _('Tag downloaded files using Mutagen')
__description__ = _('Add episode and podcast titles to MP3/OGG tags')
__authors__ = 'Bernd Schlapsi <brot@gmx.info>'
__doc__ = 'http://wiki.gpodder.org/wiki/Extensions/Tagging'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/Tagging'
__category__ = 'post-download'


DefaultConfig = {
    'strip_album_from_title': True,
    'genre_tag': 'Podcast',
    'always_remove_tags': False,
    'auto_embed_coverart': False,
    'set_artist_to_album': False,
}


class AudioFile(object):
    def __init__(self, filename, album, title, genre, pubDate, cover):
        self.filename = filename
        self.album = album
        self.title = title
        self.genre = genre
        self.pubDate = pubDate
        self.cover = cover

    def remove_tags(self):
        audio = File(self.filename, easy=True)
        if audio.tags is not None:
            audio.delete()
        audio.save()

    def write_basic_tags(self):
        audio = File(self.filename, easy=True)

        if audio.tags is None:
            audio.add_tags()

        if self.album is not None:
            audio.tags['album'] = self.album

        if self.title is not None:
            audio.tags['title'] = self.title

        if self.genre is not None:
            audio.tags['genre'] = self.genre

        if self.pubDate is not None:
            audio.tags['date'] = self.pubDate

        if self.container.config.set_artist_to_album:
            audio.tags['artist'] = self.album

        audio.save()

    def insert_coverart(self):
        """ implement the cover art logic in the subclass
        """
        None

    def get_cover_picture(self, cover):
        """ Returns mutage Picture class for the cover image
        Usefull for OGG and FLAC format

        Picture type = cover image
        see http://flac.sourceforge.net/documentation_tools_flac.html#encoding_options
        """
        f = file(cover)
        p = Picture()
        p.type = 3
        p.data = f.read()
        p.mime = mimetypes.guess_type(cover)[0]
        f.close()

        return p


class OggFile(AudioFile):
    def __init__(self, filename, album, title, genre, pubDate, cover):
        super(OggFile, self).__init__(filename, album, title, genre, pubDate, cover)

    def insert_coverart(self):
        audio = File(self.filename, easy=True)
        p = self.get_cover_picture(self.cover)
        audio['METADATA_BLOCK_PICTURE'] = base64.b64encode(p.write())
        audio.save()


class Mp4File(AudioFile):
    def __init__(self, filename, album, title, genre, pubDate, cover):
        super(Mp4File, self).__init__(filename, album, title, genre, pubDate, cover)

    def insert_coverart(self):
        audio = File(self.filename)

        if self.cover.endswith('png'):
            cover_format = MP4Cover.FORMAT_PNG
        else:
            cover_format = MP4Cover.FORMAT_JPEG

        data = open(self.cover, 'rb').read()
        audio.tags['covr'] =  [MP4Cover(data, cover_format)]
        audio.save()


class Mp3File(AudioFile):
    def __init__(self, filename, album, title, genre, pubDate, cover):
        super(Mp3File, self).__init__(filename, album, title, genre, pubDate, cover)

    def insert_coverart(self):
        audio = MP3(self.filename, ID3=ID3)

        if audio.tags is None:
            audio.add_tags()

        audio.tags.add(
            APIC(
                encoding = 3, # 3 is for utf-8
                mime = mimetypes.guess_type(self.cover)[0],
                type = 3,
                desc = u'Cover',
                data = open(self.cover).read()
            )
        )
        audio.save()


class gPodderExtension:
    def __init__(self, container):
        self.container = container

    def on_episode_downloaded(self, episode):
        info = self.read_episode_info(episode)
        if info['filename'] is None:
            return

        self.write_info2file(info, episode)

    def get_audio(self, info, episode):
        audio = None
        cover = None

        if self.container.config.auto_embed_coverart:
            cover = self.get_cover(episode.channel)

        if info['filename'].endswith('.mp3'):
            audio = Mp3File(info['filename'],
                info['album'],
                info['title'],
                info['genre'],
                info['pubDate'],
                cover)
        elif info['filename'].endswith('.ogg'):
            audio = OggFile(info['filename'],
                info['album'],
                info['title'],
                info['genre'],
                info['pubDate'],
                cover)
        elif info['filename'].endswith('.m4a') or info['filename'].endswith('.mp4'):
            audio = Mp4File(info['filename'],
                info['album'],
                info['title'],
                info['genre'],
                info['pubDate'],
                cover)

        return audio

    def read_episode_info(self, episode):
        info = {
            'filename': None,
            'album': None,
            'title': None,
            'genre': None,
            'pubDate': None
        }

        # read filename (incl. file path) from gPodder database
        info['filename'] = episode.local_filename(create=False, check_only=True)
        if info['filename'] is None:
            return

        # read title+album from gPodder database
        info['album'] = episode.channel.title
        title = episode.title
        if (self.container.config.strip_album_from_title and title and info['album'] and title.startswith(info['album'])):
            info['title'] = title[len(info['album']):].lstrip()
        else:
            info['title'] = title

        if self.container.config.genre_tag is not None:
            info['genre'] = self.container.config.genre_tag

        # convert pubDate to string
        try:
            pubDate = datetime.datetime.fromtimestamp(episode.pubDate)
            info['pubDate'] = pubDate.strftime('%Y-%m-%d %H:%M')
        except:
            try:
                # since version 3 the published date has a new/other name
                pubDate = datetime.datetime.fromtimestamp(episode.published)
                info['pubDate'] = pubDate.strftime('%Y-%m-%d %H:%M')
            except:
                info['pubDate'] = None

        return info

    def write_info2file(self, info, episode):
        audio = self.get_audio(info, episode)

        if self.container.config.always_remove_tags:
            audio.remove_tags()
        else:
            audio.write_basic_tags()

            if self.container.config.auto_embed_coverart:
                audio.insert_coverart()

        logger.info(u'tagging.on_episode_downloaded(%s/%s)', episode.channel.title, episode.title)

    def get_cover(self, podcast):
        downloader = coverart.CoverDownloader()
        return downloader.get_cover(podcast.cover_file, podcast.cover_url,
            podcast.url, podcast.title, None, None, True)
