

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
    import dbus
    # the following is taken from hal-device-manager source
    if getattr( dbus, 'version', (0,0,0)) >= (0,41,0):
        import dbus.glib
except:
    enable_ipod_functions = False

import os
import sys
import time

import libgpodder
import liblocaldb
import libpodcasts

import gobject

# do we provide iPod functions to the user?
def ipod_supported():
    global enable_ipod_functions
    return enable_ipod_functions



__ipodmanager = None

def iPodManagerSingleton():
    global __ipodmanager
    if __ipodmanager == None:
        __ipodmanager = iPodManager()
    
    return __ipodmanager



class gPodder_iPodSync(object):
    itdb = None
    ipod_mount = '' # mountpoint for ipod
    playlist_name = 'gpodder' # name of playlist to sync to
    pl_master = None
    pl_podcasts = None
    callback_progress = None
    callback_status = None
    callback_done = None
    ipod_mgr = None

    def __init__( self, callback_progress = None, callback_status = None, callback_done = None):
        if not ipod_supported():
            if libgpodder.isDebugging():
                print '(ipodsync) iPod functions not supported. (libgpod + eyed3 needed)'
        self.ipod_mgr = iPodManagerSingleton()
        self.ipod_mount = self.ipod_mgr.ipod.mount_point
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
        if self.ipod_mgr != None:
            if self.ipod_mgr.ipod != None:
                # there has to be a better way.. ;)
                # os.system( 'sudo eject %s' % ( self.ipod_mgr.ipod.device ))
                pass
        return True

    def remove_from_ipod( self, track, playlists):
        if not ipod_supported():
            return False
        if libgpodder.isDebugging():
           print '(ipodsync) REMOVING FROM IPOD!! track: %s' % track.title
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
                if libgpodder.isDebugging():
                    print "(ipodsync) found old playlist: %s" % (playlist.name)
                return playlist
        
        # if we arrive here: gpodder playlist not found!
        if libgpodder.isDebugging():
            print "creating new playlist: %s" % (playlistname)
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
                if libgpodder.isDebugging():
                    print '(ipodsync) Already on iPod: %s (from %s)' % (episode.title, track.title)
                return True
        
        return False

    def clean_playlist( self):
        if not ipod_supported():
            return False
        for track in gpod.sw_get_playlist_tracks( self.pl_podcasts):
            if libgpodder.isDebugging():
                print '(ipodsync) trying to remove track %s' % track.title
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
        # try to modify track to be more podcast-ish
        try:
            track.flag1 = 0x02
            track.flag2 = 0x01
            track.flag3 = 0x01
            track.flag4 = 0x01
        except:
            if libgpodder.isDebugging():
                print '(ipodsync) Seems like your python-gpod is out-of-date.'
        pass

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
        
        if libgpodder.isDebugging():
            print '(ipodsync) Adding item: %s from %s' % (episode.title, channel.title)
        local_filename = str(channel.getPodcastFilename( episode.url))
        try:
            eyed3_info = eyeD3.Mp3AudioFile( local_filename)
            track_length = eyed3_info.getPlayTime() * 1000 # in milliseconds
        except:
            if libgpodder.isDebugging():
                print '(ipodsync) Warning: cannot get length for %s, will use zero-length' % episode.title
            track_length = 0 # hmm.. better do something else?!
        
        track = gpod.itdb_track_new()
        
        if channel.is_music_channel:
            track.artist = str(channel.title)
        else:
            track.artist = 'gPodder podcast'
            self.set_podcast_flags( track)
        
        track.title = str(episode.title)
        track.album = str(channel.title)
        track.tracklen = track_length
        track.filetype = 'mp3' # huh?! harcoded?! well, well :) FIXME, i'd say
        track.description = str(episode.description)
        track.podcasturl = str(episode.url)
        track.podcastrss = str(channel.url)
        
        gpod.itdb_track_add( self.itdb, track, -1)
        playlist = self.get_playlist_for_channel( channel)
        gpod.itdb_playlist_add_track( playlist, track, -1)
        # if it's a music channel, also sync to master playlist
        if channel.is_music_channel:
            gpod.itdb_playlist_add_track( self.pl_master, track, -1)

        if gpod.itdb_cp_track_to_ipod( track, local_filename, None) != 1:
            if libgpodder.isDebugging():
                print '(ipodsync) could not add track: %s' % episode.title
        else:
            if libgpodder.isDebugging():
                print '(ipodsync) success for %s :)' % episode.title
        
        try:
            os.system('sync')
        except:
            # silently ignore :)
            pass


class iPod(object):
    __mountpoint = None
    
    def __init__( self, udi):
        self.is_connected = False
        self.device = None # /dev/sda
        self.children = []
        self.udi = udi
        if libgpodder.isDebugging():
            print '(iPod) new with udi: %s' % udi
    
    def has( self, udi):
        return udi in self.children

    def add( self, udi):
        if libgpodder.isDebugging():
            print '(iPod) adding: %s' % udi
        self.children.append( udi)

    def remove( self, udi):
        if libgpodder.isDebugging():
            print '(iPod) removing: %s' % udi
        self.children.remove( udi)

    def get_mount_point( self):
        return self.__mountpoint

    def set_mount_point( self, mount_point):
        if libgpodder.isDebugging():
            print '(iPod) mountpoint: %s' % mount_point
        self.__mountpoint = mount_point
        if self.__mountpoint[-1] != '/':
            self.__mountpoint = self.__mountpoint + '/'
    
    mount_point = property( fget = get_mount_point, fset = set_mount_point )

    def blowup( self):
        if libgpodder.isDebugging():
            print '(iPod) blown up!'


class iPodManager(object):
    mgr = 'org.freedesktop.Hal.Manager'
    mgr_path = '/org/freedesktop/Hal/Manager'
    
    service = 'org.freedesktop.Hal'
    interface = 'org.freedesktop.Hal.Device'
    
    ipod_key = 'portable_audio_player.storage_device'
    ipod_value = '/org/freedesktop/Hal/devices/storage_model_iPod'
    ipod_parent_key = 'info.parent'
    
    bus = None

    __ipod = None
    listeners = []
    
    def __init__( self):
        self.dbus_connect()
    
    def dbus_connect( self):
        self.bus = dbus.SystemBus()
        self.bus.add_signal_receiver( self.device_added, 'DeviceAdded', self.mgr, self.service, self.mgr_path)
        self.bus.add_signal_receiver( self.device_removed, 'DeviceRemoved', self.mgr, self.service, self.mgr_path)

    def device_added( self, udi):
        if libgpodder.isDebugging():
            print '(iPodManager) device_added: %s' % udi
        self.notify_me( udi)
        props = self.get_properties( udi)
        
        # add new iPod if connected
        if props.has_key( self.ipod_key):
            if props[self.ipod_key] == self.ipod_value:
                if libgpodder.isDebugging():
                    print '(iPodManager) received device_added'
                self.ipod = iPod( udi)
                self.ipod.device = props['block.device']
                self.notify_all()

        # iPod-related
        if self.ipod != None and props.has_key( self.ipod_parent_key) and props[self.ipod_parent_key] == self.ipod_value:
            self.ipod.add( udi)

    def notify_me( self, udi):
        callback = lambda *args: self.device_modified( udi, *args)
        self.bus.add_signal_receiver( callback, 'PropertyModified', self.interface, self.service, udi)

    def device_removed( self, udi):
        if libgpodder.isDebugging():
            print '(iPodManager) device_removed: %s' % udi
        # iPod-related
        if self.ipod != None and self.ipod.has( udi):
            self.ipod.remove( udi)
        if self.ipod != None and self.ipod.udi == udi:
            if libgpodder.isDebugging():
                print '(iPodManager) received device_removed'
            self.ipod.blowup()
            self.ipod = None
            self.notify_all()

    def device_modified( self, udi, num_changes, list):
        props = self.get_properties( udi)
        for item in list:
            key = item[0]
            if self.ipod != None:
                if key == 'volume.mount_point':
                    self.ipod.mount_point = props[key]
                    self.notify_all()
            
    def get_properties( self, udi):
        object = self.bus.get_object( self.service, udi)
        return object.GetAllProperties( dbus_interface = self.interface)

    def get_ipod( self):
        return self.__ipod

    def notify_all( self):
        for listener in self.listeners:
            listener( self.ipod)

    def set_ipod( self, ipod):
        self.__ipod = ipod

    ipod = property( fget = get_ipod, fset = set_ipod )

    def register( self, callback):
        if not callback in self.listeners:
            self.listeners.append( callback)
            callback( self.ipod)

    def unregister( self, callback):
        if callback in self.listeners:
            self.listeners.remove( callback)

