

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
#  libipodsync.py -- sync localdb contents with ipod playlist
#  thomas perl <thp@perli.net>   20060405
#
#


# variable tells if ipod functions are to be enabled
enable_ipod_functions = True


try:
    import gpod
    import eyeD3
except:
    enable_ipod_functions = False

import os
import sys
import time
import email.Utils

from liblogger import log

import liblocaldb
import libpodcasts

import gobject

# do we provide iPod functions to the user?
def ipod_supported():
    global enable_ipod_functions
    return enable_ipod_functions

# file extensions that are handled as video
video_extensions = [ "mov", "mp4", "m4v" ]


class gPodder_iPodSync(object):
    itdb = None
    ipod_mount = '' # mountpoint for ipod
    playlist_name = 'gpodder' # name of playlist to sync to
    pl_master = None
    pl_podcasts = None
    callback_progress = None
    callback_status = None
    callback_done = None

    def __init__( self, ipod_mount = '/media/ipod/', callback_progress = None, callback_status = None, callback_done = None):
        if not ipod_supported():
            log( '(ipodsync) iPod functions not supported. (libgpod + eyed3 needed)')
        self.ipod_mount = ipod_mount
        self.callback_progress = callback_progress
        self.callback_status = callback_status
        self.callback_done = callback_done
    
    def open( self):
        if not ipod_supported():
            return False
        if self.itdb == None:
            self.itdb = gpod.itdb_parse( str( self.ipod_mount), None)
            if not self.itdb:
                return False
            self.itdb.mountpoint = str(self.ipod_mount)
            self.pl_master = gpod.sw_get_playlists( self.itdb)[0]
            self.pl_podcasts = gpod.itdb_playlist_podcasts( self.itdb)
        return True

    def close( self, write_update = True):
        if not ipod_supported():
            return False
        if write_update:
            if self.callback_progress != None:
                gobject.idle_add( self.callback_progress, 100, 100)
            if self.callback_status != None:
                gobject.idle_add( self.callback_status, '...', '...', _('Saving iPod database...'))
            if self.itdb:
                gpod.itdb_write( self.itdb, None)
        self.itdb = None
        if self.callback_done != None:
            time.sleep(1)
            gobject.idle_add( self.callback_done)
        return True

    def remove_from_ipod( self, track, playlists):
        if not ipod_supported():
            return False
        log( '(ipodsync) Removing track from iPod: %s', track.title)
        if self.callback_status != None:
            gobject.idle_add( self.callback_status, track.title, track.artist)
        fname = gpod.itdb_filename_on_ipod( track)
        for playlist in playlists:
            try:
                gpod.itdb_playlist_remove_track( playlist, track)
            except:
                pass
        
        gpod.itdb_track_unlink( track)
        try:
            os.unlink( fname)
        except:
            # suppose we've already deleted it or so..
            pass
    
    def get_playlist_by_name( self, playlistname = 'gPodder'):
        if not ipod_supported():
            return False
        for playlist in gpod.sw_get_playlists( self.itdb):
            if playlist.name == playlistname:
                log( '(ipodsync) Found old playlist: %s', playlist.name)
                return playlist
        
        log( '(ipodsync) New playlist: %s', playlistname)
        new_playlist = gpod.itdb_playlist_new( str(playlistname), False)
        gpod.itdb_playlist_add( self.itdb, new_playlist, -1)
        return new_playlist

    def get_playlist_for_channel( self, channel):
        if channel.is_music_channel:
            return self.get_playlist_by_name( channel.device_playlist_name)
        else:
            return self.pl_podcasts

    def episode_is_on_ipod( self, channel, episode):
        if not ipod_supported():
            return False
        for track in gpod.sw_get_playlist_tracks( self.get_playlist_for_channel( channel)):
            if episode.title == track.title and channel.title == track.album:
                log( '(ipodsync) Already on iPod: %s (from %s)', episode.title, track.title)
                return True
        
        return False

    def clean_playlist( self):
        if not ipod_supported():
            return False
        for track in gpod.sw_get_playlist_tracks( self.pl_podcasts):
            log( '(ipodsync) Trying to remove: %s', track.title)
            self.remove_from_ipod( track, [ self.pl_podcasts ])

    def copy_channel_to_ipod( self, channel):
        if not ipod_supported():
            return False
        if not channel.sync_to_devices:
            # we don't want to sync this..
            return False
        max = len( channel)
        i = 1
        for episode in channel:
            if self.callback_progress != None:
                gobject.idle_add( self.callback_progress, i, max)
            if channel.isDownloaded( episode):
                self.add_episode_from_channel( channel, episode)
            i=i+1
        if self.callback_status != None:
            gobject.idle_add( self.callback_status, '...', '...', _('Complete: %s') % channel.title)
        time.sleep(1)

    def set_podcast_flags( self, track):
        if not ipod_supported():
            return False
        try:
            # Add blue bullet next to unplayed tracks on 5G iPods
            track.mark_unplayed = 0x02

            # Podcast flags (for new iPods?)
            track.remember_playback_position = 0x01

            # Podcast flags (for old iPods?)
            track.flag1 = 0x02
            track.flag2 = 0x01
            track.flag3 = 0x01
            track.flag4 = 0x01
        except:
            log( '(ipodsync) Seems like your python-gpod is out-of-date.')

    def add_episode_from_channel( self, channel, episode):
        if not ipod_supported():
            return False
        if self.callback_status != None:
            channeltext = channel.title
            if channel.is_music_channel:
                channeltext = _('%s (to "%s")') % ( channel.title, channel.device_playlist_name )
            gobject.idle_add( self.callback_status, episode.title, channeltext)
        
        if self.episode_is_on_ipod( channel, episode):
            # episode is already here :)
            return True
        
        log( '(ipodsync) Adding item: %s from %s', episode.title, channel.title)
        local_filename = str(channel.getPodcastFilename( episode.url))
        try:
            eyed3_info = eyeD3.Mp3AudioFile( local_filename)
            track_length = eyed3_info.getPlayTime() * 1000 # in milliseconds
            # TODO: how to get length of video (mov, mp4, m4v) files??
        except:
            print '(ipodsync) Warning: cannot get length for %s, will use 1 hour' % episode.title
            track_length = 20*60*1000 # hmm.. (20m so we can skip on video/audio with unknown length)
        
        track = gpod.itdb_track_new()
        
        if channel.is_music_channel:
            track.artist = str(channel.title)
        else:
            track.artist = 'gPodder podcast'
            self.set_podcast_flags( track)
        
        # Add release time to track if pubDate is parseable
        ipod_date = email.Utils.parsedate(episode.pubDate)
        if ipod_date != None:
            # + 2082844800 for unixtime => mactime (1970 => 1904)
            track.time_released = time.mktime(ipod_date) + 2082844800
        
        track.title = str(episode.title)
        track.album = str(channel.title)
        track.tracklen = track_length
        track.filetype = 'mp3' # huh?! harcoded?! well, well :) FIXME, i'd say
        track.description = str(episode.description)
        track.podcasturl = str(episode.url)
        track.podcastrss = str(channel.url)
        track.size = os.path.getsize( local_filename)
        
        gpod.itdb_track_add( self.itdb, track, -1)
        playlist = self.get_playlist_for_channel( channel)
        gpod.itdb_playlist_add_track( playlist, track, -1)

        # Copy channel cover file to iPod
        cover_filename = os.path.dirname( local_filename) + '/cover'
        if os.path.isfile( cover_filename):
            # Copy it to the iPod only if it exists
            gpod.itdb_track_set_thumbnails( track, cover_filename)
        
        # dirty hack to get video working, seems to work
        for ext in video_extensions:
            if local_filename.lower().endswith( '.%s' % ext):
                track.unk208 = 0x00000002 # documented on http://ipodlinux.org/ITunesDB

        # if it's a music channel, also sync to master playlist
        if channel.is_music_channel:
            gpod.itdb_playlist_add_track( self.pl_master, track, -1)

        if gpod.itdb_cp_track_to_ipod( track, local_filename, None) != 1:
            log( '(ipodsync) Could not add %s', episode.title)
        else:
            log( '(ipodsync) Added %s', episode.title)
        
        try:
            os.system('sync')
        except:
            pass

