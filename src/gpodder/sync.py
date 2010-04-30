# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2010 Thomas Perl and the gPodder Team
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


# sync.py -- Device synchronization
# Thomas Perl <thp@perli.net> 2007-12-06
# based on libipodsync.py (2006-04-05 Thomas Perl)

import gpodder

from gpodder import util
from gpodder import services
from gpodder import libconverter
from gpodder import gstreamer

from gpodder.liblogger import log

import time
import calendar

_ = gpodder.gettext

gpod_available = True
try:
    import gpod
except:
    gpod_available = False
    log('(gpodder.sync) Could not find gpod')

pymtp_available = True
try:
    import pymtp
except:
    pymtp_available = False
    log('(gpodder.sync) Could not find pymtp.')

try:
    import eyeD3
except:
    log( '(gpodder.sync) Could not find eyeD3')

try:
    import Image
except:
    log('(gpodder.sync) Could not find Python Imaging Library (PIL)')

# Register our dependencies for the synchronization module
services.dependency_manager.depend_on(_('iPod synchronization'), _('Support synchronization of podcasts to Apple iPod devices via libgpod.'), ['gpod', 'gst'], [])
services.dependency_manager.depend_on(_('MTP device synchronization'), _('Support synchronization of podcasts to devices using the Media Transfer Protocol via pymtp.'), ['pymtp'], [])
services.dependency_manager.depend_on(_('iPod OGG converter'), _('Convert OGG podcasts to MP3 files on synchronization to iPods using oggdec and LAME.'), [], ['oggdec', 'lame'])
services.dependency_manager.depend_on(_('iPod video podcasts'), _('Detect video lengths via MPlayer, to synchronize video podcasts to iPods.'), [], ['mplayer'])
services.dependency_manager.depend_on(_('Rockbox cover art support'), _('Copy podcast cover art to filesystem-based MP3 players running Rockbox.org firmware. Needs Python Imaging.'), ['Image'], [])

import os
import os.path
import glob
import time

if pymtp_available:
    class MTP(pymtp.MTP):
        sep = os.path.sep

        def __init__(self):
            pymtp.MTP.__init__(self)
            self.folders = {}

        def connect(self):
            pymtp.MTP.connect(self)
            self.folders = self.unfold(self.mtp.LIBMTP_Get_Folder_List(self.device))

        def get_folder_list(self):
            return self.folders

        def unfold(self, folder, path=''):
            result = {}
            while folder:
                folder = folder.contents
                name = self.sep.join([path, folder.name]).lstrip(self.sep)
                result[name] = folder.folder_id
                if folder.child:
                    result.update(self.unfold(folder.child, name))
                folder = folder.sibling
            return result

        def mkdir(self, path):
            folder_id = 0
            prefix = []
            parts = path.split(self.sep)
            while parts:
                prefix.append(parts[0])
                tmpath = self.sep.join(prefix)
                if self.folders.has_key(tmpath):
                    folder_id = self.folders[tmpath]
                else:
                    folder_id = self.create_folder(parts[0], parent=folder_id)
                    # log('Creating subfolder %s in %s (id=%u)' % (parts[0], self.sep.join(prefix), folder_id))
                    tmpath = self.sep.join(prefix + [parts[0]])
                    self.folders[tmpath] = folder_id
                # log(">>> %s = %s" % (tmpath, folder_id))
                del parts[0]
            # log('MTP.mkdir: %s = %u' % (path, folder_id))
            return folder_id

def open_device(config):
    device_type = config.device_type
    if device_type == 'ipod':
        return iPodDevice(config)
    elif device_type == 'filesystem':
        return MP3PlayerDevice(config)
    elif device_type == 'mtp':
        return MTPDevice(config)
    else:
        return None

def get_track_length(filename):
    length = gstreamer.get_track_length(filename)
    if length is not None:
        return length

    if util.find_command('mplayer') is not None:
        try:
            mplayer_output = os.popen('mplayer -msglevel all=-1 -identify -vo null -ao null -frames 0 "%s" 2>/dev/null' % filename).read()
            return int(float(mplayer_output[mplayer_output.index('ID_LENGTH'):].splitlines()[0][10:])*1000)
        except:
            pass
    else:
        log('Please install MPlayer for track length detection.')

    try:
        eyed3_info = eyeD3.Mp3AudioFile(filename)
        return int(eyed3_info.getPlayTime()*1000)
    except:
        pass

    return int(60*60*1000*3) # Default is three hours (to be on the safe side)

class SyncTrack(object):
    """
    This represents a track that is on a device. You need
    to specify at least the following keyword arguments, 
    because these will be used to display the track in the
    GUI. All other keyword arguments are optional and can
    be used to reference internal objects, etc... See the
    iPod synchronization code for examples.

    Keyword arguments needed:
        playcount (How often has the track been played?)
        podcast (Which podcast is this track from? Or: Folder name)
        released (The release date of the episode)

    If any of these fields is unknown, it should not be
    passed to the function (the values will default to None
    for all required fields).
    """
    def __init__(self, title, length, modified, **kwargs):
        self.title = title
        self.length = length
        self.filesize = util.format_filesize(length)
        self.modified = modified

        # Set some (possible) keyword arguments to default values
        self.playcount = None
        self.podcast = None
        self.released = None

        # Convert keyword arguments to object attributes
        self.__dict__.update(kwargs)


class Device(services.ObservableService):
    def __init__(self, config):
        self._config = config
        self.cancelled = False
        self.allowed_types = ['audio', 'video']
        self.errors = []
        self.tracks_list = []
        signals = ['progress', 'sub-progress', 'status', 'done', 'post-done']
        services.ObservableService.__init__(self, signals)

    def open(self):
        pass

    def cancel(self):
        self.cancelled = True
        self.notify('status', _('Cancelled by user'))

    def close(self):
        self.notify('status', _('Writing data to disk'))
        if self._config.sync_disks_after_transfer and not gpodder.win32:
            successful_sync = (os.system('sync') == 0)
        else:
            log('Not syncing disks. Unmount your device before unplugging.', sender=self)
            successful_sync = True
        self.notify('done')
        self.notify('post-done', self, successful_sync)
        return True

    def add_tracks(self, tracklist=[], force_played=False):
        for track in list(tracklist):
            # Filter tracks that are not meant to be synchronized
            does_not_exist = not track.was_downloaded(and_exists=True)
            exclude_played = track.is_played and not force_played and \
                    self._config.only_sync_not_played
            wrong_type = track.file_type() not in self.allowed_types

            if does_not_exist or exclude_played or wrong_type:
                log('Excluding %s from sync', track.title, sender=self)
                tracklist.remove(track)

        for id, track in enumerate(sorted(tracklist, key=lambda e: e.pubDate)):
            if self.cancelled:
                return False

            self.notify('progress', id+1, len(tracklist))

            added = self.add_track(track)

            if self._config.on_sync_mark_played:
                log('Marking as played on transfer: %s', track.url, sender=self)
                track.mark(is_played=True)

            if added and self._config.on_sync_delete and not track.is_locked:
                log('Removing episode after transfer: %s', track.url, sender=self)
                track.delete_from_disk()
        return True

    def convert_track(self, episode):
        filename = episode.local_filename(create=False)
        # The file has to exist, if we ought to transfer it, and therefore,
        # local_filename(create=False) must never return None as filename
        assert filename is not None
        (fn, extension) = os.path.splitext(filename)
        if libconverter.converters.has_converter(extension):
            if self._config.disable_pre_sync_conversion:
                log('Pre-sync conversion is not enabled, set disable_pre_sync_conversion to "False" to enable')
                return filename

            log('Converting: %s', filename, sender=self)
            callback_status = lambda percentage: self.notify('sub-progress', int(percentage))
            local_filename = libconverter.converters.convert(filename, callback=callback_status)

            if local_filename is None:
                log('Cannot convert %s', filename, sender=self)
                return filename

            return str(local_filename)

        return filename

    def remove_tracks(self, tracklist=[]):
        for id, track in enumerate(tracklist):
            if self.cancelled:
                return False
            self.notify('progress', id, len(tracklist))
            self.remove_track(track)
        return True

    def get_all_tracks(self):
        pass

    def add_track(self, track):
        pass

    def remove_track(self, track):
        pass

    def get_free_space(self):
        pass

    def episode_on_device(self, episode):
        return self._track_on_device(episode.title)

    def _track_on_device(self, track_name):
        for t in self.tracks_list:
            title = t.title
            if track_name == title:
                return t
        return None

class iPodDevice(Device):
    def __init__(self, config):
        Device.__init__(self, config)

        self.mountpoint = str(self._config.ipod_mount)

        self.itdb = None
        self.podcast_playlist = None
        

    def get_free_space(self):
        # Reserve 10 MiB for iTunesDB writing (to be on the safe side)
        RESERVED_FOR_ITDB = 1024*1024*10
        return util.get_free_disk_space(self.mountpoint) - RESERVED_FOR_ITDB

    def open(self):
        Device.open(self)
        if not gpod_available or not os.path.isdir(self.mountpoint):
            return False

        self.notify('status', _('Opening iPod database'))
        self.itdb = gpod.itdb_parse(self.mountpoint, None)
        if self.itdb is None:
            return False

        self.itdb.mountpoint = self.mountpoint
        self.podcasts_playlist = gpod.itdb_playlist_podcasts(self.itdb)
        self.master_playlist = gpod.itdb_playlist_mpl(self.itdb)

        if self.podcasts_playlist:
            self.notify('status', _('iPod opened'))

            # build the initial tracks_list
            self.tracks_list = self.get_all_tracks()

            return True
        else:
            return False

    def close(self):
        if self.itdb is not None:
            self.notify('status', _('Saving iPod database'))
            gpod.itdb_write(self.itdb, None)
            self.itdb = None
            
            if self._config.ipod_write_gtkpod_extended:
                self.notify('status', _('Writing extended gtkpod database'))
                ext_filename = os.path.join(self.mountpoint, 'iPod_Control', 'iTunes', 'iTunesDB.ext')
                idb_filename = os.path.join(self.mountpoint, 'iPod_Control', 'iTunes', 'iTunesDB')
                if os.path.exists(ext_filename) and os.path.exists(idb_filename):
                    try:
                        db = gpod.ipod.Database(self.mountpoint)
                        gpod.gtkpod.parse(ext_filename, db, idb_filename)
                        gpod.gtkpod.write(ext_filename, db, idb_filename)
                        db.close()
                    except:
                        log('Error when writing iTunesDB.ext', sender=self, traceback=True)
                else:
                    log('I could not find %s or %s. Will not update extended gtkpod DB.', ext_filename, idb_filename, sender=self)
            else:
                log('Not writing extended gtkpod DB. Set "ipod_write_gpod_extended" to True if I should write it.', sender=self)            
            
            
        Device.close(self)
        return True

    def update_played_or_delete(self, channel, episodes, delete_from_db):
        """
        Check whether episodes on ipod are played and update as played
        and delete if required.
        """
        for episode in episodes:
            track = self.episode_on_device(episode)
            if track:
                gtrack = track.libgpodtrack
                if gtrack.playcount > 0:
                    if delete_from_db and not gtrack.rating:
                        log('Deleting episode from db %s', gtrack.title, sender=self)
                        channel.delete_episode(episode)
                    else:
                        log('Marking episode as played %s', gtrack.title, sender=self)
                        episode.mark(is_played=True)

    def purge(self):
        for track in gpod.sw_get_playlist_tracks(self.podcasts_playlist):
            if gpod.itdb_filename_on_ipod(track) is None:
                log('Episode has no file: %s', track.title, sender=self)
                # self.remove_track_gpod(track)
            elif track.playcount > 0  and not track.rating:
                log('Purging episode: %s', track.title, sender=self)
                self.remove_track_gpod(track)

    def get_all_tracks(self):
        tracks = []
        for track in gpod.sw_get_playlist_tracks(self.podcasts_playlist):
            filename = gpod.itdb_filename_on_ipod(track)

            if filename is None:
                # This can happen if the episode is deleted on the device
                log('Episode has no file: %s', track.title, sender=self)
                self.remove_track_gpod(track)
                continue

            length = util.calculate_size(filename)
            timestamp = util.file_modification_timestamp(filename)
            modified = util.format_date(timestamp)
            released = gpod.itdb_time_mac_to_host(track.time_released)
            released = util.format_date(released)

            t = SyncTrack(track.title, length, modified, modified_sort=timestamp, libgpodtrack=track, playcount=track.playcount, released=released, podcast=track.artist)
            tracks.append(t)
        return tracks        

    def remove_track(self, track):
        self.notify('status', _('Removing %s') % track.title)
        self.remove_track_gpod(track.libgpodtrack)

    def remove_track_gpod(self, track):
        filename = gpod.itdb_filename_on_ipod(track)

        try:
            gpod.itdb_playlist_remove_track(self.podcasts_playlist, track)
        except:
            log('Track %s not in playlist', track.title, sender=self)

        gpod.itdb_track_unlink(track)
        util.delete_file(filename)

    def add_track(self, episode):
        self.notify('status', _('Adding %s') % episode.title)
        for track in gpod.sw_get_playlist_tracks(self.podcasts_playlist):
            if episode.url == track.podcasturl:
                if track.playcount > 0:
                    episode.mark(is_played=True)
                # Mark as played on iPod if played locally (and set podcast flags)
                self.set_podcast_flags(track, episode)
                return True

        original_filename = episode.local_filename(create=False)
        # The file has to exist, if we ought to transfer it, and therefore,
        # local_filename(create=False) must never return None as filename
        assert original_filename is not None
        local_filename = original_filename

        if util.calculate_size(original_filename) > self.get_free_space():
            log('Not enough space on %s, sync aborted...', self.mountpoint, sender = self)
            d = {'episode': episode.title, 'mountpoint': self.mountpoint}
            message =_('Error copying %(episode)s: Not enough free space on %(mountpoint)s')
            self.errors.append(message % d)
            self.cancelled = True
            return False

        local_filename = self.convert_track(episode)

        (fn, extension) = os.path.splitext(local_filename)
        if extension.lower().endswith('ogg'):
            log('Cannot copy .ogg files to iPod.', sender=self)
            return False

        track = gpod.itdb_track_new()
        
        # Add release time to track if pubDate has a valid value
        if episode.pubDate > 0:
            try:
                # libgpod>= 0.5.x uses a new timestamp format
                track.time_released = gpod.itdb_time_host_to_mac(int(episode.pubDate))
            except:
                # old (pre-0.5.x) libgpod versions expect mactime, so
                # we're going to manually build a good mactime timestamp here :)
                #
                # + 2082844800 for unixtime => mactime (1970 => 1904)
                track.time_released = int(episode.pubDate + 2082844800)
        
        track.title = str(episode.title)
        track.album = str(episode.channel.title)
        track.artist = str(episode.channel.title)
        track.description = str(util.remove_html_tags(episode.description))

        track.podcasturl = str(episode.url)
        track.podcastrss = str(episode.channel.url)

        track.tracklen = get_track_length(local_filename)
        track.size = os.path.getsize(local_filename)

        if episode.file_type() == 'audio':
            track.filetype = 'mp3'
            track.mediatype = 0x00000004
        elif episode.file_type() == 'video':
            track.filetype = 'm4v'
            track.mediatype = 0x00000006

        self.set_podcast_flags(track, episode)
        self.set_cover_art(track, local_filename)

        gpod.itdb_track_add(self.itdb, track, -1)
        gpod.itdb_playlist_add_track(self.master_playlist, track, -1)
        gpod.itdb_playlist_add_track(self.podcasts_playlist, track, -1)
        copied = gpod.itdb_cp_track_to_ipod(track, str(local_filename), None)

        if copied and gpodder.user_hooks is not None:
            gpodder.user_hooks.on_file_copied_to_ipod(self, local_filename)

        # If the file has been converted, delete the temporary file here
        if local_filename != original_filename:
            util.delete_file(local_filename)

        return True

    def set_podcast_flags(self, track, episode):
        try:
            # Set blue bullet for unplayed tracks on 5G iPods
            if episode.is_played:
                track.mark_unplayed = 0x01
                if track.playcount == 0:
                    track.playcount = 1
            else:
                if track.playcount > 0 or track.bookmark_time > 0:
                    #track is partially played so no blue bullet
                    track.mark_unplayed = 0x01
                else:
                    #totally unplayed
                    track.mark_unplayed = 0x02

            # Set several flags for to podcast values
            track.remember_playback_position = 0x01
            track.flag1 = 0x02
            track.flag2 = 0x01
            track.flag3 = 0x01
            track.flag4 = 0x01
        except:
            log('Seems like your python-gpod is out-of-date.', sender=self)
    
    def set_cover_art(self, track, local_filename):
        try:
            tag = eyeD3.Tag()
            if tag.link(local_filename):
                if 'APIC' in tag.frames and len(tag.frames['APIC']) > 0:
                    apic = tag.frames['APIC'][0]

                    extension = 'jpg'
                    if apic.mimeType == 'image/png':
                        extension = 'png'
                    cover_filename = '%s.cover.%s' (local_filename, extension)

                    cover_file = open(cover_filename, 'w')
                    cover_file.write(apic.imageData)
                    cover_file.close()

                    gpod.itdb_track_set_thumbnails(track, cover_filename)
                    return True
        except:
            log('Error getting cover using eyeD3', sender=self)

        try:
            cover_filename = os.path.join(os.path.dirname(local_filename), 'folder.jpg')

            if os.path.isfile(cover_filename):
                gpod.itdb_track_set_thumbnails(track, cover_filename)
                return True
        except:
            log('Error getting cover using channel cover', sender=self)

        return False


class MP3PlayerDevice(Device):
    # if different players use other filenames besides
    # .scrobbler.log, add them to this list
    scrobbler_log_filenames = ['.scrobbler.log']

    def __init__(self, config):
        Device.__init__(self, config)
        self.destination = self._config.mp3_player_folder
        self.buffer_size = 1024*1024 # 1 MiB
        self.scrobbler_log = []

    def get_free_space(self):
        return util.get_free_disk_space(self.destination)

    def open(self):
        Device.open(self)
        self.notify('status', _('Opening MP3 player'))
        if util.directory_is_writable(self.destination):
            self.notify('status', _('MP3 player opened'))
            # build the initial tracks_list
            self.tracks_list = self.get_all_tracks()
            if self._config.mp3_player_use_scrobbler_log:
                mp3_player_mount_point = util.find_mount_point(self.destination)
                # If a moint point cannot be found look inside self.destination for scrobbler_log_filenames
                # this prevents us from os.walk()'ing the entire / filesystem
                if mp3_player_mount_point == '/':
                    mp3_player_mount_point = self.destination
                log_location = self.find_scrobbler_log(mp3_player_mount_point)
                if log_location is not None and self.load_audioscrobbler_log(log_location):
                    log('Using Audioscrobbler log data to mark tracks as played', sender=self)
            return True
        else:
            return False

    def add_track(self, episode):
        self.notify('status', _('Adding %s') % episode.title.decode('utf-8', 'ignore'))

        if self._config.fssync_channel_subfolders:
            # Add channel title as subfolder
            folder = episode.channel.title
            # Clean up the folder name for use on limited devices
            folder = util.sanitize_filename(folder, self._config.mp3_player_max_filename_length)
            folder = os.path.join(self.destination, folder)
        else:
            folder = self.destination

        folder = util.sanitize_encoding(folder)

        from_file = util.sanitize_encoding(self.convert_track(episode))
        filename_base = util.sanitize_filename(episode.sync_filename(self._config.custom_sync_name_enabled, self._config.custom_sync_name), self._config.mp3_player_max_filename_length)

        to_file = filename_base + os.path.splitext(from_file)[1].lower()

        # dirty workaround: on bad (empty) episode titles,
        # we simply use the from_file basename
        # (please, podcast authors, FIX YOUR RSS FEEDS!)
        if os.path.splitext(to_file)[0] == '':
            to_file = os.path.basename(from_file)

        to_file = util.sanitize_encoding(os.path.join(folder, to_file))

        if not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except:
                log('Cannot create folder on MP3 player: %s', folder, sender=self)
                return False

        if self._config.mp3_player_use_scrobbler_log and not episode.is_played:
            # FIXME: This misses some things when channel.title<>album tag which is what
            # the scrobbling entity will be using.
            if [episode.channel.title, episode.title] in self.scrobbler_log:
                log('Marking "%s" from "%s" as played', episode.title, episode.channel.title, sender=self)
                episode.mark(is_played=True)

        if self._config.rockbox_copy_coverart and not os.path.exists(os.path.join(folder, 'cover.bmp')):
            log('Creating Rockbox album art for "%s"', episode.channel.title, sender=self)
            self.copy_player_cover_art(folder, from_file, \
            'cover.bmp', 'BMP', self._config.rockbox_coverart_size)

        if self._config.custom_player_copy_coverart \
        and not os.path.exists(os.path.join(folder, \
        self._config.custom_player_coverart_name)):
            log('Creating custom player album art for "%s"',
                episode.channel.title, sender=self)
            self.copy_player_cover_art(folder, from_file, \
            self._config.custom_player_coverart_name, \
            self._config.custom_player_coverart_format, \
            self._config.custom_player_coverart_size)

        if not os.path.exists(to_file):
            log('Copying %s => %s', os.path.basename(from_file), to_file.decode(util.encoding), sender=self)
            copied = self.copy_file_progress(from_file, to_file)
            if copied and gpodder.user_hooks is not None:
                gpodder.user_hooks.on_file_copied_to_filesystem(self, from_file, to_file)
            return copied

        return True

    def copy_file_progress(self, from_file, to_file):
        try:
            out_file = open(to_file, 'wb')
        except IOError, ioerror:
            d = {'filename': ioerror.filename, 'message': ioerror.strerror}
            self.errors.append(_('Error opening %(filename)s: %(message)s') % d)
            self.cancel()
            return False

        try:
            in_file = open(from_file, 'rb')
        except IOError, ioerror:
            d = {'filename': ioerror.filename, 'message': ioerror.strerror}
            self.errors.append(_('Error opening %(filename)s: %(message)s') % d)
            self.cancel()
            return False

        in_file.seek(0, 2)
        bytes = in_file.tell()
        in_file.seek(0)

        bytes_read = 0
        s = in_file.read(self.buffer_size)
        while s:
            bytes_read += len(s)
            try:
                out_file.write(s)
            except IOError, ioerror:
                self.errors.append(ioerror.strerror)
                try:
                    out_file.close()
                except:
                    pass
                try:
                    log('Trying to remove partially copied file: %s' % to_file, sender=self)
                    os.unlink( to_file)
                    log('Yeah! Unlinked %s at least..' % to_file, sender=self)
                except:
                    log('Error while trying to unlink %s. OH MY!' % to_file, sender=self)
                self.cancel()
                return False
            self.notify('sub-progress', int(min(100, 100*float(bytes_read)/float(bytes))))
            s = in_file.read(self.buffer_size)
        out_file.close()
        in_file.close()

        return True
    
    def get_all_tracks(self):
        tracks = []

        if self._config.fssync_channel_subfolders:
            files = glob.glob(os.path.join(self.destination, '*', '*'))
        else:
            files = glob.glob(os.path.join(self.destination, '*'))

        for filename in files:
            (title, extension) = os.path.splitext(os.path.basename(filename))
            length = util.calculate_size(filename)

            timestamp = util.file_modification_timestamp(filename)
            modified = util.format_date(timestamp)
            if self._config.fssync_channel_subfolders:
                podcast_name = os.path.basename(os.path.dirname(filename))
            else:
                podcast_name = None

            t = SyncTrack(title, length, modified, modified_sort=timestamp, filename=filename, podcast=podcast_name)
            tracks.append(t)
        return tracks

    def episode_on_device(self, episode):
        e = util.sanitize_filename(episode.sync_filename(self._config.custom_sync_name_enabled, self._config.custom_sync_name), self._config.mp3_player_max_filename_length)
        return self._track_on_device(e)

    def remove_track(self, track):
        self.notify('status', _('Removing %s') % track.title)
        util.delete_file(track.filename)
        directory = os.path.dirname(track.filename)
        if self.directory_is_empty(directory) and self._config.fssync_channel_subfolders:
            try:
                os.rmdir(directory)
            except:
                log('Cannot remove %s', directory, sender=self)

    def directory_is_empty(self, directory):
        files = glob.glob(os.path.join(directory, '*'))
        dotfiles = glob.glob(os.path.join(directory, '.*'))
        return len(files+dotfiles) == 0

    def find_scrobbler_log(self, mount_point):
        """ find an audioscrobbler log file from log_filenames in the mount_point dir """
        for dirpath, dirnames, filenames in os.walk(mount_point):
            for log_file in self.scrobbler_log_filenames:
                filename = os.path.join(dirpath, log_file)
                if os.path.isfile(filename):
                    return filename

        # No scrobbler log on that device
        return None

    def copy_player_cover_art(self, destination, local_filename, \
                                  cover_dst_name, cover_dst_format, \
                                  cover_dst_size):
        """
        Try to copy the channel cover to the podcast folder on the MP3
        player. This makes the player, e.g. Rockbox (rockbox.org), display the
        cover art in its interface.

        You need the Python Imaging Library (PIL) installed to be able to
        convert the cover file to a Bitmap file, which Rockbox needs.
        """
        try:
            cover_loc = os.path.join(os.path.dirname(local_filename), 'folder.jpg')
            cover_dst = os.path.join(destination, cover_dst_name)
            if os.path.isfile(cover_loc):
                log('Creating cover art file on player', sender=self)
                log('Cover art size is %s', cover_dst_size, sender=self)
                size = (cover_dst_size, cover_dst_size)
                try:
                    cover = Image.open(cover_loc)
                    cover.thumbnail(size)
                    cover.save(cover_dst, cover_dst_format)
                except IOError:
                    log('Cannot create %s (PIL?)', cover_dst, traceback=True, sender=self)
                return True
            else:
                log('No cover available to set as player cover', sender=self)
                return True
        except:
            log('Error getting cover using channel cover', sender=self)
        return False


    def load_audioscrobbler_log(self, log_file):
        """ Retrive track title and artist info for all the entries
            in an audioscrobbler portable player format logfile
            http://www.audioscrobbler.net/wiki/Portable_Player_Logging """
        try:
            log('Opening "%s" as AudioScrobbler log.', log_file, sender=self)
            f = open(log_file, 'r')
            entries = f.readlines()
            f.close()
        except IOError, ioerror:
            log('Error: "%s" cannot be read.', log_file, sender=self)
            return False

        try:
            # Scrobble Log Format: http://www.audioscrobbler.net/wiki/Portable_Player_Logging
            # Notably some fields are optional so will appear as \t\t.
            # Conforming scrobblers should strip any \t's from the actual fields.
            for entry in entries:
                entry = entry.split('\t')
                if len(entry)>=5:
                    artist, album, track, pos, length, rating = entry[:6]
                    # L means at least 50% of the track was listened to (S means < 50%)
                    if 'L' in rating:
                        # Whatever is writing the logs will only have the taginfo in the
                        # file to work from. Mostly album~=channel name
                        if len(track):
                            self.scrobbler_log.append([album, track])
                        else:
                            log('Skipping logging of %s (missing track)', album)
                else:
                    log('Skipping scrobbler entry: %d elements %s', len(entry), entry)
                    
        except:
            log('Error while parsing "%s".', log_file, sender=self)

        return True

class MTPDevice(Device):
    def __init__(self, config):
        Device.__init__(self, config)
        self.__model_name = None
        try:
            self.__MTPDevice = MTP()
        except NameError, e:
            # pymtp not available / not installed (see bug 924)
            log('pymtp not found: %s', str(e), sender=self)
            self.__MTPDevice = None

    def __callback(self, sent, total):
        if self.cancelled:
            return -1
        percentage = round(float(sent)/float(total)*100)
        text = ('%i%%' % percentage)
        self.notify('progress', sent, total, text)

    def __date_to_mtp(self, date):
        """
        this function format the given date and time to a string representation
        according to MTP specifications: YYYYMMDDThhmmss.s

        return
            the string representation od the given date
        """
        if not date:
            return ""
        try:
            d = time.gmtime(date)
            return time.strftime("%Y%m%d-%H%M%S.0Z", d)
        except Exception, exc:
            log('ERROR: An error has happend while trying to convert date to an mtp string (%s)', exc, sender=self)
            return None

    def __mtp_to_date(self, mtp):
        """
        this parse the mtp's string representation for date
        according to specifications (YYYYMMDDThhmmss.s) to
        a python time object

        """
        if not mtp:
            return None

        try:
            mtp = mtp.replace(" ", "0") # replace blank with 0 to fix some invalid string
            d = time.strptime(mtp[:8] + mtp[9:13],"%Y%m%d%H%M%S")
            _date = calendar.timegm(d)
            if len(mtp)==20:
                # TIME ZONE SHIFTING: the string contains a hour/min shift relative to a time zone
                try:
                    shift_direction=mtp[15]
                    hour_shift = int(mtp[16:18])
                    minute_shift = int(mtp[18:20])
                    shift_in_sec = hour_shift * 3600 + minute_shift * 60
                    if shift_direction == "+":
                        _date += shift_in_sec
                    elif shift_direction == "-":
                        _date -= shift_in_sec
                    else:
                        raise ValueError("Expected + or -")
                except Exception, exc:
                    log('WARNING: ignoring invalid time zone information for %s (%s)', mtp, exc, sender=self)
            return max( 0, _date )
        except Exception, exc:
            log('WARNING: the mtp date "%s" can not be parsed against mtp specification (%s)', mtp, exc, sender=self)
            return None

    def get_name(self):
        """
        this function try to find a nice name for the device.
        First, it tries to find a friendly (user assigned) name
        (this name can be set by other application and is stored on the device).
        if no friendly name was assign, it tries to get the model name (given by the vendor).
        If no name is found at all, a generic one is returned.

        Once found, the name is cached internaly to prevent reading again the device

        return
            the name of the device
        """

        if self.__model_name:
            return self.__model_name

        if self.__MTPDevice is None:
            return _('MTP device')

        self.__model_name = self.__MTPDevice.get_devicename() # actually libmtp.Get_Friendlyname
        if not self.__model_name or self.__model_name == "?????":
            self.__model_name = self.__MTPDevice.get_modelname()
        if not self.__model_name:
            self.__model_name = _('MTP device')

        return self.__model_name

    def open(self):
        Device.open(self)
        log("opening the MTP device", sender=self)
        self.notify('status', _('Opening the MTP device'), )

        try:
            self.__MTPDevice.connect()
            # build the initial tracks_list
            self.tracks_list = self.get_all_tracks()
        except Exception, exc:
            log('unable to find an MTP device (%s)', exc, sender=self, traceback=True)
            return False

        self.notify('status', _('%s opened') % self.get_name())
        return True

    def close(self):
        log("closing %s", self.get_name(), sender=self)
        self.notify('status', _('Closing %s') % self.get_name())

        try:
            self.__MTPDevice.disconnect()
        except Exception, exc:
            log('unable to close %s (%s)', self.get_name(), exc, sender=self)
            return False

        self.notify('status', _('%s closed') % self.get_name())
        Device.close(self)
        return True

    def add_track(self, episode):
        self.notify('status', _('Adding %s...') % episode.title)
        filename = str(self.convert_track(episode))
        log("sending " + filename + " (" + episode.title + ").", sender=self)

        try:
            # verify free space
            needed = util.calculate_size(filename)
            free = self.get_free_space()
            if needed > free:
                log('Not enough space on device %s: %s available, but need at least %s', self.get_name(), util.format_filesize(free), util.format_filesize(needed), sender=self)
                self.cancelled = True
                return False

            # fill metadata
            metadata = pymtp.LIBMTP_Track()
            metadata.title = str(episode.title)
            metadata.artist = str(episode.channel.title)
            metadata.album = str(episode.channel.title)
            metadata.genre = "podcast"
            metadata.date = self.__date_to_mtp(episode.pubDate)
            metadata.duration = get_track_length(str(filename))

            folder_name = ''
            if episode.mimetype.startswith('audio/') and self._config.mtp_audio_folder:
                folder_name = self._config.mtp_audio_folder
            if episode.mimetype.startswith('video/') and self._config.mtp_video_folder:
                folder_name = self._config.mtp_video_folder
            if episode.mimetype.startswith('image/') and self._config.mtp_image_folder:
                folder_name = self._config.mtp_image_folder

            if folder_name != '' and self._config.mtp_podcast_folders:
                folder_name += os.path.sep + str(episode.channel.title)

            # log('Target MTP folder: %s' % folder_name)

            if folder_name == '':
                folder_id = 0
            else:
                folder_id = self.__MTPDevice.mkdir(folder_name)

            # send the file
            to_file = util.sanitize_filename(metadata.title) + episode.extension()
            self.__MTPDevice.send_track_from_file(filename, to_file,
                    metadata, folder_id, callback=self.__callback)
            if gpodder.user_hooks is not None:
                gpodder.user_hooks.on_file_copied_to_mtp(self, filename, to_file)
        except:
            log('unable to add episode %s', episode.title, sender=self, traceback=True)
            return False

        return True

    def remove_track(self, sync_track):
        self.notify('status', _('Removing %s') % sync_track.mtptrack.title)
        log("removing %s", sync_track.mtptrack.title, sender=self)

        try:
            self.__MTPDevice.delete_object(sync_track.mtptrack.item_id)
        except Exception, exc:
            log('unable remove file %s (%s)', sync_track.mtptrack.filename, exc, sender=self)

        log('%s removed', sync_track.mtptrack.title , sender=self)

    def get_all_tracks(self):
        try:
            listing = self.__MTPDevice.get_tracklisting(callback=self.__callback)
        except Exception, exc:
            log('unable to get file listing %s (%s)', exc, sender=self)

        tracks = []
        for track in listing:
            title = track.title
            if not title or title=="": title=track.filename
            if len(title) > 50: title = title[0:49] + '...'
            artist = track.artist
            if artist and len(artist) > 50: artist = artist[0:49] + '...'
            length = track.filesize
            age_in_days = 0
            date = self.__mtp_to_date(track.date)
            if not date:
                modified = track.date # not a valid mtp date. Display what mtp gave anyway
                modified_sort = -1 # no idea how to sort invalid date
            else:
                modified = util.format_date(date)
                modified_sort = date

            t = SyncTrack(title, length, modified, modified_sort=modified_sort, mtptrack=track, podcast=artist)
            tracks.append(t)
        return tracks

    def get_free_space(self):
        if self.__MTPDevice is not None:
            return self.__MTPDevice.get_freespace()
        else:
            return 0

