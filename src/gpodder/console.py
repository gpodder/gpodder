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

from gpodder import util
from gpodder.liblogger import msg

from libpodcasts import load_channels
from libpodcasts import save_channels
from libpodcasts import podcastChannel

from libwget import downloadThread

import time

import popen2
import urllib


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
    for channel in load_channels( load_items = False):
        msg( 'channel', urllib.unquote( channel.url))


def add_channel( url):
    callback_error = lambda s: msg( 'error', s)

    url = util.normalize_feed_url( url)
    try:
        channel = podcastChannel.get_by_url( url, force_update = True)
    except:
        msg( 'error', _('Could not load feed from URL: %s'), urllib.unquote( url))
        return

    if channel:
        channels = load_channels( load_items = False)
        if channel.url in ( c.url for c in channels ):
            msg( 'error', _('Already added: %s'), urllib.unquote( url))
            return
        channels.append( channel)
        save_channels( channels)
        msg( 'add', urllib.unquote( url))
    else:
        msg( 'error', _('Could not add channel.'))


def del_channel( url):
    url = util.normalize_feed_url( url)

    channels = load_channels( load_items = False)
    keep_channels = []
    for channel in channels:
        if channel.url == url:
            msg( 'delete', urllib.unquote( channel.url))
        else:
            keep_channels.append( channel)

    if len(keep_channels) < len(channels):
        save_channels( keep_channels)
    else:
        msg( 'error', _('Could not remove channel.'))


def update():
    callback_url = lambda url: msg( 'update', urllib.unquote( url))
    callback_error = lambda s: msg( 'error', s)

    return load_channels( force_update = True, callback_url = callback_url, callback_error = callback_error)


def run():
    channels = update()

    pool = DownloadPool()
    for channel in channels:
       episodes_to_download = channel.get_new_episodes()

       for episode in episodes_to_download:
           msg( 'queue', urllib.unquote( episode.url))

       for episode in episodes_to_download:
           while not pool.has_free_slot():
               time.sleep( 3)

           pool.add()
           filename = episode.local_filename()
           #thread will call pool.set() when finished
           downloadThread( episode.url, filename, ready_event = pool, channelitem = channel, item = episode).download()
           msg( 'downloading', urllib.unquote( episode.url))
               
    
def wget_version():
    return popen2.Popen3( 'wget --version', True).fromchild.read().split('\n')[0].strip()

