
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

import libgpodder
from constants import isDebugging

from os.path import exists
from os.path import basename
from os.path import splitext

from types import ListType
from datetime import datetime
from time import time

from liblocdbwriter import writeLocalDB
from liblocdbreader import readLocalDB

from utils import deleteFilename
from utils import createIfNecessary

from threading import Event
from libwget import downloadThread
import re

from email.Utils import mktime_tz
from email.Utils import parsedate_tz

import md5

from xml.sax.saxutils import DefaultHandler
from xml.sax.handler import ErrorHandler
from xml.sax import make_parser
from string import strip

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
        self.shortname = None
        self.downloaded = None
        self.__filename = None
        self.__download_dir = None
        # should this channel be synced to devices? (ex: iPod)
        self.sync_to_devices = True
        # if this is set to true, device syncing (ex: iPod) should treat this as music, not as podcast)
        self.is_music_channel = False
        # to which playlist should be synced when "is_music_channel" is true?
        self.device_playlist_name = 'gPodder'
        
    # Create all the properties
    def get_filename(self):
        if self.__filename == None:
            self.__filename = ""

            for char in self.title.lower():
                if (char >= 'a' and char <= 'z') or (char >= 'A' and char <= 'Z') or (char >= '1' and char <= '9'):
                    self.__filename = self.__filename + char
                    
        if self.__filename == "":
            self.__filename = "__unknown__"

        return self.__filename

    def set_filename(self, value):
        self.__filename = value
        
    filename = property(fget=get_filename,
                        fset=set_filename)
    
    def addItem( self, item):
        self.append( item)

    def get_localdb_channel( self):
        ch = None
        try:
            locdb_reader = readLocalDB()
            locdb_reader.parseXML( self.index_file)
            return locdb_reader.channel
        except:
            return podcastChannel( self.url, self.title, self.link, self.description)

    def set_localdb_channel( self, channel):
        if channel != None:
            try:
                writeLocalDB( self.index_file, channel)
            except:
                if isDebugging():
                    print 'Cannot save localDB channel in set_localdb_channel( %s)' % channel.title
    
    def set_metadata_from_localdb( self):
        if isDebugging():
            print 'Reading metadata from localdb: %s' % self.index_file
        libgpodder.getLock()
        ch = self.get_localdb_channel()
        if ch != None:
            self.copy_metadata_from( ch)
        libgpodder.releaseLock()

    def save_metadata_to_localdb( self):
        if isDebugging():
            print 'Saving metadata to localdb: %s' % self.index_file
        libgpodder.getLock()
        ch = self.get_localdb_channel()
        if ch != None:
            ch.copy_metadata_from( self)
            self.set_localdb_channel( ch)
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
        if isDebugging():
            print "localdb: " + localdb

        self.downloaded = self.get_localdb_channel()
        
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
            if isDebugging():
                print "no need to re-add already added podcast item to localDB"
        
        writeLocalDB( localdb, self.downloaded)
        libgpodder.releaseLock()
        return not already_in_list
    
    def printChannel( self):
        print '- Channel: "' + self.title + '"'
        for item in self:
            print '-- Item: "' + item.title + '"'

    def isDownloaded( self, item):
        return self.podcastFilenameExists( item.url)

    # \todo Move away. We don't want gtk code in the core.
    def getItemsModel( self, want_color = True):
        new_model = gtk.ListStore( gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING)

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
        
        return new_model
    
    def getActiveByUrl( self, url):
        i = 0
        
        for item in self:
            if item.url == url:
                return i
            i = i + 1

        return -1

    def downloadRss( self, force_update = True):
        
        if (self.filename == "__unknown__" or exists( self.cache_file) == False) or force_update:
            # remove old cache file
            deleteFilename( self.cache_file)
            event = Event()
            downloadThread(self.url, self.cache_file, event).download()
            
            while event.isSet() == False:
                event.wait( 0.2)
                #FIXME: we do not want gtk code when not needed
                while gtk.events_pending():
                    gtk.main_iteration( False)

            # check if download was a success
            if exists( self.cache_file) == False:
                # FIXME: this should raise an exception
                return None
        
        return self.cache_file

    def update(self, rss_update):
        cachefile = self.downloadRss(rss_update)
        # check if download was a success
        if cachefile != None:
            reader = rssReader()
            reader.parseXML(self, cachefile)
            
    def get_save_dir(self):
        savedir = self.download_dir + self.filename + "/"
        if createIfNecessary( savedir) == False:
            self.reset_download_dir()
            savedir = self.download_dir + self.filename + "/"
        return savedir
    
    save_dir = property(fget=get_save_dir)

    def get_download_dir(self):
        if self.__download_dir == None:
            return libgpodder.gPodderLib().downloaddir
        else:
            return self.__download_dir

    def reset_download_dir( self):
        self.__download_dir = libgpodder.gPodderLib().downloaddir

    def set_download_dir(self, value):
        self.__download_dir = value
        if createIfNecessary(self.__download_dir) == False:
            # fallback to hopefully sane download dir
            self.reset_download_dir()
            return False
        return True
        #  the following disabled at the moment..
        #if isDebugging():
        #    print "set_download_dir: ", self, self.__download_dir
        
    download_dir = property (fget=get_download_dir,
                             fset=set_download_dir)

    def get_cache_file(self):
        return libgpodder.gPodderLib().cachedir + self.filename + ".xml"

    cache_file = property(fget=get_cache_file)
    
    def get_index_file(self):
        # gets index xml filename for downloaded channels list
        return self.save_dir + "index.xml"
    
    index_file = property(fget=get_index_file)
    
    def get_cover_file( self):
        # gets cover filename for cover download cache
        return self.save_dir + "cover"

    cover_file = property(fget=get_cover_file)
    
    def getPodcastFilename( self, url):
        # strip question mark (and everything behind it), fix %20 errors
        filename = basename( url).replace( "%20", " ")
	indexOfQuestionMark = filename.rfind( "?")
	if indexOfQuestionMark != -1:
	    filename = filename[:indexOfQuestionMark]
	# end strip questionmark
        extension = splitext( filename)[1].lower()

        legacy_location = self.save_dir + filename
        new_location = self.save_dir + md5.new(url).hexdigest() + extension

        # this supports legacy podcast locations, should be removed at some point (or move files from old location to new location)
        if exists( legacy_location):
            if isDebugging():
                print "(gpodder < 0.7 compat) using old filename scheme for already downloaded podcast."
            return legacy_location
        else:
            return new_location
    
    def podcastFilenameExists( self, url):
        return exists( self.getPodcastFilename( url))
    
    def deleteDownloadedItemByUrlAndTitle(self, url, title):
        if isDebugging():
            print "deleteDownloadedItemByUrlAndTitle: " + title + " (" + url + ")"
        # no multithreaded access
        libgpodder.getLock()
	nr_items = 0
        localdb = self.index_file
        if isDebugging():
            print "localdb: " + localdb
        try: 
            locdb_reader = readLocalDB()
            locdb_reader.parseXML( localdb)
            self.downloaded = locdb_reader.channel
            for item in self.downloaded:
                if item.title == title and item.url == url:
                    nr_items += 1
                    self.downloaded.remove(item)
        except:
            print _("No LocalDB found or error in existing LocalDB.")
        if isDebugging():
            print " found", nr_items, "matching item(s)"
        if nr_items > 0:
            writeLocalDB( localdb, self.downloaded)
        libgpodder.releaseLock()
        if nr_items > 0:
            return True
	return False

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
        
        # we suppose it's the same when the download URL is the same..
        return self.url == other_item.url
    
    def getSize( self):
        try:
            size = int( self.length)
        except ValueError:
            return '?? MB'
        
        kilobyte = 1024
        megabyte = kilobyte * 1024
        gigabyte = megabyte * 1024
        
        if size > gigabyte:
            # Might be a bit big, but who cares...
            return '%d GB' % str(size / gigabyte)
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
    new_model = gtk.ListStore( gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_OBJECT)
    
    for channel in channels:
        new_iter = new_model.append()
        new_model.set( new_iter, 0, channel.url)
        new_model.set( new_iter, 1, channel.title) # + " ("+channel.url+")")
        #if channel.image != None:
        #    new_model.set( new_iter, 2, gtk.gdk.pixbuf_new_from_file_at_size( channel.image, 60, 60))
        #else:
        #    new_model.set( new_iter, 2, None)
    
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

class rssErrorHandler( ErrorHandler):
    def __init__( self):
        None

    def error( self, exception):
        print exception

    def fatalError( self, exception):
        print "FATAL ERROR: ", exception

    def warning( self, exception):
        print "warning: ", exception

class rssReader( DefaultHandler):
    channel_url = ""
    channel = None
    current_item = None
    current_element_data = ""

    def __init__( self):
        None
    
    def parseXML( self, channel, filename):
        self.channel = channel
        parser = make_parser()
	parser.returns_unicode = True
        parser.setContentHandler( self)
	parser.setErrorHandler( rssErrorHandler())
        # no multithreaded access to filename
        libgpodder.getLock()
        try:
            parser.parse( filename)
        finally:
            libgpodder.releaseLock()
    
    def startElement( self, name, attrs):
        self.current_element_data = ""

        # We ignore the channel tag. 
#        if name == "channel":
#            pass 
        if name == "item":
            self.current_item = podcastItem()
        
        if name == "enclosure" and self.current_item != None:
            self.current_item.url = attrs.get( "url", "")
            self.current_item.length = attrs.get( "length", "")
            self.current_item.mimetype = attrs.get( "type", "")

        if name == "itunes:image":
            self.channel.image = attrs.get( "href", "")
    
    def endElement( self, name):
        if self.current_item == None:
            if name == "title":
                self.channel.title = self.current_element_data
            if name == "link":
                self.channel.link = self.current_element_data
            if name == "description":
                self.channel.description = stripHtml( self.current_element_data)
            if name == "pubDate":
                self.channel.pubDate = self.current_element_data
            if name == "language":
                self.channel.language = self.current_element_data
            if name == "copyright":
                self.channel.copyright = self.current_element_data
            if name == "webMaster":
                self.channel.webMaster = self.current_element_data
        
        if self.current_item != None:
            if name == "title":
                self.current_item.title = self.current_element_data
            if name == "link":
                self.current_item.link = self.current_element_data
            if name == "description":
                self.current_item.description = stripHtml( self.current_element_data)
            if name == "guid":
                self.current_item.guid = self.current_element_data
            if name == "pubDate":
                self.current_item.pubDate = self.current_element_data
            if name == "item":
                self.channel.addItem( self.current_item)
                self.current_item = None
    
    def characters( self, ch):
        self.current_element_data = self.current_element_data + ch
