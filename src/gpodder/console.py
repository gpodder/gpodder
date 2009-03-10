# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from gpodder import util
from gpodder import download
from gpodder import sync
from gpodder.libgpodder import gl
from gpodder.liblogger import msg
from gpodder.dbsqlite import db

from libpodcasts import load_channels
from libpodcasts import update_channels
from libpodcasts import save_channels
from libpodcasts import PodcastChannel

import time

import popen2
import urllib
import sys


def list_channels():
    for channel in load_channels():
        msg('podcast', urllib.unquote(channel.url))


def add_channel( url):
    callback_error = lambda s: msg( 'error', s)

    url = util.normalize_feed_url(url)

    channels = load_channels()
    if url in (c.url for c in channels):
        msg('error', _('Already added: %s'), urllib.unquote(url))
        return

    try:
        channel = PodcastChannel.load(url, create=True)
    except:
        msg( 'error', _('Could not load feed from URL: %s'), urllib.unquote( url))
        return

    if channel:
        channels.append(channel)
        save_channels(channels)
        db.commit()
        msg('add', urllib.unquote(url))
    else:
        msg('error', _('Could not add podcast.'))


def del_channel( url):
    url = util.normalize_feed_url( url)

    channels = load_channels()
    keep_channels = []
    for channel in channels:
        if channel.url == url:
            msg( 'delete', urllib.unquote( channel.url))
        else:
            keep_channels.append( channel)

    if len(keep_channels) < len(channels):
        save_channels( keep_channels)
        db.commit()
    else:
        msg('error', _('Could not remove podcast.'))


def update():
    callback_error = lambda s: msg('error', s)
    sys.stdout.write(_('Updating podcast feeds...'))
    sys.stdout.flush()
    result = update_channels(callback_error=callback_error)
    print _('done.')
    db.commit()
    return result

def run():
    channels = update()
    new_episodes = 0

    for channel in channels:
       for episode in channel.get_new_episodes():
           msg( 'downloading', urllib.unquote( episode.url))
           # Calling run() calls the code in the current thread
           download.DownloadThread( channel, episode).run()
           new_episodes += 1

    if new_episodes == 0:
        print _('No new episodes to download.')
    elif new_episodes == 1:
        print _('Downloaded one new episode.')
    else:
        print _('Downloaded %d new episodes.') % new_episodes
    db.commit()

def sync_device():
    device = sync.open_device()
    if device is None:
        msg('error', _('No device configured. Please use the GUI.'))
        return False

    callback_status = lambda s: msg('status', '%s', s)
    device.register('status', callback_status)
    callback_done = lambda: msg('done', _('Synchronization finished.'))
    device.register('done', callback_done)
    callback_progress = lambda i, n: msg('progress', _('Synchronizing: %d of %d') % (i, n))
    device.register('progress', callback_progress)

    if not device.open():
        msg('error', _('Cannot open device.'))
        return False

    for channel in load_channels():
        if not channel.sync_to_devices:
            msg('info', _('Skipping podcast: %s') % channel.title)
            continue
        
        episodes_to_sync = []
        for episode in channel.get_all_episodes():
            if episode.was_downloaded(and_exists=True):
                episodes_to_sync.append(episode)
        device.add_tracks(episodes_to_sync)

    db.commit()
    if not device.close():
        msg('error', _('Cannot close device.'))
        return False

def sync_stats():
    size = 0
    device = sync.open_device()
    if device is None:
        msg('error', _('No device configured. Please use the GUI.'))
        return False

    for channel in load_channels():
        if not channel.sync_to_devices:
            continue
        for episode in channel.get_all_episodes():
            if episode.was_downloaded(and_exists=True):
                episode.calculate_filesize()
                size += episode.length
    msg('info', _('Free space on device %s: %s') % (gl.get_device_name(), gl.format_filesize(device.get_free_space())))
    msg('info', _('Size of episodes to sync: %s') % gl.format_filesize(size))

    difference = device.get_free_space() - size
    if difference < 0:
        msg('error', _('Need to free at least %s more') % gl.format_filesize(abs(difference)))
        return False
    else:
        msg('info', _('Free space after sync: %s') % gl.format_filesize(abs(difference)))

    if not device.close():
        msg('error', _('Cannot close device.'))
        return False

    return True
