# -*- coding: utf-8 -*-


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

import os
import time

from libgpodder import gPodderChannelReader
from libgpodder import gPodderChannelWriter
from libgpodder import gPodderLib
from libpodcasts import podcastChannel

from librssreader import rssReader
from libwget import downloadThread
from liblogger import msg

from os import kill
from string import strip
import popen2
import signal


class DownloadPool(object):
    def __init__( self, max_downloads = 1):
        self.max_downloads = max_downloads
        self.cur_downloads = 0

    def add( self):
        self.cur_downloads += 1

    def set( self):
        if self.cur_downloads < 1:
            self.cur_downloads = 1

        self.cur_downloads -= 1
    
    def has_free_slot( self):
        return self.cur_downloads < self.max_downloads


def list_channels():
    for channel in gPodderChannelReader().read():
        msg( 'channel', channel.url)


def add_channel( url):
    gl = gPodderLib()

    channels = gPodderChannelReader().read()

    url = gl.sanitize_feed_url( url)
    channel = podcastChannel( url = url)
    channel.remove_cache_file()
    channels.append( channel)

    gPodderChannelWriter().write( channels)

    if len( gPodderChannelReader().read( False)) == len( channels):
        msg( 'add', url)
    else:
        msg( 'error', _('Could not add channel.'))


def del_channel( url):
    gl = gPodderLib()
    
    channels = gPodderChannelReader().read()

    removed = False

    url = gl.sanitize_feed_url( url)
    for i in range( len(channels)-1, -1, -1):
        if channels[i].url == url:
            channels.remove( channels[i])
            msg( 'delete', url)
            removed = True

    if removed:
        gPodderChannelWriter().write( channels)
    else:
        msg( 'error', _('Could not remove channel.'))


def update():
    urlcallback = lambda url: msg( 'update', url)

    return gPodderChannelReader().read( True, callback_url = urlcallback)


def run():
    gl = gPodderLib()
    channels = update()

    pool = DownloadPool()
    for channel in channels:
       episodes_to_download = []
       last_pubdate = channel.newest_pubdate_downloaded()

       if not last_pubdate:
            for item in channel[0:min(len(channel),3)]:
                msg( 'queue', item.url)
                episodes_to_download.append( item)
       else:
            for item in channel:
                if item.compare_pubdate( last_pubdate) >= 0 and not channel.is_downloaded( item) and not gl.history_is_downloaded( item.url):
                    msg( 'queue', item.url)
                    episodes_to_download.append( item)

       for item in episodes_to_download:
           if channel.is_downloaded( item) or gl.history_is_downloaded( item.url):
               break

           while not pool.has_free_slot():
               time.sleep( 3)

           pool.add()
           filename = channel.getPodcastFilename( item.url)
           #thread will call pool.set() when finished
           downloadThread( item.url, filename, ready_event = pool, channelitem = channel, item = item).download()
           msg( 'downloading', item.url)
               
    
def testForWget():
        command = 'wget --version'
        # get stdout, read all, split by line, strip whitespace
        version = popen2.Popen3( command, True).fromchild.read().split('\n')[0].strip()
	return version
# end testForWget()

