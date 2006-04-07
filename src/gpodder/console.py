# -*- coding: utf-8 -*-


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

import os
import time

from libgpodder import gPodderChannelReader
from libgpodder import gPodderChannelWriter
from libgpodder import gPodderLib
from libpodcasts import podcastChannel
from librssreader import rssReader
from libwget import downloadThread

from os import kill
from string import strip
import popen2
import signal


#TODO: move to libwget??
class DownloadPool:
    def __init__(self, max_downloads = 3):
        assert(max_downloads > 0)
        
        self.max_downloads = max_downloads
        self.cur_downloads = 0

    def addone(self):
        self.cur_downloads += 1

    def set(self):
        '''Ping function for downloadThread'''
        if self.cur_downloads >0:
            self.cur_downloads -= 1
        else:
            self.cur_downloads = 0
    
    def may_download(self):
        return self.cur_downloads < self.max_downloads


def list_channels():
    reader = gPodderChannelReader()
    reader.read()
    for id, channel in enumerate(reader.channels):
        print "%s: %s" %(id, channel.url)

def add_channel(url):
    reader = gPodderChannelReader()
    channels = reader.read()

    cachefile = gPodderLib().downloadRss(url)
    rssreader = rssReader()
    rssreader.parseXML(url, cachefile)
        
    channels.append(rssreader.channel)
    gPodderChannelWriter().write(channels)

def del_channel(chid):
    #TODO maybe add id to channels.xml 
    reader = gPodderChannelReader()
    channels = reader.read()
    if chid >=0 and chid < len(channels):
        ch = channels.pop(chid)
        print _('delete channel: %s') %ch.url
        gPodderChannelWriter().write(channels)
    else:
        print _('%s is not a valid id') %str(chid)


def update():
    reader = gPodderChannelReader()
    reader.read(True)


def run():
    '''Update channels und download all items which are not already downloaded'''
    reader = gPodderChannelReader()
    updated_channels = reader.read(True)

    pool = DownloadPool()
    
    for channel in updated_channels:
       for item in channel.items:
           filename = channel.getPodcastFilename( item.url)
           if not channel.isDownloaded( item):
               while not pool.may_download():
                   time.sleep(3)
               
               pool.addone()
               #thread will call pool.set() when finished
               thread = downloadThread(item.url, filename, pool)
               thread.download()
               
    
def testForWget():
        command = "wget --version | head -n1"
        process = popen2.Popen3( command, True)
        stdout = process.fromchild
        data = stdout.readline( 80)
	kill( process.pid, signal.SIGKILL)
	return strip( data)
# end testForWget()

