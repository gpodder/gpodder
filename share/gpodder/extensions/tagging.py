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
import logging
import mimetypes

from mutagen import File
from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4Tags
from mutagen.flac import Picture
from mutagen.id3 import APIC, ID3
from mutagen.mp3 import MP3, EasyMP3
from mutagen.mp4 import MP4Cover, MP4Tags

import gpodder
from gpodder import coverart

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

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
    'always_remove_tags': False,
    'auto_embed_coverart': False,
    'set_artist_to_album': True,
    'set_version': 4,
    'modify_tags': True,
    'remove_before_modify': True,

    'write_title': True,
    'write_album': True,
    'write_subtitle': False,
    'write_comments': False,
    'write_genre': True,
    'write_pubdate': True,
}


class AudioFile(object):
    def __init__(self, filename, album, title, subtitle, genre, pubDate, cover):
        self.filename = filename
        self.album = album
        self.title = title
        self.subtitle = subtitle
        self.genre = genre
        self.pubDate = pubDate
        self.cover = cover

    def remove_tags(self):
        audio = File(self.filename, easy=True)
        if audio.tags is not None:
            audio.delete()
        audio.save()

    def write_basic_tags(self, remove_before_modify, modify_tags, set_artist_to_album, set_version,
                         write_album, write_title, write_subtitle, write_comments, write_genre, write_pubdate):
        audio = File(self.filename, easy=True)

        if audio is None:
            logger.warning("Unable to add tags to file '%s'", self.filename)
            return

        if audio.tags is None:
            audio.add_tags()

        if modify_tags:
            if remove_before_modify:
                logger.info("removing before writing")
                audio.delete()

            if write_album is True and self.album is not None:
                logger.info("writing album")
                audio.tags['album'] = self.album

            if write_title is True and self.title is not None:
                logger.info("writing title")
                audio.tags['title'] = self.title

            if write_subtitle is True and self.subtitle is not None:
                logger.info("writing subtitle")
                audio.tags['subtitle'] = self.subtitle

            if write_comments is True and self.subtitle is not None:
                logger.info("writing comments")
                audio.tags['comments'] = self.subtitle

            if write_genre is True and self.genre is not None:
                logger.info("writing genre")
                audio.tags['genre'] = self.genre

            if write_pubdate is True and self.pubDate is not None:
                logger.info("writing date")
                audio.tags['date'] = self.pubDate

            if set_artist_to_album:
                logger.info("writing artist")
                audio.tags['artist'] = self.album

        if type(audio) is EasyMP3:
            audio.save(v2_version=set_version)
        else:
            # Not actually audio
            audio.save()

    def insert_coverart(self):
        """Implement the cover art logic in the subclass."""
        None

    def get_cover_picture(self, cover):
        """Return mutagen Picture class for the cover image.

        Useful for OGG and FLAC format

        Picture type = cover image
        see http://flac.sourceforge.net/documentation_tools_flac.html#encoding_options
        """
        f = open(cover, mode='rb')
        p = Picture()
        p.type = 3
        p.data = f.read()
        p.mime = mimetypes.guess_type(cover)[0]
        f.close()

        return p


class OggFile(AudioFile):
    def __init__(self, filename, album, title, subtitle, genre, pubDate, cover):
        super(OggFile, self).__init__(filename, album, title, subtitle, genre, pubDate, cover)

    def insert_coverart(self):
        audio = File(self.filename, easy=True)
        p = self.get_cover_picture(self.cover)
        audio['METADATA_BLOCK_PICTURE'] = base64.b64encode(p.write())
        audio.save()


class Mp4File(AudioFile):
    def __init__(self, filename, album, title, subtitle, genre, pubDate, cover):
        super(Mp4File, self).__init__(filename, album, title, subtitle, genre, pubDate, cover)

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
    def __init__(self, filename, album, title, subtitle, genre, pubDate, cover):
        super(Mp3File, self).__init__(filename, album, title, subtitle, genre, pubDate, cover)

    def insert_coverart(self):
        audio = MP3(self.filename, ID3=ID3)

        if audio.tags is None:
            audio.add_tags()

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
                cover)
        return audio

    def read_episode_info(self, episode):
        info = {
            'filename': None,
            'album': None,
            'title': None,
            'subtitle': None,
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

        return info

    def write_info2file(self, info, episode):
        audio = self.get_audio(info, episode)

        if self.container.config.always_remove_tags:
            audio.remove_tags()
        else:
            audio.write_basic_tags(self.container.config.remove_before_modify,
                                   self.container.config.modify_tags,
                                   self.container.config.set_artist_to_album,
                                   self.container.config.set_version,
                                   self.container.config.write_album,
                                   self.container.config.write_title,
                                   self.container.config.write_subtitle,
                                   self.container.config.write_comments,
                                   self.container.config.write_genre,
                                   self.container.config.write_pubdate)

            if self.container.config.auto_embed_coverart:
                audio.insert_coverart()

        logger.info('tagging.on_episode_downloaded(%s/%s)', episode.channel.title, episode.title)

    def get_cover(self, podcast):
        downloader = coverart.CoverDownloader()
        return downloader.get_cover(podcast.cover_file, podcast.cover_url,
            podcast.url, podcast.title, None, None, True)
    
    def toggle_sensitivity_of_widgets(self):
        if not self.container.config.always_remove_tags:
            self.container.modify_tags.set_sensitive(True)
            self.container.remove_before_modify.set_sensitive(self.container.config.modify_tags)
            self.container.write_album.set_sensitive(self.container.config.modify_tags)
            self.container.write_title.set_sensitive(self.container.config.modify_tags)
            self.container.write_subtitle.set_sensitive(self.container.config.modify_tags)
            self.container.write_comments.set_sensitive(self.container.config.modify_tags)
            self.container.write_comments_note.set_sensitive(self.container.config.modify_tags)
            self.container.write_genre.set_sensitive(self.container.config.modify_tags)
            self.container.write_pubdate.set_sensitive(self.container.config.modify_tags)
            self.container.set_artist_to_album.set_sensitive(self.container.config.modify_tags)
            self.container.auto_embed_coverart.set_sensitive(True)
            self.container.note1.set_sensitive(True)

            if self.container.config.modify_tags:
                self.container.hbox_genre_tag.set_sensitive(self.container.config.write_genre)
                self.container.strip_album_from_title.set_sensitive(self.container.config.write_title)
            else:
                self.container.hbox_genre_tag.set_sensitive(False)
                self.container.strip_album_from_title.set_sensitive(False)

        else:
            self.container.modify_tags.set_sensitive(False)
            self.container.remove_before_modify.set_sensitive(False)
            self.container.write_album.set_sensitive(False)
            self.container.write_title.set_sensitive(False)
            self.container.strip_album_from_title.set_sensitive(False)
            self.container.write_subtitle.set_sensitive(False)
            self.container.write_comments.set_sensitive(False)
            self.container.write_comments_note.set_sensitive(False)
            self.container.write_genre.set_sensitive(False)
            self.container.write_pubdate.set_sensitive(False)
            self.container.set_artist_to_album.set_sensitive(False)
            self.container.auto_embed_coverart.set_sensitive(False)
            self.container.note1.set_sensitive(False)
            self.container.hbox_genre_tag.set_sensitive(False)

    def toggle_always_remove_tags(self, widget):
        self.container.config.always_remove_tags = widget.get_active()
        self.toggle_sensitivity_of_widgets()

    def toggle_auto_embed_coverart(self, widget):
        self.container.config.auto_embed_coverart = widget.get_active()

    def toggle_remove_before_modify(self, widget):
        self.container.config.remove_before_modify = widget.get_active()
    
    def toggle_set_artist_to_album(self, widget):
        self.container.config.set_artist_to_album = widget.get_active()
    
    def toggle_modify_tags(self, widget):
        self.container.config.modify_tags = widget.get_active()
        self.toggle_sensitivity_of_widgets()
    
    def toggle_strip_album_from_title(self, widget):
        self.container.config.strip_album_from_title = widget.get_active()
    
    def toggle_write_title(self, widget):
        self.container.config.write_title = widget.get_active()
        self.toggle_sensitivity_of_widgets()

    def toggle_write_album(self, widget):
        self.container.config.write_album = widget.get_active()
    
    def toggle_write_subtitle(self, widget):
        self.container.config.write_subtitle = widget.get_active()

    def toggle_write_comments(self, widget):
        self.container.config.write_comments = widget.get_active()

    def toggle_write_genre(self, widget):
        self.container.config.write_genre = widget.get_active()
        self.toggle_sensitivity_of_widgets()

    def toggle_write_pubdate(self, widget):
        self.container.config.write_pubdate = widget.get_active()
    
    def on_genre_tag_changed(self, widget):
        self.container.config.genre_tag = widget.get_text()
    
    # destroy references to widgets which don't exist anymore
    def on_box_destroy(self, widget):
        del(self.container.always_remove_tags)
        del(self.container.remove_before_modify)
        del(self.container.modify_tags)
        del(self.container.write_title)
        del(self.container.write_album)
        del(self.container.write_subtitle)
        del(self.container.write_comments)
        del(self.container.write_comments_note)
        del(self.container.write_genre)
        del(self.container.write_pubdate)
        del(self.container.set_artist_to_album)
        del(self.container.strip_album_from_title)
        del(self.container.genre_tag)
        del(self.container.genre_tag_label)
        del(self.container.hbox_genre_tag)
        del(self.container.auto_embed_coverart)
        del(self.container.note1)
        None

    def show_preferences(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        title = Gtk.Label(use_markup=True, label=_('<b><big>Tagging Extension</big></b>'))
        title.set_halign(Gtk.Align.CENTER)
        box.add(title)

        whatisthis = Gtk.Label(use_markup=True, wrap=True, label=_(
            'This extension writes tags on episodes after download.'
        ))
        whatisthis.set_property('xalign', 0.0)
        box.add(whatisthis)

        box.pack_start(Gtk.HSeparator(), False, False, 0)

        self.container.always_remove_tags = Gtk.CheckButton(_('Only Remove Existing Tags'))
        self.container.always_remove_tags.set_active(self.container.config.always_remove_tags)
        self.container.always_remove_tags.connect('toggled', self.toggle_always_remove_tags)
        box.pack_start(self.container.always_remove_tags, False, False, 0)

        self.container.modify_tags = Gtk.CheckButton(_('Modify tags'))
        self.container.modify_tags.set_active(self.container.config.modify_tags)
        self.container.modify_tags.connect('toggled', self.toggle_modify_tags)
        box.pack_start(self.container.modify_tags, False, False, 0)

        self.container.remove_before_modify = Gtk.CheckButton(_('Remove existing tags before writing'))
        self.container.remove_before_modify.set_active(self.container.config.remove_before_modify)
        self.container.remove_before_modify.connect('toggled', self.toggle_remove_before_modify)
        box.pack_start(self.container.remove_before_modify, False, False, 0)

        box.pack_start(Gtk.HSeparator(), False, False, 0)

        self.container.write_title = Gtk.CheckButton(_('Write Title tag'))
        self.container.write_title.set_active(self.container.config.write_title)
        self.container.write_title.connect('toggled', self.toggle_write_title)
        box.pack_start(self.container.write_title, False, False, 0)

        self.container.write_album = Gtk.CheckButton(_('Write Album tag'))
        self.container.write_album.set_active(self.container.config.write_album)
        self.container.write_album.connect('toggled', self.toggle_write_album)
        box.pack_start(self.container.write_album, False, False, 0)

        self.container.set_artist_to_album = Gtk.CheckButton(_('Write Artist tag (to same as Album)'))
        self.container.set_artist_to_album.set_active(self.container.config.set_artist_to_album)
        self.container.set_artist_to_album.connect('toggled', self.toggle_set_artist_to_album)
        box.pack_start(self.container.set_artist_to_album, False, False, 0)

        self.container.write_subtitle = Gtk.CheckButton(_('Write Subtitle tag'))
        self.container.write_subtitle.set_active(self.container.config.write_subtitle)
        self.container.write_subtitle.connect('toggled', self.toggle_write_subtitle)
        box.pack_start(self.container.write_subtitle, False, False, 0)

        self.container.write_comments = Gtk.CheckButton(_('Write Comments tag (to same as Subtitle)'))
        self.container.write_comments.set_active(self.container.config.write_comments)
        self.container.write_comments.connect('toggled', self.toggle_write_comments)
        box.pack_start(self.container.write_comments, False, False, 0)

        self.container.write_comments_note = Gtk.Label(_('Note: Subtitle is often very long. Can cause parsing issues.'))
        self.container.write_comments_note.set_property('xalign', 0.0)
        box.add(self.container.write_comments_note)

        self.container.write_genre = Gtk.CheckButton(_('Write Genre tag'))
        self.container.write_genre.set_active(self.container.config.write_genre)
        self.container.write_genre.connect('toggled', self.toggle_write_genre)
        box.pack_start(self.container.write_genre, False, False, 0)

        self.container.write_pubdate = Gtk.CheckButton(_('Write Publish Date tag'))
        self.container.write_pubdate.set_active(self.container.config.write_pubdate)
        self.container.write_pubdate.connect('toggled', self.toggle_write_pubdate)
        box.pack_start(self.container.write_pubdate, False, False, 0)

        box.pack_start(Gtk.HSeparator(), False, False, 0)

        self.container.strip_album_from_title = Gtk.CheckButton(_('Remove Album from Title (if present)'))
        self.container.strip_album_from_title.set_active(self.container.config.strip_album_from_title)
        self.container.strip_album_from_title.connect('toggled', self.toggle_strip_album_from_title)
        box.pack_start(self.container.strip_album_from_title, False, False, 0)

        self.container.genre_tag = Gtk.Entry()
        self.container.genre_tag.set_text(self.container.config.genre_tag)
        self.container.genre_tag.connect("changed", self.on_genre_tag_changed)
        self.container.genre_tag.set_halign(Gtk.Align.END)
        self.container.genre_tag.set_size_request(200, -1)
        self.container.genre_tag_label = Gtk.Label(_('Genre tag:'))
        self.container.hbox_genre_tag = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.container.hbox_genre_tag.pack_start(self.container.genre_tag_label, False, False, 0)
        self.container.hbox_genre_tag.pack_start(self.container.genre_tag, True, True, 0)
        box.pack_start(self.container.hbox_genre_tag, False, False, 0)

        box.pack_start(Gtk.HSeparator(), False, False, 0)

        self.container.auto_embed_coverart = Gtk.CheckButton(_('Embed coverart'))
        self.container.auto_embed_coverart.set_active(self.container.config.auto_embed_coverart)
        self.container.auto_embed_coverart.connect('toggled', self.toggle_auto_embed_coverart)
        box.pack_start(self.container.auto_embed_coverart, False, False, 0)

        self.container.note1 = Gtk.Label(use_markup=True, wrap=True, label=_(
            'Note: Coverart is not standardized in any way, so results may vary.'))
        self.container.note1.set_property('xalign', 0.0)
        box.add(self.container.note1)

        box.connect("destroy", self.on_box_destroy)

        self.toggle_sensitivity_of_widgets()

        box.show_all()
        return box

    def on_preferences(self):
        return [(_('Tagging'), self.show_preferences)]