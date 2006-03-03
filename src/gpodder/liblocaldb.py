
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
    
    def __init__( self):
        self.downloaddir = gPodderLib().downloaddir
        self.directories = listdir( self.downloaddir)

    def getIndexFileList( self):
        iflist = []
        
        for d in self.directories:
            iflist.append( self.downloaddir + sep + d + sep + "index.xml")

        return iflist

    def getDownloadedChannelsList( self):
        newlist = []
        
        ifl = self.getIndexFileList()
        for f in ifl:
            if isfile( f):
                # whew! found a index file, parse it and append
                rdb = readLocalDB()
                rdb.parseXML( f)
                newlist.append( rdb.channel)
        
        return newlist

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
        rdb = readLocalDB()
        rdb.parseXML( filename)
        return rdb.channel.getItemsModel()
    
    def getLocalFilenameByPodcastURL( self, channel_filename, url):
        rdb = readLocalDB()
        rdb.parseXML( channel_filename)
        return gPodderLib().getPodcastFilename( rdb.channel, url)

