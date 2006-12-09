

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

from libgpodder import gPodderLib
from libgpodder import gPodderChannelReader
from liblogger import log

class localDB( object):
    def __init__( self):
        self.__channel_list = None

    def get_channel_list( self):
        if self.__channel_list != None:
            return self.__channel_list

        self.__channel_list = []
        self.available_channels = gPodderChannelReader().read()

        for channel in self.available_channels:
            local = channel.localdb_channel
            if len( local):
                self.__channel_list.append( local)
        
        return self.__channel_list

    channel_list = property(fget=get_channel_list)


    def get_channel( self, url):
        for channel in self.channel_list:
            if channel.url == url:
                return channel
        
        return None

    def get_podcast( self, url):
        for channel in self.channel_list:
            for episode in channel:
                if episode.url == url:
                    return episode
        
        return None
    

    def get_tree_model( self, url):
        # Try to add downloaded items (TODO: remove at some point in the future)
        to_be_added = []
        for episode in self.get_channel( url):
            to_be_added.append( episode.url)
        if to_be_added:
            gPodderLib().history_mark_downloaded( to_be_added)

        return self.get_channel( url).items_liststore( False)

    def get_model( self):
        new_model = gtk.ListStore( gobject.TYPE_STRING, gobject.TYPE_STRING)
        
        for channel in self.channel_list:
            new_iter = new_model.append()
            new_model.set( new_iter, 0, channel.url)
            new_model.set( new_iter, 1, channel.title)
        
        return new_model
    

    def get_filename_by_podcast( self, url, podcast_url):
        ch = self.get_channel( url)

        if not ch:
            return None

        return ch.getPodcastFilename( podcast_url)
    
    def clear_cache( self):
        self.__channel_list = None


