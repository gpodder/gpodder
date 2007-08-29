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
#

import gtk
import gobject
import pango

from gpodder import util
from gpodder import opml
from gpodder import cache
from gpodder import services

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

from datetime import datetime
from time import time

from liblocdbwriter import writeLocalDB
from liblocdbreader import readLocalDB

from libtagupdate import update_metadata_on_file
from libtagupdate import tagging_supported

from threading import Event
from libwget import downloadThread
import re

from types import ListType
from email.Utils import mktime_tz
from email.Utils import parsedate_tz

from xml.sax import saxutils

from xml.sax import make_parser

import md5

import string

import shelve

class ChannelSettings(object):
    storage = shelve.open( libgpodder.gPodderLib().channel_settings_file)

    @classmethod
    def get_settings_by_url( cls, url):
        if isinstance( url, unicode):
            url = url.encode('utf-8')
        log( 'Trying to get settings for %s', url)
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
    MAP_FROM = 'abcdefghijklmnopqrstuvwxyz0123456789'
    MAP_TO   = 'qazwsxedcrfvtgbyhnujmikolp9514738062'
    SETTINGS = ('sync_to_devices', 'is_music_channel', 'device_playlist_name','override_title','username','password')
    icon_cache = {}

    storage = shelve.open( libgpodder.gPodderLib().feed_cache_file)
    fc = cache.Cache( storage)

    @classmethod
    def get_by_url( cls, url, force_update = False):
        if isinstance( url, unicode):
            url = url.encode('utf-8')

        c = cls.fc.fetch( url, force_update)
        channel = podcastChannel( url)
        channel.title = c.feed.title
        if hasattr( c.feed, 'link'):
            channel.link = c.feed.link
        if hasattr( c.feed, 'subtitle'):
            channel.description = util.remove_html_tags( c.feed.subtitle)

        if hasattr( c.feed, 'updated'):
            channel.pubDate = c.feed.updated
        if hasattr( c.feed, 'image'):
            if c.feed.image.href:
                channel.image = c.feed.image.href

        for entry in c.entries:
            if not len(entry.enclosures):
                log('Skipping entry: %s', entry)
                continue

            episode = None

            try:
                episode = podcastItem.from_feedparser_entry( entry, channel)
            except:
                log( 'Cannot instantiate episode for %s. Skipping.', entry.enclosures[0].href, sender = channel)

            if episode:
                channel.append( episode)

        channel.sort( reverse = True)
        
        cls.storage.sync()
        return channel

    @staticmethod
    def create_from_dict( d, load_items = True, force_update = False, callback_error = None):
        if load_items:
            try:
                return podcastChannel.get_by_url( d['url'], force_update = force_update)
            except:
                callback_error and callback_error( _('Could not load channel feed from URL: %s') % d['url'])
                log( 'Cannot load podcastChannel from URL: %s', d['url'])

        c = podcastChannel()
        for key in ( 'url', 'title', 'description' ):
            if key in d:
                setattr( c, key, d[key])

        return c

    def __init__( self, url = "", title = "", link = "", description = ""):
        self.url = url
        self.title = title
        self.link = link
        self.description = util.remove_html_tags( description)
        self.image = None
        self.pubDate = datetime.now().ctime()
        self.downloaded = None

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

        self.__tree_model = None
        
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
    
    def get_localdb_channel( self):
        try:
            locdb_reader = readLocalDB( self.url)
            locdb_reader.parseXML( self.index_file)
            return locdb_reader.channel
        except:
            return podcastChannel( self.url, self.title, self.link, self.description)

    def set_localdb_channel( self, channel):
        if channel != None:
            try:
                log( 'Setting localdb channel data')
                writeLocalDB( self.index_file, channel)
            except:
                log( 'Cannot save channel in set_localdb_channel( %s)', channel.title)

    localdb_channel = property(fget=get_localdb_channel,
                               fset=set_localdb_channel)
    
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
        for episode in self.localdb_channel:
            pubdate = episode.newer_pubdate( pubdate)
        return pubdate

    def get_new_episodes( self):
        last_pubdate = self.newest_pubdate_downloaded()
        gl = libgpodder.gPodderLib()

        if not last_pubdate:
            return self[0:min(len(self),gl.default_new)]

        new_episodes = []

        for episode in self.get_all_episodes():
            # episode is older than newest downloaded
            if episode.compare_pubdate( last_pubdate) < 0:
                continue

            # episode has been downloaded before
            if episode.is_downloaded() or gl.history_is_downloaded( episode.url):
                continue

            # download is currently in progress
            if services.download_status_manager.is_download_in_progress( episode.url):
                continue

            new_episodes.append( episode)

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
        libgpodder.getLock()
        localdb = self.index_file
        log( 'Local database: %s', localdb)

        self.downloaded = self.localdb_channel

        already_in_list = False
        # try to find the new item in the list
        for it in self.downloaded:
            if it.equals( item):
                already_in_list = True
                break

        # only append if not already in list
        if not already_in_list:
            self.downloaded.append( item)
            writeLocalDB( localdb, self.downloaded)

            # Update metadata on file (if possible and wanted)
            if libgpodder.gPodderLib().update_tags and tagging_supported():
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
            
        libgpodder.releaseLock()
        return not already_in_list
    
    def is_played(self, item):
        return libgpodder.gPodderLib().history_is_played( item.url)

    def get_all_episodes( self):
        episodes = []
        added_urls = []
        added_guids = []

        # go through all episodes (both new and downloaded),
        # prefer already-downloaded (in localdb)
        for item in [] + self.localdb_channel + self:
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

    def force_update_tree_model( self):
        self.__tree_model = None

    def update_model( self):
        new_episodes = self.get_new_episodes()

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

        if os.path.exists( local_filename):
            file_type = util.file_type_by_extension( util.file_extension_from_url( url))
            if file_type == 'audio':
                status_icon = util.get_tree_icon( 'audio-x-generic', played, self.icon_cache)
            elif file_type == 'video':
                status_icon = util.get_tree_icon( 'video-x-generic', played, self.icon_cache)
            elif file_type == 'torrent':
                status_icon = util.get_tree_icon( 'applications-internet', played, self.icon_cache)
            else:
                status_icon = util.get_tree_icon( 'unknown', played, self.icon_cache)
        elif services.download_status_manager.is_download_in_progress( url):
            status_icon = util.get_tree_icon( gtk.STOCK_GO_DOWN, icon_cache = self.icon_cache)
        elif libgpodder.gPodderLib().history_is_downloaded( url):
            status_icon = util.get_tree_icon( gtk.STOCK_DELETE, icon_cache = self.icon_cache)
        elif url in [ e.url for e in new_episodes ]:
            status_icon = util.get_tree_icon( gtk.STOCK_NEW, icon_cache = self.icon_cache)
        else:
            status_icon = None

        model.set( iter, 4, status_icon)

    def items_liststore( self):
        """
        Return a gtk.ListStore containing episodes for this channel
        """
        new_model = gtk.ListStore( gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_BOOLEAN, gtk.gdk.Pixbuf, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        new_episodes = self.get_new_episodes()

        for item in self.get_all_episodes():
            new_iter = new_model.append( ( item.url, item.title, util.format_filesize( item.length), True, None, item.cute_pubdate(), item.one_line_description(), item.description, item.local_filename() ))
            self.iter_set_downloading_columns( new_model, new_iter, new_episodes)
        
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

    def delete_episode_by_url(self, url):
        log( 'Delete %s', url)
        # no multithreaded access
        libgpodder.getLock()

        new_localdb = self.localdb_channel

        for item in new_localdb:
            if item.url == url:
                new_localdb.remove(item)

        self.localdb_channel = new_localdb

        # clean-up downloaded file
        episode = self.find_episode( url)
        util.delete_file( episode.local_filename())

        libgpodder.releaseLock()

    def obfuscate_password(self, password, unobfuscate = False):
        if unobfuscate:
            translation_table = string.maketrans(self.MAP_TO + self.MAP_TO.upper(), self.MAP_FROM + self.MAP_FROM.upper())
        else:
            translation_table = string.maketrans(self.MAP_FROM + self.MAP_FROM.upper(), self.MAP_TO + self.MAP_TO.upper())
        try:
            # For now at least, only ascii passwords will work, non-ascii passwords will be stored in plaintext :-(
            return string.translate(password.encode('ascii'), translation_table)
        except:
            return password
        
class podcastItem(object):
    """holds data for one object in a channel"""

    @staticmethod
    def from_feedparser_entry( entry, channel):
        episode = podcastItem( channel)

        episode.title = entry.get( 'title', util.get_first_line( util.remove_html_tags( entry.get( 'summary', ''))))
        episode.link = entry.get( 'link', '')
        episode.description = util.remove_html_tags( entry.get( 'summary', entry.get( 'link', entry.get( 'title', ''))))
        episode.guid = entry.get( 'id', '')
        episode.pubDate = entry.get( 'updated', '')

        if episode.title == '':
            log( 'Warning: Episode has no title, adding anyways.. (Feed Is Buggy!)', sender = episode)

        if len(entry.enclosures) > 1:
            log( 'Warning: More than one enclosure found in feed, only using first', sender = episode)

        enclosure = entry.enclosures[0]
        episode.url = enclosure.href
        episode.length = enclosure.length
        episode.mimetype = enclosure.type

        if episode.title == '':
            ( filename, extension ) = os.path.splitext( os.path.basename( episode.url))
            episode.title = filename

        return episode


    def __init__( self, channel):
        self.url = ''
        self.title = ''
        self.length = 0
        self.mimetype = ''
        self.guid = ''
        self.description = ''
        self.link = ''
        self.channel = channel
        self.pubDate = datetime.now().ctime()

    def one_line_description( self):
        lines = self.description.strip().splitlines()
        if not lines or lines[0] == '':
            return _('No description available')
        else:
            desc = lines[0].strip()
            if len( desc) > 84:
                return desc[:80] + '...'
            else:
                return desc

    def is_downloaded( self):
        return os.path.exists( self.local_filename())

    def local_filename( self):
        extension = util.file_extension_from_url( self.url)
        return os.path.join( self.channel.save_dir, md5.new( self.url).hexdigest() + extension)

    def file_type( self):
        return util.file_type_by_extension( util.file_extension_from_url( self.url))
    
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
        diff = int((time()+1)/seconds_in_a_day) - int(timestamp/seconds_in_a_day)
        
        if diff == 0:
           return _("Today")
        if diff == 1:
           return _("Yesterday")
        if diff < 7:
            return str(datetime.fromtimestamp( timestamp).strftime( "%A"))
        
        return str(datetime.fromtimestamp( timestamp).strftime( "%x"))

    def calculate_filesize( self):
        try:
            self.length = str(os.path.getsize( self.local_filename()))
        except:
            log( 'Could not get filesize for %s.', self.url)
    
    def equals( self, other_item):
        if other_item == None:
            return False
        
        return self.url == other_item.url



def channelsToModel( channels):
    new_model = gtk.ListStore( gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_STRING, gtk.gdk.Pixbuf)
    pos = 0
    
    for channel in channels:
        new_episodes = channel.get_new_episodes()
        count = len(channel)
        count_new = len(new_episodes)

        new_iter = new_model.append()
        new_model.set( new_iter, 0, channel.url)
        new_model.set( new_iter, 1, channel.title)

        new_model.set( new_iter, 2, count)
        if count_new == 0:
            new_model.set( new_iter, 3, '')
        elif count_new == 1:
            new_model.set( new_iter, 3, _('New episode: %s') % ( new_episodes[-1].title ) + ' ')
        else:
            new_model.set( new_iter, 3, _('%s new episodes') % count_new + ' ')

        if count_new:
            new_model.set( new_iter, 4, pango.WEIGHT_BOLD)
            new_model.set( new_iter, 5, str(count_new))
        else:
            new_model.set( new_iter, 4, pango.WEIGHT_NORMAL)
            new_model.set( new_iter, 5, '')

        new_model.set( new_iter, 6, pos)

        new_model.set( new_iter, 7, '%s\n<small>%s</small>' % ( saxutils.escape( channel.title), saxutils.escape( channel.description.split('\n')[0]), ))

        channel_cover_found = False
        if os.path.exists( channel.cover_file) and os.path.getsize(channel.cover_file) > 0:
            try:
                new_model.set( new_iter, 8, gtk.gdk.pixbuf_new_from_file_at_size( channel.cover_file, 32, 32))
                channel_cover_found = True
            except: 
                exctype, value = sys.exc_info()[:2]
                log( 'Could not convert icon file "%s", error was "%s"', channel.cover_file, value )

        if not channel_cover_found:
            iconsize = gtk.icon_size_from_name('channel-icon')
            if not iconsize:
                iconsize = gtk.icon_size_register('channel-icon',32,32)
            icon_theme = gtk.icon_theme_get_default()
            globe_icon_name = 'applications-internet'
            try:
                new_model.set( new_iter, 8, icon_theme.load_icon(globe_icon_name, iconsize, 0))
            except:
                log( 'Cannot load "%s" icon (using an old or incomplete icon theme?)', globe_icon_name)
                new_model.set( new_iter, 8, None)

        pos = pos + 1
    
    return new_model



def load_channels( load_items = True, force_update = False, callback_proc = None, callback_url = None, callback_error = None):
    importer = opml.Importer( libgpodder.gPodderLib().channel_opml_file)
    result = []
    count = 0
    for item in importer.items:
        callback_proc and callback_proc( count, len( importer.items))
        callback_url and callback_url( item['url'])
        result.append( podcastChannel.create_from_dict( item, load_items = load_items, force_update = force_update, callback_error = callback_error))
        count += 1
    return result

def save_channels( channels):
    exporter = opml.Exporter( libgpodder.gPodderLib().channel_opml_file)
    exporter.write( channels)


