
#
# gPodder
# Copyright (c) 2005-2006 Thomas Perl <thp@perli.net>
# Released under the GNU General Public License (GPL)
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
    
    def getDownloadedEpisodesModelByFilename( self, filename):
        if filename in self.localdbs:
          rdb = self.localdbs[filename]
        else:
          rdb = readLocalDB()
          rdb.parseXML( filename)
          self.localdbs[filename] = rdb
        
        return rdb.channel.getItemsModel()
    
    def getLocalFilenameByPodcastURL( self, channel_filename, url):
        if channel_filename in self.localdbs:
          rdb = self.localdbs[channel_filename]
        else:
          rdb = readLocalDB()
          rdb.parseXML( channel_filename)
          self.localdbs[channel_filename] = rdb
        
        return rdb.channel.getPodcastFilename( url)
    
    def clear_cache( self):
        # clear cached data, so it is re-read next time
        self.localdbs.clear()
        self.chlist = None
        self.iflist = None

