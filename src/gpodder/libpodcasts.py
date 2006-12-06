
#
# gPodder (a media aggregator / podcast client)
# Copyright (C) 2005-2006 Thomas Perl <thp at perli.net>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, 
# MA  02110-1301, USA.
#


#
#  libpodcasts.py -- data classes for gpodder
#  thomas perl <thp@perli.net>   20051029
#
#

import gtk
import gobject
import htmlentitydefs

from liblogger import log
import libgpodder

from os.path import exists
from os.path import basename
from os.path import splitext
import os.path
import os
import glob
import shutil

from types import ListType
from datetime import datetime
from time import time

from liblocdbwriter import writeLocalDB
from liblocdbreader import readLocalDB

from threading import Event
from libwget import downloadThread
import re

from email.Utils import mktime_tz
from email.Utils import parsedate_tz

import md5


class podcastChannel(ListType):
    """holds data for a complete channel"""

    def __init__( self, url = "", title = "", link = "", description = ""):
        self.url = url
        self.title = title
        self.link = link
        self.description = stripHtml( description)
        self.image = None
        self.pubDate = datetime.now().ctime()
        self.language = ''
        self.copyright = ''
        self.webMaster = ''
        self.downloaded = None
        # should this channel be synced to devices? (ex: iPod)
        self.sync_to_devices = True
        # if this is set to true, device syncing (ex: iPod) should treat this as music, not as podcast)
        self.is_music_channel = False
        # to which playlist should be synced when "is_music_channel" is true?
        self.device_playlist_name = 'gPodder'
        
    def get_filename( self):
        """Return the MD5 sum of the channel URL"""
        return md5.new( self.url).hexdigest()

    filename = property(fget=get_filename)

    def get_title( self):
        return self.__title

    def set_title( self, value):
        self.__title = value.strip()

    title = property(fget=get_title,
                     fset=set_title)
    
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
    
    def set_metadata_from_localdb( self):
        log( 'Reading metadata from database: %s', self.index_file)
        libgpodder.getLock()
        self.copy_metadata_from( self.localdb_channel)
        libgpodder.releaseLock()

    def save_metadata_to_localdb( self):
        log( 'Saving metadata to database: %s', self.index_file)
        libgpodder.getLock()
        ch = self.localdb_channel
        ch.copy_metadata_from( self)
        self.localdb_channel = ch
        libgpodder.releaseLock()

    def copy_metadata_from( self, ch):
        # copy all metadata fields
        self.sync_to_devices = ch.sync_to_devices
        self.is_music_channel = ch.is_music_channel
        self.device_playlist_name = ch.device_playlist_name
    
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
        else:
            log( 'Podcast episode already downloaded.')
        
        writeLocalDB( localdb, self.downloaded)
        libgpodder.releaseLock()
        return not already_in_list
    
    def printChannel( self):
        print '- Channel: "' + self.title + '"'
        for item in self:
            print '-- Item: "' + item.title + '"'

    def isDownloaded( self, item):
        return self.podcastFilenameExists( item.url)

    def getItemsModel( self, want_color = True):
        new_model = gtk.ListStore( gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)

        for item in self:
            # Skip items with no download url
            if item.url != "":
                if self.isDownloaded(item) and want_color:
                    background_color = "#eeeeee"
                else:
                    background_color = "white"
                new_iter = new_model.append()
                new_model.set( new_iter, 0, item.url)
                new_model.set( new_iter, 1, item.title)
                new_model.set( new_iter, 2, item.getSize())
                new_model.set( new_iter, 3, True)
                new_model.set( new_iter, 4, background_color)
                new_model.set( new_iter, 5, item.cute_pubdate())
                new_model.set( new_iter, 6, item.one_line_description())
        
        return new_model
    
    def getActiveByUrl( self, url):
        i = 0
        
        for item in self:
            if item.url == url:
                return i
            i = i + 1

        return -1

    def downloadRss( self, force_update = True):
        if not exists( self.cache_file) or force_update:
            # remove old cache file
            libgpodder.gPodderLib().deleteFilename( self.cache_file)
            event = Event()
            downloadThread( self.url, self.cache_file, event).download()
            
            while event.isSet() == False:
                event.wait( 0.2)
                #FIXME: we do not want gtk code when not needed
                while gtk.events_pending():
                    gtk.main_iteration( False)

            # check if download was a success
            if exists( self.cache_file) == False:
                return None
        
        return self.cache_file
    
    def get_save_dir(self):
        save_dir = os.path.join( libgpodder.gPodderLib().downloaddir, self.filename ) + '/'

        # Create save_dir if it does not yet exist
        if libgpodder.gPodderLib().createIfNecessary( save_dir) == False:
            log( '(libpodcasts) Could not create: %s', save_dir)

        return save_dir
    
    save_dir = property(fget=get_save_dir)

    def get_cache_file(self):
        return libgpodder.gPodderLib().cachedir + self.filename + '.xml'

    cache_file = property(fget=get_cache_file)

    def remove_cache_file( self):
        libgpodder.gPodderLib().deleteFilename( self.cache_file)

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
    
    def getPodcastFilename( self, url):
        # strip question mark (and everything behind it), fix %20 errors
        filename = basename( url).replace( '%20', ' ')
	indexOfQuestionMark = filename.rfind( '?')
	if indexOfQuestionMark != -1:
	    filename = filename[:indexOfQuestionMark]
	# end strip questionmark
        extension = splitext( filename)[1].lower()

        return self.save_dir + md5.new(url).hexdigest() + extension
    
    def podcastFilenameExists( self, url):
        return exists( self.getPodcastFilename( url))
    
    def delete_episode_by_url(self, url):
        log( 'Delete %s', url)
        # no multithreaded access
        libgpodder.getLock()

        new_localdb = self.localdb_channel

        for item in new_localdb:
            if item.url == url:
                new_localdb.remove(item)

        self.localdb_channel = new_localdb

        libgpodder.releaseLock()

class podcastItem(object):
    """holds data for one object in a channel"""
    def __init__( self,
                  url = "",
                  title = "",
                  length = "0",
                  mimetype = "",
                  guid = "",
                  description = "",
                  link = "",
                  pubDate = None):
        self.url = url
        self.title = title
        self.length = length
        self.mimetype = mimetype
        self.guid = guid
        self.description = stripHtml( description)
        self.link = ""
        self.pubDate = pubDate
        if pubDate == None:
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
    
    def equals( self, other_item):
        if other_item == None:
            return False
        
        return self.url == other_item.url

    def get_title( self):
        return self.__title

    def set_title( self, value):
        self.__title = value.strip()

    title = property(fget=get_title,
                     fset=set_title)
    
    def getSize( self):
        try:
            size = int( self.length)
        except ValueError:
            return '-'
        
        kilobyte = 1024
        megabyte = kilobyte * 1024
        gigabyte = megabyte * 1024
        
        if size > gigabyte:
            # Might be a bit big, but who cares...
            return '%d GB' % int(size / gigabyte)
        if size > megabyte:
            return '%d MB' % int(size / megabyte)
        if size > kilobyte:
            return '%d KB' % int(size / kilobyte)

        return '%d Bytes' % size


class opmlChannel(object):
    def __init__( self, xmlurl, title = 'Unknown OPML Channel'):
        self.title = title
        self.xmlurl = xmlurl


def channelsToModel( channels):
    new_model = gtk.ListStore( gobject.TYPE_STRING, gobject.TYPE_STRING)
    
    for channel in channels:
        new_iter = new_model.append()
        new_model.set( new_iter, 0, channel.url)
        new_model.set( new_iter, 1, channel.title)
    
    return new_model

def stripHtml( html):
    # strips html from a string (fix for <description> tags containing html)
    dict = htmlentitydefs.entitydefs
    rexp = re.compile( "<[^>]*>")
    stripstr = rexp.sub( "", html)
    # strips html entities
    for key in dict.keys():
        stripstr = stripstr.replace( '&'+unicode(key,'iso-8859-1')+';', unicode(dict[key], 'iso-8859-1'))
    return stripstr

