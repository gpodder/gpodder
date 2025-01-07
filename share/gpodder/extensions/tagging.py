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
from io import BytesIO

import gi
from mutagen import File
from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4Tags
from mutagen.flac import Picture
from mutagen.id3 import APIC, ID3
from mutagen.mp3 import MP3, EasyMP3
from mutagen.mp4 import MP4Cover, MP4Tags
from PIL import Image

import gpodder
from gpodder import coverart

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
    'set_artist_to_album': True,
    'set_version': 4,
    'modify_tags': True,
    'remove_before_modify': True,

    'embed_coverart': False,
    'prefer_channel_coverart': False,
    'normalize_coverart': True,
    'episode_coverart_size': 500,
    'episode_coverart_filetype': 0,

    'write_title': True,
    'write_album': True,
    'write_subtitle': False,
    'write_comments': False,
    'write_genre': True,
    'write_pubdate': True,
}


class AudioFile(object):
    def __init__(self, filename, album, title, subtitle, genre, pubDate):
        self.filename = filename
        self.album = album
        self.title = title
        self.subtitle = subtitle
        self.genre = genre
        self.pubDate = pubDate

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

    def extract_coverart(self):
        """Implement the cover art logic in the subclass."""
        None

    def insert_coverart(self, image=None, mimetype=None):
        """Implement the cover art logic in the subclass."""
        None

    def get_cover_picture(self, cover, mimetype):
        """Return mutagen FLAC Picture class for the cover image.

        Useful for OGG and FLAC format

        Picture type = cover image
        see http://flac.sourceforge.net/documentation_tools_flac.html#encoding_options
        """
        p = Picture()
        p.type = 3
        p.data = cover
        p.mime = mimetype

        return p


class OggFile(AudioFile):
    def __init__(self, filename, album, title, subtitle, genre, pubDate):
        super(OggFile, self).__init__(filename, album, title, subtitle, genre, pubDate)

    def extract_coverart(self):
        audio = File(self.filename, easy=True)
        try:
            image = base64.b64decode(str(audio['metadata_block_picture']))
            image = Picture(image)
        except:
            return None
        else:
            return image.data

    def insert_coverart(self, image=None, mimetype=None):
        if image is not None and mimetype is not None:
            audio = File(self.filename, easy=True)
            p = self.get_cover_picture(image, mimetype)

            # VorbisComment METADATA_BLOCK_PICTURE tag
            # do the dance to encode into base64, then decode into ascii
            b64encoded = base64.b64encode(p.write())
            audio['METADATA_BLOCK_PICTURE'] = b64encoded.decode("ascii")
            audio.save()


class Mp4File(AudioFile):
    def __init__(self, filename, album, title, subtitle, genre, pubDate):
        super(Mp4File, self).__init__(filename, album, title, subtitle, genre, pubDate)

    def extract_coverart(self):
        # TODO: implement mp4file extract_coverart
        return None

    def insert_coverart(self, image=None, mimetype=None):
        audio = File(self.filename)

        if image is not None and mimetype is not None:
            if mimetype.endswith('png'):
                cover_format = MP4Cover.FORMAT_PNG
            else:
                cover_format = MP4Cover.FORMAT_JPEG

            audio.tags['covr'] = [MP4Cover(image, cover_format)]
            audio.save()


class Mp3File(AudioFile):
    def __init__(self, filename, album, title, subtitle, genre, pubDate):
        super(Mp3File, self).__init__(filename, album, title, subtitle, genre, pubDate)

    def extract_coverart(self):
        tags = ID3(self.filename)
        try:
            p = tags.get("APIC:").data
        except:
            return None
        else:
            return p

    def insert_coverart(self, image=None, mimetype=None):
        audio = MP3(self.filename, ID3=ID3)

        if image is not None and mimetype is not None:
            logger.info("writing mp3 coverart")
            if audio.tags is None:
                audio.add_tags()

            audio.tags.add(
                APIC(
                    encoding=3,  # 3 is for utf-8
                    mime=mimetype,
                    type=3,
                    desc='Cover',
                    data=image
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
        self.art_filetypes = [
            "JPEG",
            "PNG",
        ]

    def on_episode_downloaded(self, episode):
        # Ensure we're within the bounds of the list
        if self.container.config.episode_coverart_filetype > (len(self.art_filetypes) - 1):
            self.container.config.episode_coverart_filetype = 0

        config_filetype = self.art_filetypes[self.container.config.episode_coverart_filetype].upper()

        info = self.read_episode_info(episode)
        if info['filename'] is None:
            return

        extracted_image = self.get_embeddedart(info, episode)
        channel_image_filename = self.get_channelart(episode.channel)
        try:
            with open(channel_image_filename, 'rb') as f:
                channel_image = f.read()
        except:
            logger.error("problems reading channel image!")
            channel_image = None

        embed_img = None
        mimetype = None
        if self.container.config.embed_coverart:
            if (self.container.config.prefer_channel_coverart or extracted_image is None) and\
                    channel_image is not None:
                logger.info("using channel image")
                embed_img = channel_image
            elif extracted_image is not None:
                logger.info("using episode image")
                embed_img = extracted_image

            if self.container.config.normalize_coverart:
                # normalize artwork regardless of source
                embed_img = self.normalize_image(embed_img, config_filetype)

            # find imagetype and mimetype regardless of source or normalization status
            if embed_img is not None:
                with Image.open(BytesIO(embed_img)) as img:
                    image_filetype = img.format.upper()

                mimetype = mimetypes.guess_type('x.' + image_filetype.lower(), strict=False)[0]
                logger.info("image mimetype %s", mimetype)

        self.write_info2file(info, episode, embed_img, mimetype)

    def get_audio(self, info, episode):
        audio = None
        audioClass = None

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
                info['pubDate'])
        return audio

    # extract coverart from episode, if exists
    def get_embeddedart(self, info, episode):
        audio = self.get_audio(info, episode)
        return audio.extract_coverart()

    # takes a raw bytes obj, returns a raw bytes obj
    def normalize_image(self, bytesimg, filetype):
        size = int(self.container.config.episode_coverart_size)
        with Image.open(BytesIO(bytesimg)) as img:
            if img.height > size:
                out = img.resize((size, size))
            else:
                out = img.copy()

        bytesimg = BytesIO()
        out.save(bytesimg, format=filetype, progressive=False)
        bytesimg = bytesimg.getvalue()
        return bytesimg

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

    def write_info2file(self, info, episode, episode_art, art_mimetype):
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

            audio.insert_coverart(episode_art, art_mimetype)

        logger.info('tagging %s/%s completed', episode.channel.title, episode.title)

    def get_channelart(self, podcast):
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
            self.container.vbox_coverart.set_sensitive(True)

            if self.container.config.modify_tags:
                self.container.hbox_genre_tag.set_sensitive(self.container.config.write_genre)
                self.container.strip_album_from_title.set_sensitive(self.container.config.write_title)
            else:
                self.container.hbox_genre_tag.set_sensitive(False)
                self.container.strip_album_from_title.set_sensitive(False)

            if self.container.config.embed_coverart:
                self.container.prefer_channel_coverart.set_sensitive(True)
                self.container.normalize_coverart.set_sensitive(True)
                self.container.note1.set_sensitive(True)
                if self.container.config.normalize_coverart:
                    self.container.hbox_convert_size.set_sensitive(True)
                    self.container.hbox_art_name.set_sensitive(True)
                else:
                    self.container.hbox_convert_size.set_sensitive(False)
                    self.container.hbox_art_name.set_sensitive(False)
            else:
                self.container.prefer_channel_coverart.set_sensitive(False)
                self.container.normalize_coverart.set_sensitive(False)
                self.container.note1.set_sensitive(False)
                self.container.hbox_convert_size.set_sensitive(False)
                self.container.hbox_art_name.set_sensitive(False)

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
            self.container.hbox_genre_tag.set_sensitive(False)
            self.container.vbox_coverart.set_sensitive(False)

    def toggle_always_remove_tags(self, widget):
        self.container.config.always_remove_tags = widget.get_active()
        self.toggle_sensitivity_of_widgets()

    def toggle_embed_coverart(self, widget):
        self.container.config.embed_coverart = widget.get_active()
        self.toggle_sensitivity_of_widgets()

    def toggle_prefer_channel_coverart(self, widget):
        self.container.config.prefer_channel_coverart = widget.get_active()

    def toggle_normalize_coverart(self, widget):
        self.container.config.normalize_coverart = widget.get_active()
        self.toggle_sensitivity_of_widgets()

    def on_episode_coverart_size_changed(self, widget):
        self.container.config.episode_coverart_size = widget.get_value_as_int()

    def on_episode_coverart_filetype_changed(self, widget):
        self.container.config.episode_coverart_filetype = widget.get_active()

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

    def show_preferences(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        title = Gtk.Label(use_markup=True, label=_('<b><big>Tagging Extension</big></b>'))
        title.set_halign(Gtk.Align.CENTER)
        box.add(title)

        whatisthis = Gtk.Label(use_markup=True, wrap=True, label=_(
            'This extension writes tags on MP3/MP4/OGG episodes after download.'
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

        self.container.vbox_coverart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        self.container.embed_coverart = Gtk.CheckButton(_('Embed Coverart'))
        self.container.embed_coverart.set_active(self.container.config.embed_coverart)
        self.container.embed_coverart.connect('toggled', self.toggle_embed_coverart)
        self.container.vbox_coverart.pack_start(self.container.embed_coverart, False, False, 0)

        self.container.prefer_channel_coverart = Gtk.CheckButton(_('Prefer channel coverart'))
        self.container.prefer_channel_coverart.set_active(self.container.config.prefer_channel_coverart)
        self.container.prefer_channel_coverart.connect('toggled', self.toggle_prefer_channel_coverart)
        self.container.vbox_coverart.pack_start(self.container.prefer_channel_coverart, False, False, 0)

        self.container.normalize_coverart = Gtk.CheckButton(_('Process art: convert, resize, and make baseline'))
        self.container.normalize_coverart.set_active(self.container.config.normalize_coverart)
        self.container.normalize_coverart.connect('toggled', self.toggle_normalize_coverart)
        self.container.vbox_coverart.pack_start(self.container.normalize_coverart, False, False, 0)

        self.container.note1 = Gtk.Label(use_markup=True, wrap=True, label=_(
            'Enable conversion and resizing of art.\n\n'
            ' If enabled, convert art to desired format (default JPEG) and size (default 500px x 500px),\n'
            ' and if format is JPEG, write as Baseline (rather than Progressive) format.\n'
            ' If disabled, embed art as-is.'))
        self.container.note1.set_property('xalign', 0.0)
        self.container.vbox_coverart.add(self.container.note1)

        self.container.episode_coverart_size = Gtk.SpinButton()
        self.container.episode_coverart_size.set_numeric(True)
        self.container.episode_coverart_size.set_range(100, 2000)
        self.container.episode_coverart_size.set_digits(0)
        self.container.episode_coverart_size.set_increments(50, 100)
        self.container.episode_coverart_size.set_snap_to_ticks(True)
        self.container.episode_coverart_size.set_value(float(self.container.config.episode_coverart_size))
        self.container.episode_coverart_size.set_halign(Gtk.Align.END)
        self.container.episode_coverart_size.set_size_request(200, -1)
        self.container.episode_coverart_size.connect("value-changed", self.on_episode_coverart_size_changed)
        self.container.episode_coverart_size_label = Gtk.Label(_('Image size (px):'))
        self.container.hbox_convert_size = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.container.hbox_convert_size.pack_start(self.container.episode_coverart_size_label, False, False, 0)
        self.container.hbox_convert_size.pack_start(self.container.episode_coverart_size, True, True, 0)
        self.container.vbox_coverart.pack_start(self.container.hbox_convert_size, False, False, 0)

        self.container.episode_coverart_filetype = Gtk.ComboBoxText()
        for i in range(len(self.art_filetypes)):
            self.container.episode_coverart_filetype.append(self.art_filetypes[i], self.art_filetypes[i])
        self.container.episode_coverart_filetype.set_active(self.container.config.episode_coverart_filetype)
        self.container.episode_coverart_filetype.connect("changed", self.on_episode_coverart_filetype_changed)
        self.container.episode_coverart_filetype.set_halign(Gtk.Align.END)
        self.container.episode_coverart_filetype.set_size_request(200, -1)
        self.container.episode_coverart_filetype_label = Gtk.Label(_('Image type:'))
        self.container.hbox_art_name = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.container.hbox_art_name.pack_start(self.container.episode_coverart_filetype_label, False, False, 0)
        self.container.hbox_art_name.pack_start(self.container.episode_coverart_filetype, True, True, 0)
        self.container.vbox_coverart.pack_start(self.container.hbox_art_name, False, False, 0)

        box.pack_start(self.container.vbox_coverart, False, False, 0)

        self.toggle_sensitivity_of_widgets()

        box.show_all()
        return box

    def on_preferences(self):
        return [(_('Tagging'), self.show_preferences)]
