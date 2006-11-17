

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

from liblocdbreader import readLocalDB
from libgpodder import gPodderLib
from liblogger import log

from os import listdir
from os import sep
from os.path import isfile

class localDB( object):
    def __init__( self):
        self.channel_list = None
        self.local_db_cache = {}

    def getDownloadedChannelsList( self):
        # do not re-read downloaded channels list
        if self.channel_list != None:
            log( '(localDB) using cached downloaded channels list')
            return self.channel_list
        
        self.channel_list = []
        
        for d in listdir( gPodderLib().downloaddir):
            f = sep.join( [ gPodderLib().downloaddir, d, 'index.xml' ])
            if isfile( f):
                # Index file exists, parse if needed
                if f not in self.local_db_cache:
                    rdb = readLocalDB()
                    rdb.parseXML( f)
                    # Use folder name as channel's filename
                    rdb.channel.set_filename( d)
                    self.local_db_cache[f] = rdb

                # Append index file to list if it has episodes
                if len( self.local_db_cache[f].channel) > 0:
                    self.channel_list.append( self.local_db_cache[f].channel)
        
        return self.channel_list

    def getDownloadedChannelsModel( self):
        new_model = gtk.ListStore( gobject.TYPE_STRING, gobject.TYPE_STRING)
        
        for channel in self.getDownloadedChannelsList():
            log( 'Getting ListStore for %s', channel.title)
            new_iter = new_model.append()
            new_model.set( new_iter, 0, channel.url)
            new_model.set( new_iter, 1, channel.title)
        
        return new_model

    def get_rdb_by_filename( self, filename):
        if filename not in self.local_db_cache:
            self.clear_cache()
            self.getDownloadedChannelsList()
        
        return self.local_db_cache[filename]
    
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
        # Clear cache, so it can be re-read on next request
        self.local_db_cache = {}
        self.channel_list = None

