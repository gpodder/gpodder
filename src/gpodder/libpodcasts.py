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


#
#  libpodcasts.py -- data classes for gpodder
#  thomas perl <thp@perli.net>   20051029
#
#  Contains code based on:
#            liblocdbwriter.py (2006-01-09)
#            liblocdbreader.py (2006-01-10)
#

import gtk
import gobject
import pango

import gpodder
from gpodder import util
from gpodder import opml
from gpodder import cache
from gpodder import services
from gpodder import draw
from gpodder import libtagupdate
from gpodder import dumbshelve

from gpodder.liblogger import log
from gpodder.libgpodder import gl
from gpodder.dbsqlite import db

import os.path
import os
import glob
import shutil
import sys
import urllib
import urlparse
import time
import datetime
import rfc822
import md5
import xml.dom.minidom
import feedparser

from xml.sax import saxutils


if gpodder.interface == gpodder.MAEMO:
    ICON_AUDIO_FILE = 'gnome-mime-audio-mp3'
    ICON_VIDEO_FILE = 'gnome-mime-video-mp4'
    ICON_BITTORRENT = 'qgn_toolb_browser_web'
    ICON_DOWNLOADING = 'qgn_toolb_messagin_moveto'
    ICON_DELETED = 'qgn_toolb_gene_deletebutton'
    ICON_NEW = 'qgn_list_gene_favor'
else:
    ICON_AUDIO_FILE = 'audio-x-generic'
    ICON_VIDEO_FILE = 'video-x-generic'
    ICON_BITTORRENT = 'applications-internet'
    ICON_DOWNLOADING = gtk.STOCK_GO_DOWN
    ICON_DELETED = gtk.STOCK_DELETE
    ICON_NEW = gtk.STOCK_ABOUT



class podcastChannel(object):
    """holds data for a complete channel"""
    SETTINGS = ('sync_to_devices', 'device_playlist_name','override_title','username','password')
    icon_cache = {}

    fc = cache.Cache()

    @classmethod
    def load(cls, url, create=True):
        if isinstance(url, unicode):
            url = url.encode('utf-8')

        tmp = db.load_channels(factory=lambda d: cls.create_from_dict(d), url=url)
        if len(tmp):
            return tmp[0]
        elif create:
            tmp = podcastChannel(url)
            if not tmp.update():
                return None
            tmp.save()
            db.force_last_new(tmp)
            return tmp

    @staticmethod
    def create_from_dict(d):
        c = podcastChannel()
        for key in d:
            if hasattr(c, key):
                setattr(c, key, d[key])
        return c

    def update(self):
        (updated, c) = self.fc.fetch(self.url, self)

        if c is None:
            return False

        if self.url != c.url:
            log('Updating channel URL from %s to %s', self.url, c.url, sender=self)
            self.url = c.url

        # update the cover if it's not there
        self.update_cover()

        # If we have an old instance of this channel, and
        # feedcache says the feed hasn't changed, return old
        if not updated:
            log('Channel %s is up to date', self.url)
            return True

        # Save etag and last-modified for later reuse
        if c.headers.get('etag'):
            self.etag = c.headers.get('etag')
        if c.headers.get('last-modified'):
            self.last_modified = c.headers.get('last-modified')

        self.parse_error = c.get('bozo_exception', None)

        if hasattr(c.feed, 'title'):
            self.title = c.feed.title
        else:
            self.title = self.url
        if hasattr( c.feed, 'link'):
            self.link = c.feed.link
        if hasattr( c.feed, 'subtitle'):
            self.description = util.remove_html_tags(c.feed.subtitle)

        if hasattr(c.feed, 'updated_parsed') and c.feed.updated_parsed is not None:
            self.pubDate = rfc822.mktime_tz(c.feed.updated_parsed+(0,))
        else:
            self.pubDate = time.time()
        if hasattr( c.feed, 'image'):
            if hasattr(c.feed.image, 'href') and c.feed.image.href:
                old = self.image
                self.image = c.feed.image.href
                if old != self.image:
                    self.update_cover(force=True)

        # Marked as bulk because we commit after importing episodes.
        db.save_channel(self, bulk=True)

        # We can limit the maximum number of entries that gPodder will parse
        # via the "max_episodes_per_feed" configuration option.
        if len(c.entries) > gl.config.max_episodes_per_feed:
            log('Limiting number of episodes for %s to %d', self.title, gl.config.max_episodes_per_feed)
        for entry in c.entries[:min(gl.config.max_episodes_per_feed, len(c.entries))]:
            episode = None

            try:
                episode = podcastItem.from_feedparser_entry(entry, self)
            except Exception, e:
                log('Cannot instantiate episode "%s": %s. Skipping.', entry.get('id', '(no id available)'), e, sender=self, traceback=True)

            if episode:
                episode.save(bulk=True)

        return True

    def update_cover(self, force=False):
        if self.cover_file is None or not os.path.exists(self.cover_file) or force:
            if self.image is not None:
                services.cover_downloader.request_cover(self)

    def delete(self):
        db.delete_channel(self)

    def save(self):
        db.save_channel(self)

    def stat(self, state=None, is_played=None, is_locked=None):
        return db.get_channel_stat(self.url, state=state, is_played=is_played, is_locked=is_locked)

    def __init__( self, url = "", title = "", link = "", description = ""):
        self.id = None
        self.url = url
        self.title = title
        self.link = link
        self.description = util.remove_html_tags( description)
        self.image = None
        self.pubDate = 0
        self.parse_error = None
        self.newest_pubdate_cached = None
        self.update_flag = False # channel is updating or to be updated
        self.iter = None

        # should this channel be synced to devices? (ex: iPod)
        self.sync_to_devices = True
        # to which playlist should be synced
        self.device_playlist_name = 'gPodder'
        # if set, this overrides the channel-provided title
        self.override_title = ''
        self.username = ''
        self.password = ''

        self.last_modified = None
        self.etag = None

        self.save_dir_size = 0
        self.__save_dir_size_set = False

    def request_save_dir_size(self):
        if not self.__save_dir_size_set:
            self.update_save_dir_size()
        self.__save_dir_size_set = True

    def update_save_dir_size(self):
        self.save_dir_size = util.calculate_size(self.save_dir)
        
    def get_filename( self):
        """Return the MD5 sum of the channel URL"""
        return md5.new( self.url).hexdigest()

    filename = property(fget=get_filename)

    def get_title( self):
        if self.override_title:
            return self.override_title
        elif not self.__title.strip():
            return self.url
        else:
            return self.__title

    def set_title( self, value):
        self.__title = value.strip()

    title = property(fget=get_title,
                     fset=set_title)

    def set_custom_title( self, custom_title):
        custom_title = custom_title.strip()

        if custom_title != self.__title:
            self.override_title = custom_title
        else:
            self.override_title = ''

    def get_downloaded_episodes(self):
        return db.load_episodes(self, factory=lambda c: podcastItem.create_from_dict(c, self), state=db.STATE_DOWNLOADED)
    
    def save_settings(self):
        db.save_channel(self)
    
    def get_new_episodes( self):
        return [episode for episode in db.load_episodes(self, factory=lambda x: podcastItem.create_from_dict(x, self)) if episode.state == db.STATE_NORMAL and not episode.is_played]

    def update_m3u_playlist(self):
        if gl.config.create_m3u_playlists:
            downloaded_episodes = self.get_downloaded_episodes()
            fn = util.sanitize_filename(self.title)
            if len(fn) == 0:
                fn = os.path.basename(self.save_dir)
            m3u_filename = os.path.join(gl.downloaddir, fn+'.m3u')
            log('Writing playlist to %s', m3u_filename, sender=self)
            f = open(m3u_filename, 'w')
            f.write('#EXTM3U\n')

            for episode in downloaded_episodes:
                filename = episode.local_filename()
                if os.path.dirname(filename).startswith(os.path.dirname(m3u_filename)):
                    filename = filename[len(os.path.dirname(m3u_filename)+os.sep):]
                f.write('#EXTINF:0,'+self.title+' - '+episode.title+' ('+episode.cute_pubdate()+')\n')
                f.write(filename+'\n')
            f.close()

    def addDownloadedItem(self, item):
        log('addDownloadedItem(%s)', item.url)

        if not item.was_downloaded():
            item.mark(is_played=False, state=db.STATE_DOWNLOADED)

            # Update metadata on file (if possible and wanted)
            if gl.config.update_tags and libtagupdate.tagging_supported():
                filename = item.local_filename()
                try:
                    libtagupdate.update_metadata_on_file(filename, title=item.title, artist=self.title, genre='Podcast')
                except Exception, e:
                    log('Error while calling update_metadata_on_file(): %s', e)

            self.update_m3u_playlist()
            
            if item.file_type() == 'torrent':
                torrent_filename = item.local_filename()
                destination_filename = util.torrent_filename( torrent_filename)
                gl.invoke_torrent(item.url, torrent_filename, destination_filename)

    def get_all_episodes(self):
        return db.load_episodes(self, factory = lambda d: podcastItem.create_from_dict(d, self), limit=gl.config.max_episodes_per_feed)

    # not used anymore
    def update_model( self):
        self.update_save_dir_size()
        model = self.tree_model

        iter = model.get_iter_first()
        while iter is not None:
            self.iter_set_downloading_columns(model, iter)
            iter = model.iter_next( iter)

    @property
    def tree_model( self):
        log('Returning TreeModel for %s', self.url, sender = self)
        return self.items_liststore()

    def iter_set_downloading_columns( self, model, iter, episode=None):
        global ICON_AUDIO_FILE, ICON_VIDEO_FILE, ICON_BITTORRENT
        global ICON_DOWNLOADING, ICON_DELETED, ICON_NEW
        
        if episode is None:
            url = model.get_value( iter, 0)
            episode = db.load_episode(url, factory=lambda x: podcastItem.create_from_dict(x, self))
        else:
            url = episode.url

        if gl.config.episode_list_descriptions:
            icon_size = 32
        else:
            icon_size = 16

        if services.download_status_manager.is_download_in_progress(url):
            status_icon = util.get_tree_icon(ICON_DOWNLOADING, icon_cache=self.icon_cache, icon_size=icon_size)
        else:
            if episode.state == db.STATE_NORMAL:
                if episode.is_played:
                    status_icon = None
                else:
                    status_icon = util.get_tree_icon(ICON_NEW, icon_cache=self.icon_cache, icon_size=icon_size)
            elif episode.was_downloaded(and_exists=True):
                missing = not episode.file_exists()

                if missing:
                    log('Episode missing: %s (before drawing an icon)', episode.url, sender=self)

                file_type = util.file_type_by_extension( model.get_value( iter, 9))
                if file_type == 'audio':
                    status_icon = util.get_tree_icon(ICON_AUDIO_FILE, not episode.is_played, episode.is_locked, not episode.file_exists(), self.icon_cache, icon_size)
                elif file_type == 'video':
                    status_icon = util.get_tree_icon(ICON_VIDEO_FILE, not episode.is_played, episode.is_locked, not episode.file_exists(), self.icon_cache, icon_size)
                elif file_type == 'torrent':
                    status_icon = util.get_tree_icon(ICON_BITTORRENT, not episode.is_played, episode.is_locked, not episode.file_exists(), self.icon_cache, icon_size)
                else:
                    status_icon = util.get_tree_icon('unknown', not episode.is_played, episode.is_locked, not episode.file_exists(), self.icon_cache, icon_size)
            elif episode.state == db.STATE_DELETED or episode.state == db.STATE_DOWNLOADED:
                status_icon = util.get_tree_icon(ICON_DELETED, icon_cache=self.icon_cache, icon_size=icon_size)
            else:
                log('Warning: Cannot determine status icon.', sender=self)
                status_icon = None

        model.set( iter, 4, status_icon)

    def items_liststore( self):
        """
        Return a gtk.ListStore containing episodes for this channel
        """
        new_model = gtk.ListStore( gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, 
            gobject.TYPE_BOOLEAN, gtk.gdk.Pixbuf, gobject.TYPE_STRING, gobject.TYPE_STRING, 
            gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING )

        for item in self.get_all_episodes():
            description = item.title_and_description

            if item.length:
                filelength = gl.format_filesize(item.length, 1)
            else:
                filelength = None

            new_iter = new_model.append((item.url, item.title, filelength, 
                True, None, item.cute_pubdate(), description, item.description, 
                item.local_filename(), item.extension()))
            self.iter_set_downloading_columns( new_model, new_iter, episode=item)
        
        self.update_save_dir_size()
        return new_model
    
    def find_episode( self, url):
        return db.load_episode(url, factory=lambda x: podcastItem.create_from_dict(x, self))

    def get_save_dir(self):
        save_dir = os.path.join(gl.downloaddir, self.filename, '')

        # Create save_dir if it does not yet exist
        if not util.make_directory( save_dir):
            log( 'Could not create save_dir: %s', save_dir, sender = self)

        return save_dir
    
    save_dir = property(fget=get_save_dir)

    def remove_downloaded( self):
        shutil.rmtree( self.save_dir, True)
    
    def get_index_file(self):
        # gets index xml filename for downloaded channels list
        return os.path.join( self.save_dir, 'index.xml')
    
    index_file = property(fget=get_index_file)
    
    def get_cover_file( self):
        # gets cover filename for cover download cache
        return os.path.join( self.save_dir, 'cover')

    cover_file = property(fget=get_cover_file)

    def delete_episode_by_url(self, url):
        episode = db.load_episode(url, lambda c: podcastItem.create_from_dict(c, self))

        if episode is not None:
            util.delete_file(episode.local_filename())
            episode.set_state(db.STATE_DELETED)

        self.update_m3u_playlist()


class podcastItem(object):
    """holds data for one object in a channel"""

    @staticmethod
    def load(url, channel):
        e = podcastItem(channel)
        d = db.load_episode(url)
        if d is not None:
            for k, v in d.iteritems():
                if hasattr(e, k):
                    setattr(e, k, v)
        return e

    @staticmethod
    def from_feedparser_entry( entry, channel):
        episode = podcastItem( channel)

        episode.title = entry.get( 'title', util.get_first_line( util.remove_html_tags( entry.get( 'summary', ''))))
        episode.link = entry.get( 'link', '')
        episode.description = util.remove_html_tags( entry.get( 'summary', entry.get( 'link', entry.get( 'title', ''))))
        episode.guid = entry.get( 'id', '')
        if entry.get( 'updated_parsed', None):
            episode.pubDate = rfc822.mktime_tz(entry.updated_parsed+(0,))

        if episode.title == '':
            log( 'Warning: Episode has no title, adding anyways.. (Feed Is Buggy!)', sender = episode)

        enclosure = None
        if hasattr(entry, 'enclosures') and len(entry.enclosures) > 0:
            enclosure = entry.enclosures[0]
            if len(entry.enclosures) > 1:
                for e in entry.enclosures:
                    if hasattr( e, 'href') and hasattr( e, 'length') and hasattr( e, 'type') and (e.type.startswith('audio/') or e.type.startswith('video/')):
                        if util.normalize_feed_url(e.href) is not None:
                            log( 'Selected enclosure: %s', e.href, sender = episode)
                            enclosure = e
                            break
            episode.url = util.normalize_feed_url( enclosure.get( 'href', ''))
        elif hasattr(entry, 'link'):
            (filename, extension) = util.filename_from_url(entry.link)
            if extension == '' and hasattr( entry, 'type'):
                extension = util.extension_from_mimetype(e.type)
            file_type = util.file_type_by_extension(extension)
            if file_type is not None:
                log('Adding episode with link to file type "%s".', file_type, sender=episode)
                episode.url = entry.link

        if not episode.url:
            # This item in the feed has no downloadable enclosure
            return None

        if not episode.pubDate:
            metainfo = util.get_episode_info_from_url(episode.url)
            if 'pubdate' in metainfo:
                try:
                    episode.pubDate = int(float(metainfo['pubdate']))
                except:
                    log('Cannot convert pubDate "%s" in from_feedparser_entry.', str(metainfo['pubdate']), traceback=True)

        if hasattr( enclosure, 'length'):
            try:
                episode.length = int(enclosure.length)
            except:
                episode.length = -1

        if hasattr( enclosure, 'type'):
            episode.mimetype = enclosure.type

        if episode.title == '':
            ( filename, extension ) = os.path.splitext( os.path.basename( episode.url))
            episode.title = filename

        return episode


    def __init__( self, channel):
        # Used by Storage for faster saving
        self.id = None
        self.url = ''
        self.title = ''
        self.length = 0
        self.mimetype = 'application/octet-stream'
        self.guid = ''
        self.description = ''
        self.link = ''
        self.channel = channel
        self.pubDate = None

        self.state = db.STATE_NORMAL
        self.is_played = False
        self.is_locked = False

    def save(self, bulk=False):
        if self.state != db.STATE_DOWNLOADED and self.file_exists():
            self.state = db.STATE_DOWNLOADED
        db.save_episode(self, bulk=bulk)

    def set_state(self, state):
        self.state = state
        db.mark_episode(self.url, state=self.state, is_played=self.is_played, is_locked=self.is_locked)

    def mark(self, state=None, is_played=None, is_locked=None):
        if state is not None:
            self.state = state
        if is_played is not None:
            self.is_played = is_played
        if is_locked is not None:
            self.is_locked = is_locked
        db.mark_episode(self.url, state=state, is_played=is_played, is_locked=is_locked)

    @staticmethod
    def create_from_dict(d, channel):
        e = podcastItem(channel)
        for key in d:
            if hasattr(e, key):
                setattr(e, key, d[key])
        return e

    @property
    def title_and_description(self):
        """
        Returns Pango markup for displaying in a TreeView, and
        disables the description when the config variable
        "episode_list_descriptions" is not set.
        """
        if gl.config.episode_list_descriptions:
            return '%s\n<small>%s</small>' % (saxutils.escape(self.title), saxutils.escape(self.one_line_description()))
        else:
            return saxutils.escape(self.title)

    def age_in_days(self):
        return util.file_age_in_days(self.local_filename())

    def is_old(self):
        return self.age_in_days() > gl.config.episode_old_age
    
    def get_age_string(self):
        return util.file_age_to_string(self.age_in_days())

    age_prop = property(fget=get_age_string)

    def one_line_description( self):
        lines = self.description.strip().splitlines()
        if not lines or lines[0] == '':
            return _('No description available')
        else:
            return ' '.join((l.strip() for l in lines if l.strip() != ''))

    def delete_from_disk(self):
        try:
            self.channel.delete_episode_by_url(self.url)
        except:
            log('Cannot delete episode from disk: %s', self.title, traceback=True, sender=self)

    def local_filename( self):
        ext = self.extension()

        # For compatibility with already-downloaded episodes,
        # we accept md5 filenames if they are downloaded now.
        md5_filename = os.path.join(self.channel.save_dir, md5.new(self.url).hexdigest()+ext)
        if os.path.exists(md5_filename) or not gl.config.experimental_file_naming:
            return md5_filename

        # If the md5 filename does not exist, 
        ( episode, e ) = util.filename_from_url(self.url)
        episode = util.sanitize_filename(episode) + ext

        # If the episode filename looks suspicious,
        # we still return the md5 filename to be on
        # the safe side of the fence ;)
        if len(episode) == 0 or episode.startswith('redirect.'):
            return md5_filename
        filename = os.path.join(self.channel.save_dir, episode)
        return filename

    def extension( self):
         ( filename, ext ) = util.filename_from_url(self.url)
         # if we can't detect the extension from the url fallback on the mimetype
         if ext == '' or util.file_type_by_extension(ext) is None:
             ext = util.extension_from_mimetype(self.mimetype)
             #log('Getting extension from mimetype for: %s  (mimetype: %s)' % (self.title, ext), sender=self)
         return ext

    def mark_new(self):
        self.state = db.STATE_NORMAL
        self.is_played = False
        db.mark_episode(self.url, state=self.state, is_played=self.is_played)

    def mark_old(self):
        self.is_played = True
        db.mark_episode(self.url, is_played=True)

    def file_exists(self):
        return os.path.exists(self.local_filename())

    def was_downloaded(self, and_exists=False):
        if self.state != db.STATE_DOWNLOADED:
            return False
        if and_exists and not self.file_exists():
            return False
        return True

    def sync_filename( self):
        if gl.config.custom_sync_name_enabled:
            return util.object_string_formatter(gl.config.custom_sync_name, episode=self, channel=self.channel)
        else:
            return self.title

    def file_type( self):
        return util.file_type_by_extension( self.extension() )

    @property
    def basename( self):
        return os.path.splitext( os.path.basename( self.url))[0]
    
    @property
    def published( self):
        try:
            return datetime.datetime.fromtimestamp(self.pubDate).strftime('%Y%m%d')
        except:
            log( 'Cannot format pubDate for "%s".', self.title, sender = self)
            return '00000000'
    
    def cute_pubdate(self):
        result = util.format_date(self.pubDate)
        if result is None:
            return '(%s)' % _('unknown')
        else:
            return result
    
    pubdate_prop = property(fget=cute_pubdate)

    def calculate_filesize( self):
        try:
            self.length = os.path.getsize(self.local_filename())
        except:
            log( 'Could not get filesize for %s.', self.url)

    def get_filesize_string( self):
        return gl.format_filesize( self.length)

    filesize_prop = property(fget=get_filesize_string)

    def get_channel_title( self):
        return self.channel.title

    channel_prop = property(fget=get_channel_title)

    def get_played_string( self):
        if not self.is_played:
            return _('Unplayed')
        
        return ''

    played_prop = property(fget=get_played_string)
    


def update_channel_model_by_iter( model, iter, channel, color_dict,
    cover_cache=None, max_width=0, max_height=0 ):

    count_downloaded = channel.stat(state=db.STATE_DOWNLOADED)
    count_new = channel.stat(state=db.STATE_NORMAL, is_played=False)
    count_unplayed = channel.stat(state=db.STATE_DOWNLOADED, is_played=False)

    channel.iter = iter
    model.set(iter, 0, channel.url)
    model.set(iter, 1, channel.title)

    title_markup = saxutils.escape(channel.title)
    description_markup = saxutils.escape(util.get_first_line(channel.description) or _('No description available'))
    d = []
    if count_new:
        d.append('<span weight="bold">')
    d.append(title_markup)
    if count_new:
        d.append('</span>')

    description = ''.join(d+['\n', '<small>', description_markup, '</small>'])
    model.set(iter, 2, description)

    if channel.parse_error is not None:
        model.set(iter, 6, channel.parse_error)
        color = color_dict['parse_error']
    else:
        color = color_dict['default']

    if channel.update_flag:
        color = color_dict['updating']

    model.set(iter, 8, color)

    if count_unplayed > 0 or count_downloaded > 0:
        model.set(iter, 3, draw.draw_pill_pixbuf(str(count_unplayed), str(count_downloaded)))
        model.set(iter, 7, True)
    else:
        model.set(iter, 7, False)

    # Load the cover if we have it, but don't download
    # it if it's not available (to avoid blocking here)
    pixbuf = services.cover_downloader.get_cover(channel, avoid_downloading=True)
    new_pixbuf = None
    if pixbuf is not None:
        new_pixbuf = util.resize_pixbuf_keep_ratio(pixbuf, max_width, max_height, channel.url, cover_cache)
    model.set(iter, 5, new_pixbuf or pixbuf)

def channels_to_model(channels, color_dict, cover_cache=None, max_width=0, max_height=0):
    new_model = gtk.ListStore( str, str, str, gtk.gdk.Pixbuf, int,
        gtk.gdk.Pixbuf, str, bool, str )

    for channel in channels:
        update_channel_model_by_iter( new_model, new_model.append(), channel,
            color_dict, cover_cache, max_width, max_height )

    return new_model


def load_channels():
    return db.load_channels(lambda d: podcastChannel.create_from_dict(d))

def update_channels(callback_proc=None, callback_error=None, is_cancelled_cb=None):
    log('Updating channels....')

    channels = load_channels()
    count = 0

    for channel in channels:
        if is_cancelled_cb is not None and is_cancelled_cb():
            return channels
        callback_proc and callback_proc(count, len(channels))
        channel.update()
        count += 1

    return channels

def save_channels( channels):
    exporter = opml.Exporter(gl.channel_opml_file)
    return exporter.write(channels)

def can_restore_from_opml():
    try:
        if len(opml.Importer(gl.channel_opml_file).items):
            return gl.channel_opml_file
    except:
        return None



class LocalDBReader( object):
    """
    DEPRECATED - Only used for migration to SQLite
    """
    def __init__( self, url):
        self.url = url

    def get_text( self, nodelist):
        return ''.join( [ node.data for node in nodelist if node.nodeType == node.TEXT_NODE ])

    def get_text_by_first_node( self, element, name):
        return self.get_text( element.getElementsByTagName( name)[0].childNodes)
    
    def get_episode_from_element( self, channel, element):
        episode = podcastItem( channel)
        episode.title = self.get_text_by_first_node( element, 'title')
        episode.description = self.get_text_by_first_node( element, 'description')
        episode.url = self.get_text_by_first_node( element, 'url')
        episode.link = self.get_text_by_first_node( element, 'link')
        episode.guid = self.get_text_by_first_node( element, 'guid')

        if not episode.guid:
            for k in ('url', 'link'):
                if getattr(episode, k) is not None:
                    episode.guid = getattr(episode, k)
                    log('Notice: episode has no guid, using %s', episode.guid)
                    break
        try:
            episode.pubDate = float(self.get_text_by_first_node(element, 'pubDate'))
        except:
            log('Looks like you have an old pubDate in your LocalDB -> converting it')
            episode.pubDate = self.get_text_by_first_node(element, 'pubDate')
            log('FYI: pubDate value is: "%s"', episode.pubDate, sender=self)
            pubdate = feedparser._parse_date(episode.pubDate)
            if pubdate is None:
                log('Error converting the old pubDate - sorry!', sender=self)
                episode.pubDate = 0
            else:
                log('PubDate converted successfully - yay!', sender=self)
                episode.pubDate = time.mktime(pubdate)
        try:
            episode.mimetype = self.get_text_by_first_node( element, 'mimetype')
        except:
            log('No mimetype info for %s', episode.url, sender=self)
        episode.calculate_filesize()
        return episode

    def load_and_clean( self, filename):
        """
        Clean-up a LocalDB XML file that could potentially contain
        "unbound prefix" XML elements (generated by the old print-based
        LocalDB code). The code removes those lines to make the new 
        DOM parser happy.

        This should be removed in a future version.
        """
        lines = []
        for line in open(filename).read().split('\n'):
            if not line.startswith('<gpodder:info'):
                lines.append( line)

        return '\n'.join( lines)
    
    def read( self, filename):
        doc = xml.dom.minidom.parseString( self.load_and_clean( filename))
        rss = doc.getElementsByTagName('rss')[0]
        
        channel_element = rss.getElementsByTagName('channel')[0]

        channel = podcastChannel( url = self.url)
        channel.title = self.get_text_by_first_node( channel_element, 'title')
        channel.description = self.get_text_by_first_node( channel_element, 'description')
        channel.link = self.get_text_by_first_node( channel_element, 'link')

        episodes = []
        for episode_element in rss.getElementsByTagName('item'):
            episode = self.get_episode_from_element( channel, episode_element)
            episodes.append(episode)

        return episodes

