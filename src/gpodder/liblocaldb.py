

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
#  liblocaldb.py -- access routines to the local podcast database
#  thomas perl <thp@perli.net>   20060204
#
#

import gtk
import gobject
import libgpodder

from liblocdbreader import readLocalDB
from libgpodder import gPodderLib

from os import listdir
from os import sep
from os.path import isfile

class localDB( object):
    directories = []
    downloaddir = None
    iflist = None # index file list (will be cached in object)
    chlist = None # downloaded channels list (will be cached in object)
    localdbs = {} # localdbs is a cache that maps filenames to readLocalDB objs
    
    def __init__( self):
        if libgpodder.isDebugging():
            print "created new localDB object"
        self.downloaddir = gPodderLib().downloaddir
        self.directories = listdir( self.downloaddir)

    def getIndexFileList( self):
        # do not re-read if we already readed the list of index files
        if self.iflist != None:
            if libgpodder.isDebugging():
                print "(localDB) using cached index file list"
            return self.iflist
        
        self.iflist = []
        
        for d in self.directories:
            self.iflist.append( self.downloaddir + sep + d + sep + "index.xml")
        
        return self.iflist

    def getDownloadedChannelsList( self):
        # do not re-read downloaded channels list
        if self.chlist != None:
            if libgpodder.isDebugging():
                print "(localDB) using cached downloaded channels list"
            return self.chlist
        
        self.chlist = []
        
        ifl = self.getIndexFileList()
        for f in ifl:
            if isfile( f):
                # whew! found a index file, parse it and append
                # if there's a rdb in cache already, use that
                if f in self.localdbs:
                    rdb = self.localdbs[f]
                else:
                    rdb = readLocalDB()
                    rdb.parseXML( f)
                    self.localdbs[f] = rdb
                # append this one to list
                if len( rdb.channel) > 0:
                    self.chlist.append( rdb.channel)
        
        return self.chlist

    def getDownloadedChannelsModel( self):
        new_model = gtk.ListStore( gobject.TYPE_STRING, gobject.TYPE_STRING)
        
        for channel in self.getDownloadedChannelsList():
            if libgpodder.isDebugging():
                print "(getmodel) " + channel.title
            new_iter = new_model.append()
            new_model.set( new_iter, 0, channel.url)
            new_model.set( new_iter, 1, channel.title)
        
        return new_model

    def get_rdb_by_filename( self, filename):
        if filename in self.localdbs:
          rdb = self.localdbs[filename]
        else:
          rdb = readLocalDB()
          rdb.parseXML( filename)
          self.localdbs[filename] = rdb
        
        return rdb
    
    def getDownloadedEpisodesModelByFilename( self, filename):
        return self.get_rdb_by_filename( filename).channel.getItemsModel( False)
    
    def getLocalFilenameByPodcastURL( self, channel_filename, url):
        return self.get_rdb_by_filename( channel_filename).channel.getPodcastFilename( url)

    def get_podcast_by_podcast_url( self, channel_filename, url):
        for episode in self.get_rdb_by_filename( channel_filename).channel:
            if episode.url == url:
                return episode
        
        return None
    
    def clear_cache( self):
        # clear cached data, so it is re-read next time
        self.localdbs.clear()
        self.chlist = None
        self.iflist = None

