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
# TODO:
# Review all changes to make sure they fallback if they have errors
# linting

import base64
import datetime
import logging
import mimetypes
import os

from mutagen import File
from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4Tags
from mutagen.flac import Picture
from mutagen.id3 import APIC, ID3
from mutagen.mp3 import MP3, EasyMP3
from mutagen.mp4 import MP4Cover, MP4Tags

import gpodder
from gpodder import coverart

logger = logging.getLogger(__name__)


# workaround for https://github.com/quodlibet/mutagen/issues/334
# can't add_tags to MP4 when file has no tag
MP4Tags._padding = 0

_ = gpodder.gettext

__title__ = _('Tag downloaded files using Mutagen')
__description__ = _('Add episode and podcast titles to MP3/OGG tags')
__authors__ = 'Bernd Schlapsi <brot@gmx.info>'
__doc__ = 'https://gpodder.github.io/docs/extensions/tagging.html'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/Tagging'
__category__ = 'post-download'


DefaultConfig = {
    'strip_album_from_title': True,
    'genre_tag': 'Podcast',
    'additional_genre_tags': False,
    'artist_tags': False,
    'always_remove_tags': False,
    'auto_embed_coverart': False,
    'use_episode_specific_cover': False,
    'set_artist_to_album': False,
    'set_episode_number_to_track': False,
    'set_season_number_to_disc': False,
    'set_version': 4,
    'modify_tags': True
}


class AudioFile(object):
    def __init__(self, filename, album, title, subtitle, genre, pubDate, cover, track_id, season, podcast_artist, episode_artist, categorys, keywords):
        self.filename = filename
        self.album = album
        self.title = title
        self.subtitle = subtitle
        self.genre = genre
        self.pubDate = pubDate
        self.cover = cover
        self.track_id = track_id
        self.season = season
        self.podcast_artist = podcast_artist
        self.episode_artist = episode_artist
        self.categorys = categorys
        self.keywords = keywords


    def remove_tags(self):
        audio = File(self.filename, easy=True)
        if audio.tags is not None:
            audio.delete()
        audio.save()

    def write_basic_tags(self, modify_tags, set_artist_to_album, set_version, set_episode_number_to_track, set_season_number_to_disc, additional_genre_tags, artist_tags):
        audio = File(self.filename, easy=True)

        if audio is None:
            logger.warning("Unable to add tags to file '%s'", self.filename)
            return

        if audio.tags is None:
            audio.add_tags()

        if modify_tags:
            if self.album is not None:
                audio.tags['album'] = self.album

            if self.title is not None:
                audio.tags['title'] = self.title

            if self.subtitle is not None:
                audio.tags['subtitle'] = self.subtitle

            if self.subtitle is not None:
                audio.tags['comments'] = self.subtitle

            if self.genre is not None:
                audio.tags['genre'] = self.genre

            if self.pubDate is not None:
                audio.tags['date'] = self.pubDate

            if set_artist_to_album:
                audio.tags['artist'] = self.album
            else:
                if self.podcast_artist is not None and artist_tags:
                    #use the podcast artist as album artist
                    #use the episode artist as track artist (if they are different)
                    #deliminate multiple artists with ' / '
                    audio.tags['albumartist'] = self.album

                    if self.podcast_artist != self.episode_artist:
                        audio.tags['artist'] = self.episode_artist
            
            if (self.categorys is not None or self.keywords is not None) and additional_genre_tags:
                #take self.categorys and self.keywords and merge them together into a single string, with ' / ' as the deliminator. only add the deliminator if both exist. otherwise just add the one that exists
                if self.categorys is not None and self.keywords is not None:
                    audio.tags['genre'] = self.categorys + ' / ' + self.keywords
                elif self.categorys is not None:
                    audio.tags['genre'] = self.categorys
                elif self.keywords is not None:
                    audio.tags['genre'] = self.keywords

            if self.track_id is not None and set_episode_number_to_track:
                audio.tags['tracknumber'] = str(self.track_id)
            
            if self.season is not None and set_season_number_to_disc:
                audio.tags['discnumber'] = str(self.season)

        if type(audio) is EasyMP3:
            audio.save(v2_version=set_version)
        else:
            # Not actually audio
            audio.save()

    def insert_coverart(self):
        """ implement the cover art logic in the subclass
        """
        None

    def get_cover_picture(self, cover):
        """ Returns mutagen Picture class for the cover image
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
    def __init__(self, filename, album, title, subtitle, genre, pubDate, cover, track_id, season, podcast_artists, episode_artists, categorys, keywords):
        super(OggFile, self).__init__(filename, album, title, subtitle, genre, pubDate, cover, track_id, season, podcast_artists, episode_artists, categorys, keywords)

    def insert_coverart(self):
        audio = File(self.filename, easy=True)
        p = self.get_cover_picture(self.cover)
        audio['METADATA_BLOCK_PICTURE'] = base64.b64encode(p.write())
        audio.save()


class Mp4File(AudioFile):
    def __init__(self, filename, album, title, subtitle, genre, pubDate, cover, track_id, season, podcast_artists, episode_artists, categorys, keywords):
        super(Mp4File, self).__init__(filename, album, title, subtitle, genre, pubDate, cover, track_id, season, podcast_artists, episode_artists, categorys, keywords)

    def insert_coverart(self):
        audio = File(self.filename)

        if self.cover.endswith('png'):
            cover_format = MP4Cover.FORMAT_PNG
        else:
            cover_format = MP4Cover.FORMAT_JPEG

        data = open(self.cover, 'rb').read()
        audio.tags['covr'] = [MP4Cover(data, cover_format)]
        audio.save()


class Mp3File(AudioFile):
    def __init__(self, filename, album, title, subtitle, genre, pubDate, cover, track_id, season, podcast_artists, episode_artists, categorys, keywords):
        super(Mp3File, self).__init__(filename, album, title, subtitle, genre, pubDate, cover, track_id, season, podcast_artists, episode_artists, categorys, keywords)

    def insert_coverart(self):
        audio = MP3(self.filename, ID3=ID3)

        if audio.tags is None:
            audio.add_tags()

        #add Front Cover image
        audio.tags.add(
            APIC(
                encoding=3,  # 3 is for utf-8
                mime=mimetypes.guess_type(self.cover)[0],
                type=3,
                desc='Cover',
                data=open(self.cover, 'rb').read()
            )
        )
        audio.save()


class gPodderExtension:
    def __init__(self, container):
        self.container = container
        # fix #737 EasyID3 doesn't recognize subtitle and comment tags
        EasyID3.RegisterTextKey("comments", "COMM")
        EasyID3.RegisterTextKey("subtitle", "TIT3")
        EasyMP4Tags.RegisterTextKey("comments", "desc")
        EasyMP4Tags.RegisterFreeformKey("subtitle", "SUBTITLE")

    def on_episode_downloaded(self, episode):
        info = self.read_episode_info(episode)
        if info['filename'] is None:
            return

        self.write_info2file(info, episode)

    def get_audio(self, info, episode):
        audio = None
        cover = None
        audioClass = None

        if self.container.config.auto_embed_coverart:
            if self.container.config.use_episode_specific_cover:
                cover = self.get_episode_cover(episode)
            else:
                cover = self.get_cover(episode.channel)

        if info['filename'].endswith('.mp3'):
            audioClass = Mp3File
        elif info['filename'].endswith('.ogg'):
            audioClass = OggFile
        elif info['filename'].endswith('.m4a') or info['filename'].endswith('.mp4'):
            audioClass = Mp4File
        elif File(info['filename'], easy=True):
            # mutagen can work with it: at least add basic tags
            audioClass = AudioFile

        if audioClass:
            audio = audioClass(info['filename'],
                info['album'],
                info['title'],
                info['subtitle'],
                info['genre'],
                info['pubDate'],
                cover,
                info['track_id'],
                info['season'],
                info["podcast_artist"],
                info["episode_artist"],
                info["categorys"],
                info["keywords"]),
        return audio

    def read_episode_info(self, episode):
        info = {
            'filename': None,
            'album': None,
            'title': None,
            'subtitle': None,
            'genre': None,
            'pubDate': None,
            'track_id': None,
            'season': None,
            'podcast_artist': None,
            'episode_artist': None,
            'categorys': None,
            'keywords': None,
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

        info['subtitle'] = episode._text_description

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
        
        # get track_id and season from the gPodder database
        info['track_id'] = episode.track_id
        info['season'] = episode.season

        # get podcast artist from the gPodder database
        info['podcast_artist'] = episode.channel.author

        # get episode artist from the gPodder database
        info['episode_artist'] = episode.author

        # get categorys from the gPodder database
        info['categorys'] = episode.channel.categorys

        # get keywords from the gPodder database
        info['keywords'] = episode.channel.keywords

        return info

    def write_info2file(self, info, episode):
        audio = self.get_audio(info, episode)

        if self.container.config.always_remove_tags:
            audio.remove_tags()
        else:
            audio.write_basic_tags(self.container.config.modify_tags,
                                   self.container.config.set_artist_to_album,
                                   self.container.config.set_version, 
                                   self.container.config.set_episode_number_to_track, 
                                   self.container.config.set_season_number_to_disc,
                                   self.container.config.additional_genre_tags,
                                   self.container.config.artist_tags)

            if self.container.config.auto_embed_coverart:
                audio.insert_coverart()

        logger.info('tagging.on_episode_downloaded(%s/%s)', episode.channel.title, episode.title)

    def get_cover(self, podcast):
        downloader = coverart.CoverDownloader()
        return downloader.get_cover(podcast.cover_file, podcast.cover_url,
            podcast.url, podcast.title, None, None, True)
        
    def get_episode_cover(self, episode):
        downloader = coverart.CoverDownloader()
        #check if episode has a cover
        if episode.cover_file is not None:
            return downloader.get_cover(episode.cover_file, episode.episode_art_url,
                episode.channel.url, episode.channel.title, None, None, True)
        else:
            #if not, just use the podcast cover
            return self.get_cover(episode.channel)