# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (C) 2005-2007 Thomas Perl <thp at perli.net>
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

from gpodder import util
from gpodder import opml
from gpodder import cache
from gpodder import services
from gpodder import draw

from liblogger import log
import libgpodder

from os.path import exists
from os.path import basename
import os.path
import os
import glob
import shutil
import sys
import urllib
import urlparse
import time
import threading

from datetime import datetime

from libtagupdate import update_metadata_on_file
from libtagupdate import tagging_supported

from threading import Event
import re

from types import ListType
from email.Utils import mktime_tz
from email.Utils import parsedate_tz

from xml.sax import saxutils

import xml.dom.minidom

import md5

import string

import shelve

global_lock = threading.RLock()

class ChannelSettings(object):
    storage = shelve.open( libgpodder.gPodderLib().channel_settings_file)

    @classmethod
    def get_settings_by_url( cls, url):
        if isinstance( url, unicode):
            url = url.encode('utf-8')
        if cls.storage.has_key( url):
            return cls.storage[url]
        else:
            return {}

    @classmethod
    def set_settings_by_url( cls, url, settings):
        if isinstance( url, unicode):
            url = url.encode('utf-8')
        log( 'Saving settings for %s', url)
        cls.storage[url] = settings
        cls.storage.sync()


class podcastChannel(ListType):
    """holds data for a complete channel"""
    SETTINGS = ('sync_to_devices', 'is_music_channel', 'device_playlist_name','override_title','username','password')
    icon_cache = {}

    storage = shelve.open( libgpodder.gPodderLib().feed_cache_file)
    fc = cache.Cache( storage)

    @classmethod
    def clear_cache(cls, urls_to_keep):
        for url in cls.storage.keys():
            if url not in urls_to_keep:
                log('(podcastChannel) Removing old feed from cache: %s', url)
                del cls.storage[url]

    @classmethod
    def get_by_url( cls, url, force_update = False, offline = False):
        if isinstance( url, unicode):
            url = url.encode('utf-8')

        c = cls.fc.fetch( url, force_update, offline)
        channel = podcastChannel( url)
        channel.load_settings()
        channel.title = c.feed.title
        if hasattr( c.feed, 'link'):
            channel.link = c.feed.link
        if hasattr( c.feed, 'subtitle'):
            channel.description = util.remove_html_tags( c.feed.subtitle)

        if hasattr( c.feed, 'updated_parsed'):
            channel.pubDate = util.updated_parsed_to_rfc2822( c.feed.updated_parsed)
        if hasattr( c.feed, 'image'):
            if c.feed.image.href:
                channel.image = c.feed.image.href

        for entry in c.entries:
            if not hasattr( entry, 'enclosures'):
                log('Skipping entry: %s', entry.get( 'id', '(no id available)'), sender = channel)
                continue

            episode = None

            try:
                episode = podcastItem.from_feedparser_entry( entry, channel)
            except:
                log( 'Cannot instantiate episode: %s. Skipping.', entry.get( 'id', '(no id available)'), sender = channel)

            if episode:
                channel.append( episode)

        channel.sort( reverse = True)
        
        cls.storage.sync()
        return channel

    @staticmethod
    def create_from_dict( d, load_items = True, force_update = False, callback_error = None, offline = False):
        if load_items:
            try:
                return podcastChannel.get_by_url( d['url'], force_update = force_update, offline= offline)
            except:
                callback_error and callback_error( _('Could not load channel feed from URL: %s') % d['url'])
                log( 'Cannot load podcastChannel from URL: %s', d['url'])

        c = podcastChannel()
        for key in ( 'url', 'title', 'description' ):
            if key in d:
                setattr( c, key, d[key])
        c.load_settings()

        return c

    def __init__( self, url = "", title = "", link = "", description = ""):
        self.url = url
        self.title = title
        self.link = link
        self.description = util.remove_html_tags( description)
        self.image = None
        self.pubDate = ''

        # should this channel be synced to devices? (ex: iPod)
        self.sync_to_devices = True
        # if this is set to true, device syncing (ex: iPod) should treat this as music, not as podcast)
        self.is_music_channel = False
        # to which playlist should be synced when "is_music_channel" is true?
        self.device_playlist_name = 'gPodder'
        # if set, this overrides the channel-provided title
        self.override_title = ''
        self.username = ''
        self.password = ''

        self.update_save_dir_size()

        self.__tree_model = None

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
    
    def load_downloaded_episodes( self):
        try:
            return LocalDBReader( self.url).read( self.index_file)
        except:
            return podcastChannel( self.url, self.title, self.link, self.description)

    def save_downloaded_episodes( self, channel):
        try:
            log( 'Setting localdb channel data => %s', self.index_file, sender = self)
            LocalDBWriter( self.index_file).write( channel)
        except:
            log( 'Error writing to localdb: %s', self.index_file, sender = self, traceback = True)
    
    def load_settings( self):
        settings = ChannelSettings.get_settings_by_url( self.url)

        for key in self.SETTINGS:
            if settings.has_key( key):
                setattr( self, key, settings[key])

    def save_settings( self):
        settings = {}
        for key in self.SETTINGS:
            settings[key] = getattr( self, key)

        ChannelSettings.set_settings_by_url( self.url, settings)

    def newest_pubdate_downloaded( self):
        gl = libgpodder.gPodderLib()

        # Try DownloadHistory's entries first
        for episode in self:
            if gl.history_is_downloaded( episode.url):
                return episode.pubDate

        # If nothing found, do pubDate comparison
        pubdate = None
        for episode in self.load_downloaded_episodes():
            pubdate = episode.newer_pubdate( pubdate)
        return pubdate
    
    def episode_is_new(self, episode, last_pubdate = None):
        gl = libgpodder.gPodderLib()
        if last_pubdate is None:
            last_pubdate = self.newest_pubdate_downloaded()

        # episode is older than newest downloaded
        if episode.compare_pubdate(last_pubdate) < 0:
            return False

        # episode has been downloaded before
        if episode.is_downloaded() or gl.history_is_downloaded(episode.url):
            return False

        # download is currently in progress
        if services.download_status_manager.is_download_in_progress(episode.url):
            return False

        return True
    
    def get_new_episodes( self):
        last_pubdate = self.newest_pubdate_downloaded()
        gl = libgpodder.gPodderLib()

        if not last_pubdate:
            return self[0:min(len(self),gl.config.default_new)]

        new_episodes = []
        for episode in self.get_all_episodes():
            if self.episode_is_new(episode, last_pubdate):
                new_episodes.append(episode)

        return new_episodes

    def can_sort_by_pubdate( self):
        for episode in self:
            try:
                mktime_tz(parsedate_tz( episode.pubDate))
            except:
                log('Episode %s has non-parseable pubDate. Sorting disabled.', episode.title)
                return False

        return True
    
    def addDownloadedItem( self, item):
        # no multithreaded access
        global_lock.acquire()

        downloaded_episodes = self.load_downloaded_episodes()
        already_in_list = item.url in [ episode.url for episode in downloaded_episodes ]

        # only append if not already in list
        if not already_in_list:
            downloaded_episodes.append( item)
            self.save_downloaded_episodes( downloaded_episodes)

            # Update metadata on file (if possible and wanted)
            if libgpodder.gPodderLib().config.update_tags and tagging_supported():
                filename = item.local_filename()
                try:
                    update_metadata_on_file( filename, title = item.title, artist = self.title)
                except:
                    log('Error while calling update_metadata_on_file() :(')

        libgpodder.gPodderLib().history_mark_downloaded( item.url)
        
        if item.file_type() == 'torrent':
            torrent_filename = item.local_filename()
            destination_filename = util.torrent_filename( torrent_filename)
            libgpodder.gPodderLib().invoke_torrent( item.url, torrent_filename, destination_filename)
            
        global_lock.release()
        return not already_in_list

    def get_all_episodes( self):
        episodes = []
        added_urls = []
        added_guids = []

        # go through all episodes (both new and downloaded),
        # prefer already-downloaded (in localdb)
        for item in [] + self.load_downloaded_episodes() + self:
            # skip items with the same guid (if it has a guid)
            if item.guid and item.guid in added_guids:
                continue

            # skip items with the same download url
            if item.url in added_urls:
                continue

            episodes.append( item)

            added_urls.append( item.url)
            if item.guid:
                added_guids.append( item.guid)

        episodes.sort( reverse = True)

        return episodes
    

    def get_episode_stats( self):
        (available, downloaded, newer, unplayed) = (0, 0, 0, 0)
        last_pubdate = self.newest_pubdate_downloaded()

        for episode in self.get_all_episodes():
            available += 1
            if self.episode_is_new(episode, last_pubdate):
                newer += 1
            if episode.is_downloaded():
                downloaded += 1
                if not episode.is_played():
                    unplayed += 1

        return (available, downloaded, newer, unplayed)

        
    def force_update_tree_model( self):
        self.__tree_model = None

    def update_model( self):
        new_episodes = self.get_new_episodes()
        self.update_save_dir_size()

        iter = self.tree_model.get_iter_first()
        while iter != None:
            self.iter_set_downloading_columns( self.tree_model, iter, new_episodes)
            iter = self.tree_model.iter_next( iter)

    @property
    def tree_model( self):
        if not self.__tree_model:
            log('Generating TreeModel for %s', self.url, sender = self)
            self.__tree_model = self.items_liststore()

        return self.__tree_model

    def iter_set_downloading_columns( self, model, iter, new_episodes = []):
        url = model.get_value( iter, 0)
        local_filename = model.get_value( iter, 8)
        played = not libgpodder.gPodderLib().history_is_played( url)
        locked = libgpodder.gPodderLib().history_is_locked(url)
        gl = libgpodder.gPodderLib()

        if gl.config.episode_list_descriptions:
            icon_size = 32
        else:
            icon_size = 16

        if os.path.exists( local_filename):
            file_type = util.file_type_by_extension( util.file_extension_from_url(url))
            if file_type == 'audio':
                status_icon = util.get_tree_icon('audio-x-generic', played, locked, self.icon_cache, icon_size)
            elif file_type == 'video':
                status_icon = util.get_tree_icon('video-x-generic', played, locked, self.icon_cache, icon_size)
            elif file_type == 'torrent':
                status_icon = util.get_tree_icon('applications-internet', played, locked, self.icon_cache, icon_size)
            else:
                status_icon = util.get_tree_icon('unknown', played, locked, self.icon_cache, icon_size)
            
        elif services.download_status_manager.is_download_in_progress(url):
            status_icon = util.get_tree_icon(gtk.STOCK_GO_DOWN, icon_cache=self.icon_cache, icon_size=icon_size)
        elif gl.history_is_downloaded(url):
            status_icon = util.get_tree_icon(gtk.STOCK_DELETE, icon_cache=self.icon_cache, icon_size=icon_size)
        elif url in [e.url for e in new_episodes]:
            status_icon = util.get_tree_icon(gtk.STOCK_NEW, icon_cache=self.icon_cache, icon_size=icon_size)
        else:
            status_icon = None

        model.set( iter, 4, status_icon)

    def items_liststore( self):
        """
        Return a gtk.ListStore containing episodes for this channel
        """
        new_model = gtk.ListStore( gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_BOOLEAN, gtk.gdk.Pixbuf, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        new_episodes = self.get_new_episodes()
        gl = libgpodder.gPodderLib()

        for item in self.get_all_episodes():
            if gl.config.episode_list_descriptions:
                description = '%s\n<small>%s</small>' % (saxutils.escape(item.title), saxutils.escape(item.one_line_description()))
            else:
                description = saxutils.escape(item.title)
            new_iter = new_model.append((item.url, item.title, libgpodder.gPodderLib().format_filesize(item.length, 1), True, None, item.cute_pubdate(), description, item.description, item.local_filename()))
            self.iter_set_downloading_columns( new_model, new_iter, new_episodes)
        
        self.update_save_dir_size()
        return new_model
    
    def find_episode( self, url):
        for item in self.get_all_episodes():
            if url == item.url:
                return item

        return None

    def get_save_dir(self):
        save_dir = os.path.join( libgpodder.gPodderLib().downloaddir, self.filename, '')

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

    def get_cover_pixbuf(self, size=128):
        fn = self.cover_file
        if os.path.exists(fn) and os.path.getsize(fn) > 0:
            try:
                return gtk.gdk.pixbuf_new_from_file_at_size(fn, size, size)
            except:
                pass

        return None

    def delete_episode_by_url(self, url):
        global_lock.acquire()
        downloaded_episodes = self.load_downloaded_episodes()

        for episode in self.get_all_episodes():
            if episode.url == url:
                util.delete_file( episode.local_filename())
                if episode in downloaded_episodes:
                    downloaded_episodes.remove( episode)

        self.save_downloaded_episodes( downloaded_episodes)
        global_lock.release()

class podcastItem(object):
    """holds data for one object in a channel"""

    @staticmethod
    def from_feedparser_entry( entry, channel):
        episode = podcastItem( channel)

        episode.title = entry.get( 'title', util.get_first_line( util.remove_html_tags( entry.get( 'summary', ''))))
        episode.link = entry.get( 'link', '')
        episode.description = util.remove_html_tags( entry.get( 'summary', entry.get( 'link', entry.get( 'title', ''))))
        episode.guid = entry.get( 'id', '')
        if entry.get( 'updated_parsed', None):
            episode.pubDate = util.updated_parsed_to_rfc2822( entry.updated_parsed)

        if episode.title == '':
            log( 'Warning: Episode has no title, adding anyways.. (Feed Is Buggy!)', sender = episode)

        enclosure = entry.enclosures[0]
        if len(entry.enclosures) > 1:
            for e in entry.enclosures:
                if hasattr( e, 'href') and hasattr( e, 'length') and hasattr( e, 'type') and (e.type.startswith('audio/') or e.type.startswith('video/')):
                    if util.normalize_feed_url( e.href) != None:
                        log( 'Selected enclosure: %s', e.href, sender = episode)
                        enclosure = e
                        break

        episode.url = util.normalize_feed_url( enclosure.get( 'href', ''))
        if not episode.url:
            raise ValueError( 'Episode has an invalid URL')

        if hasattr( enclosure, 'length'):
            episode.length = enclosure.length
        if hasattr( enclosure, 'type'):
            episode.mimetype = enclosure.type

        if episode.title == '':
            ( filename, extension ) = os.path.splitext( os.path.basename( episode.url))
            episode.title = filename

        return episode


    def __init__( self, channel):
        self.url = ''
        self.title = ''
        self.length = 0
        self.mimetype = 'application/octet-stream'
        self.guid = ''
        self.description = ''
        self.link = ''
        self.channel = channel
        self.pubDate = ''

    def is_played(self):
        gl = libgpodder.gPodderLib()
        return gl.history_is_played(self.url)

    def age_in_days(self):
        return util.file_age_in_days(self.local_filename())

    def is_old(self):
        gl = libgpodder.gPodderLib()
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

    def is_downloaded( self):
        return os.path.exists( self.local_filename())

    def is_locked(self):
        return libgpodder.gPodderLib().history_is_locked(self.url)

    def delete_from_disk(self):
        try:
            self.channel.delete_episode_by_url(self.url)
        except:
            log('Cannot delete episode from disk: %s', self.title, traceback=True, sender=self)

    def local_filename( self):
        extension = util.file_extension_from_url( self.url)
        return os.path.join( self.channel.save_dir, md5.new( self.url).hexdigest() + extension)

    def sync_filename( self):
        if libgpodder.gPodderLib().config.custom_sync_name_enabled:
            return util.object_string_formatter( libgpodder.gPodderLib().config.custom_sync_name, episode = self, channel = self.channel)
        else:
            return self.title

    def file_type( self):
        return util.file_type_by_extension( util.file_extension_from_url( self.url))

    @property
    def basename( self):
        return os.path.splitext( os.path.basename( self.url))[0]
    
    @property
    def published( self):
        try:
            return datetime.fromtimestamp( mktime_tz( parsedate_tz( self.pubDate))).strftime('%Y%m%d')
        except:
            log( 'Cannot format pubDate for "%s".', self.title, sender = self)
            return '00000000'
    
    def __cmp__( self, other):
        try:
            timestamp_self = int(mktime_tz( parsedate_tz( self.pubDate)))
            timestamp_other = int(mktime_tz( parsedate_tz( other.pubDate)))
        except:
            # by default, do as if this is not the same
            # this is here so that comparisons with None 
            # can be allowed (item != None -> True)
            return -1
        
        return timestamp_self - timestamp_other

    def compare_pubdate( self, pubdate):
        try:
            timestamp_self = int(mktime_tz( parsedate_tz( self.pubDate)))
        except:
            return -1

        try:
            timestamp_other = int(mktime_tz( parsedate_tz( pubdate)))
        except:
            return 1

        return timestamp_self - timestamp_other

    def newer_pubdate( self, pubdate = None):
        if self.compare_pubdate( pubdate) > 0:
            return self.pubDate
        else:
            return pubdate

    def cute_pubdate( self):
        seconds_in_a_day = 86400
        try:
            timestamp = int(mktime_tz( parsedate_tz( self.pubDate)))
        except:
            return _("(unknown)")
        diff = int((time.time()+1)/seconds_in_a_day) - int(timestamp/seconds_in_a_day)
        
        if diff == 0:
           return _("Today")
        if diff == 1:
           return _("Yesterday")
        if diff < 7:
            return str(datetime.fromtimestamp( timestamp).strftime( "%A"))
        
        return str(datetime.fromtimestamp( timestamp).strftime( "%x"))
    
    pubdate_prop = property(fget=cute_pubdate)

    def calculate_filesize( self):
        try:
            self.length = str(os.path.getsize( self.local_filename()))
        except:
            log( 'Could not get filesize for %s.', self.url)

    def get_filesize_string( self):
        gl = libgpodder.gPodderLib()
        return gl.format_filesize( self.length)

    filesize_prop = property(fget=get_filesize_string)

    def get_channel_title( self):
        return self.channel.title

    channel_prop = property(fget=get_channel_title)

    def get_played_string( self):
        if not self.is_played():
            return _('Unplayed')
        
        return ''

    played_prop = property(fget=get_played_string)
    
    def equals( self, other_item):
        if other_item == None:
            return False
        
        return self.url == other_item.url



def channels_to_model(channels):
    new_model = gtk.ListStore(str, str, str, gtk.gdk.Pixbuf, int, gtk.gdk.Pixbuf)
    
    for channel in channels:
        (count_available, count_downloaded, count_new, count_unplayed) = channel.get_episode_stats()
        
        new_iter = new_model.append()
        new_model.set(new_iter, 0, channel.url)
        new_model.set(new_iter, 1, channel.title)

        title_markup = saxutils.escape(channel.title)
        description_markup = saxutils.escape(util.get_first_line(channel.description))
        new_model.set(new_iter, 2, '%s\n<small>%s</small>' % (title_markup, description_markup))

        if count_unplayed > 0 or count_downloaded > 0:
            new_model.set(new_iter, 3, draw.draw_pill_pixbuf(str(count_unplayed), str(count_downloaded)))

        if count_new > 0:
            new_model.set( new_iter, 4, pango.WEIGHT_BOLD)
        else:
            new_model.set( new_iter, 4, pango.WEIGHT_NORMAL)

        channel_cover_found = False
        if os.path.exists( channel.cover_file) and os.path.getsize(channel.cover_file) > 0:
            try:
                new_model.set( new_iter, 5, gtk.gdk.pixbuf_new_from_file_at_size( channel.cover_file, 32, 32))
                channel_cover_found = True
            except: 
                exctype, value = sys.exc_info()[:2]
                log( 'Could not convert icon file "%s", error was "%s"', channel.cover_file, value )
                util.delete_file(channel.cover_file)

        if not channel_cover_found:
            iconsize = gtk.icon_size_from_name('channel-icon')
            if not iconsize:
                iconsize = gtk.icon_size_register('channel-icon',32,32)
            icon_theme = gtk.icon_theme_get_default()
            globe_icon_name = 'applications-internet'
            try:
                new_model.set( new_iter, 5, icon_theme.load_icon(globe_icon_name, iconsize, 0))
            except:
                log( 'Cannot load "%s" icon (using an old or incomplete icon theme?)', globe_icon_name)
                new_model.set( new_iter, 5, None)
    
    return new_model



def load_channels( load_items = True, force_update = False, callback_proc = None, callback_url = None, callback_error = None, offline = False):
    importer = opml.Importer( libgpodder.gPodderLib().channel_opml_file)
    result = []

    urls_to_keep = []
    count = 0
    for item in importer.items:
        callback_proc and callback_proc( count, len( importer.items))
        callback_url and callback_url( item['url'])
        urls_to_keep.append(item['url'])
        result.append( podcastChannel.create_from_dict( item, load_items = load_items, force_update = force_update, callback_error = callback_error, offline = offline))
        count += 1

    podcastChannel.clear_cache(urls_to_keep)
    result.sort(key=lambda x:x.title.lower())
    return result

def save_channels( channels):
    exporter = opml.Exporter( libgpodder.gPodderLib().channel_opml_file)
    return exporter.write(channels)



class LocalDBReader( object):
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
        episode.pubDate = self.get_text_by_first_node( element, 'pubDate')
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
        channel.load_settings()

        for episode_element in rss.getElementsByTagName('item'):
            episode = self.get_episode_from_element( channel, episode_element)
            channel.append( episode)

        return channel



class LocalDBWriter(object):
    def __init__( self, filename):
        self.filename = filename

    def create_node( self, doc, name, content):
        node = doc.createElement( name)
        node.appendChild( doc.createTextNode( content))
        return node

    def create_item( self, doc, episode):
        item = doc.createElement( 'item')
        item.appendChild( self.create_node( doc, 'title', episode.title))
        item.appendChild( self.create_node( doc, 'description', episode.description))
        item.appendChild( self.create_node( doc, 'url', episode.url))
        item.appendChild( self.create_node( doc, 'link', episode.link))
        item.appendChild( self.create_node( doc, 'guid', episode.guid))
        item.appendChild( self.create_node( doc, 'pubDate', episode.pubDate))
        return item

    def write( self, channel):
        doc = xml.dom.minidom.Document()

        rss = doc.createElement( 'rss')
        rss.setAttribute( 'version', '1.0')
        doc.appendChild( rss)

        channele = doc.createElement( 'channel')
        channele.appendChild( self.create_node( doc, 'title', channel.title))
        channele.appendChild( self.create_node( doc, 'description', channel.description))
        channele.appendChild( self.create_node( doc, 'link', channel.link))
        rss.appendChild( channele)

        for episode in channel:
            if episode.is_downloaded():
                rss.appendChild( self.create_item( doc, episode))

        try:
            fp = open( self.filename, 'w')
            fp.write( doc.toxml( encoding = 'utf-8'))
            fp.close()
        except:
            log( 'Could not open file for writing: %s', self.filename, sender = self)
            return False
        
        return True

