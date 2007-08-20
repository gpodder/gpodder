

#
# gPodder (a media aggregator / podcast client)
# Copyright (C) 2005-2007 Thomas Perl <thp at perli.net>
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

from libgpodder import gPodderLib
from libpodcasts import load_channels
from liblogger import log

class localDB( object):
    def __init__( self):
        self.__channel_list = None

    def get_channel_list( self):
        if self.__channel_list != None:
            return self.__channel_list

        self.__channel_list = []
        self.available_channels = load_channels( load_items = False)

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
    
    def get_filename_by_podcast( self, url, podcast_url):
        ch = self.get_channel( url)

        if not ch:
            return None

        return ch.getPodcastFilename( podcast_url)
    
    def clear_cache( self):
        self.__channel_list = None


