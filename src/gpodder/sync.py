# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (C) 2005-2007 Thomas Perl <thp at perli.net>
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


from gpodder import util
from gpodder import services
from gpodder import libgpodder
from gpodder import libconverter
from gpodder import libtagupdate

from gpodder.liblogger import log

try:
    import gpod
except:
    log('(gpodder.sync) Could not find gpod')

try:
    import mad
except:
    log('(gpodder.sync) Could not find pymad')

try:
    import eyeD3
except:
    log( '(gpodder.sync) Could not find eyeD3')


import os
import os.path
import glob
import shutil
import sys
import time
import string
import email.Utils
import re


def open_device():
    gl = libgpodder.gPodderLib()
    device_type = gl.config.device_type
    if device_type == 'ipod':
        return iPodDevice()
    elif device_type == 'filesystem':
        return MP3PlayerDevice()
    else:
        return None

def get_track_length(filename):
    if util.find_command('mplayer') is not None:
        try:
            mplayer_output = os.popen('mplayer -msglevel all=-1 -identify -vo null -ao null -frames 0 "%s" 2>/dev/null' % filename).read()
            return int(float(mplayer_output[mplayer_output.index('ID_LENGTH'):].splitlines()[0][10:])*1000)
        except:
            pass
    else:
        log('Please install MPlayer for track length detection.')

    try:
        mad_info = mad.MadFile(filename)
        return int(mad_info.total_time())
    except:
        pass
    
    try:
        eyed3_info = eyeD3.Mp3AudioFile(filename)
        return int(eyed3_info.getPlayTime()*1000)
    except:
        pass

    return int(60*60*1000*3) # Default is three hours (to be on the safe side)


class SyncTrack(object):
    def __init__(self, title, length, modified, **kwargs):
        self.title = title
        self.length = length
        gl = libgpodder.gPodderLib()
        self.filesize = util.format_filesize(length, gl.config.use_si_units)
        self.modified = modified
        self.__dict__.update(kwargs)


class Device(services.ObservableService):
    def __init__(self):
        self.cancelled = False
        self.allowed_types = ['audio', 'video']

        signals = ['progress', 'sub-progress', 'status', 'done']
        services.ObservableService.__init__(self, signals)

    def open(self):
        pass

    def cancel(self):
        self.cancelled = True
        self.notify('status', _('Cancelled by user'))

    def close(self):
        self.notify('status', _('Writing data to disk'))
        os.system('sync')
        self.notify('done')
        return True

    def add_tracks(self, tracklist=[], force_played=False):
        gl = libgpodder.gPodderLib()
        for id, track in enumerate(tracklist):
            if self.cancelled:
                return False

            self.notify('progress', id+1, len(tracklist))

            if not track.is_downloaded():
                continue

            if track.is_played() and gl.config.only_sync_not_played and not force_played:
                continue

            if track.file_type() not in self.allowed_types:
                continue

            if gl.config.on_sync_mark_played:
                log('Marking as played on transfer: %s', track.url, sender=self)
                gl.history_mark_played(track.url)

            added = self.add_track(track)

            if added and gl.config.on_sync_delete:
                log('Removing episode after transfer: %s', track.url, sender=self)
                track.delete_from_disk()
        return True

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


class iPodDevice(Device):
    def __init__(self):
        Device.__init__(self)

        gl = libgpodder.gPodderLib()
        self.mountpoint = str(gl.config.ipod_mount)

        self.itdb = None
        self.podcast_playlist = None

    def open(self):
        if not os.path.isdir(self.mountpoint):
            return False

        self.notify('status', _('Opening iPod database'))
        self.itdb = gpod.itdb_parse(self.mountpoint, None)
        if self.itdb is None:
            return False

        self.itdb.mountpoint = self.mountpoint
        self.podcasts_playlist = gpod.itdb_playlist_podcasts(self.itdb)

        if self.podcasts_playlist:
            self.notify('status', _('iPod opened'))
            return True
        else:
            return False

    def close(self):
        if self.itdb is not None:
            self.notify('status', _('Saving iPod database'))
            gpod.itdb_write(self.itdb, None)
            self.itdb = None
        Device.close(self)
        return True

    def get_all_tracks(self):
        tracks = []
        gl = libgpodder.gPodderLib()
        for track in gpod.sw_get_playlist_tracks(self.podcasts_playlist):
            filename = gpod.itdb_filename_on_ipod(track)
            length = util.calculate_size(filename)

            age_in_days = util.file_age_in_days(filename)
            modified = util.file_age_to_string(age_in_days)

            t = SyncTrack(track.title, length, modified, libgpodtrack=track)
            tracks.append(t)
        return tracks

    def remove_track(self, track):
        self.notify('status', _('Removing %s') % track.title)
        track = track.libgpodtrack
        filename = gpod.itdb_filename_on_ipod(track)

        try:
            gpod.itdb_playlist_remove_track(self.podcasts_playlist, track)
        except:
            log('Track %s not in playlist', track.title, sender=self)

        gpod.itdb_track_unlink(track)
        util.delete_file(filename)

    def add_track(self, episode):
        self.notify('status', _('Adding %s') % episode.title)
        gl = libgpodder.gPodderLib()
        for track in gpod.sw_get_playlist_tracks(self.podcasts_playlist):
            if episode.url == track.podcasturl:
                if track.playcount > 0:
                    gl.history_mark_played(track.podcasturl)
                # Mark as played on iPod if played locally (and set podcast flags)
                self.set_podcast_flags(track)
                return True

        original_filename = str(episode.local_filename())
        local_filename = original_filename

        # Reserve 10 MiB for iTunesDB writing (to be on the safe side)
        RESERVED_FOR_ITDB = 1024*1024*10
        space_for_track = util.get_free_disk_space(self.mountpoint) - RESERVED_FOR_ITDB
        needed = util.calculate_size(local_filename)

        if needed > space_for_track:
            log('Not enough space on %s: %s available, but need at least %s', self.mountpoint, util.format_filesize(space_for_track), util.format_filesize(needed), sender = self)
            self.errors.append( _('Error copying %s: Not enough free disk space on %s') % (episode.title, self.mountpoint))
            self.cancelled = True
            return False

        (fn, extension) = os.path.splitext(original_filename)
        if libconverter.converters.has_converter(extension):
            log('Converting: %s', original_filename, sender=self)
            callback_status = lambda percentage: self.notify('sub-progress', int(percentage))
            local_filename = libconverter.converters.convert(original_filename, callback=callback_status)

            if not libtagupdate.update_metadata_on_file(local_filename, title=episode.title, artist=episode.channel.title):
                log('Could not set metadata on converted file %s', local_filename, sender=self)

            if local_filename is None:
                log('Cannot convert %s', original_filename, sender=self)
                return False
            else:
                local_filename = str(local_filename)

        (fn, extension) = os.path.splitext(local_filename)
        if extension.lower().endswith('ogg'):
            log('Cannot copy .ogg files to iPod.', sender=self)
            return False

        track = gpod.itdb_track_new()
        
        # Add release time to track if pubDate is parseable
        ipod_date = email.Utils.parsedate(episode.pubDate)
        if ipod_date is not None:
            try:
                # libgpod>= 0.5.x uses a new timestamp format
                track.time_released = gpod.itdb_time_host_to_mac(int(time.mktime(ipod_date)))
            except:
                # old (pre-0.5.x) libgpod versions expect mactime, so
                # we're going to manually build a good mactime timestamp here :)
                #
                # + 2082844800 for unixtime => mactime (1970 => 1904)
                track.time_released = int(time.mktime(ipod_date) + 2082844800)
        
        track.title = str(episode.title)
        track.album = str(episode.channel.title)
        track.artist = str(episode.channel.title)
        track.description = str(episode.description)

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

        self.set_podcast_flags(track)
        self.set_cover_art(track, local_filename)

        gpod.itdb_track_add(self.itdb, track, -1)
        gpod.itdb_playlist_add_track(self.podcasts_playlist, track, -1)
        gpod.itdb_cp_track_to_ipod( track, local_filename, None)

        # If the file has been converted, delete the temporary file here
        if local_filename != original_filename:
            util.delete_file(local_filename)

        return True

    def set_podcast_flags(self, track):
        try:
            # Set blue bullet for unplayed tracks on 5G iPods
            gl = libgpodder.gPodderLib()
            if gl.history_is_played(track.podcasturl):
                track.mark_unplayed = 0x01
                if track.playcount == 0:
                    track.playcount = 1
            else:
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
            cover_filename = os.path.join(os.path.dirname(local_filename), 'cover')
            if os.path.isfile(cover_filename):
                gpod.itdb_track_set_thumbnails(track, cover_filename)
                return True
        except:
            log('Error getting cover using channel cover', sender=self)

        return False


class MP3PlayerDevice(Device):
    def __init__(self):
        Device.__init__(self)

        # Try to detect OS encoding (by Leonid Ponomarev)
        if 'LANG' in os.environ and '.' in os.environ['LANG']:
            lang = os.environ['LANG']
            (language, encoding) = lang.rsplit('.', 1)
            log('Detected encoding: %s', encoding, sender=self)
            self.enc = encoding
        else:
            # Using iso-8859-15 here as (hopefully) sane default
            # see http://en.wikipedia.org/wiki/ISO/IEC_8859-1
            log('Using ISO-8859-15 as encoding. If this', sender=self)
            log('is incorrect, please set your $LANG variable.', sender=self)
            self.enc = 'iso-8859-15'

        gl = libgpodder.gPodderLib()
        self.destination = gl.config.mp3_player_folder
        self.buffer_size = 1024*1024 # 1 MiB

    def open(self):
        self.notify('status', _('Opening MP3 player'))
        if util.directory_is_writable(self.destination):
            self.notify('status', _('MP3 player opened'))
            return True
        else:
            return False
    
    def add_track(self, episode):
        self.notify('status', _('Adding %s') % episode.title)
        gl = libgpodder.gPodderLib()

        if gl.config.fssync_channel_subfolders:
            # Add channel title as subfolder
            folder = episode.channel.title
            folder = re.sub('[/|?*<>:+\[\]\"\\\]', '_', folder.encode(self.enc, 'ignore'))
            folder = os.path.join(self.destination, folder)
        else:
            folder = self.destination

        from_file = episode.local_filename()

        filename_base = episode.sync_filename()

        # don't allow extremely long file names: cut the
        # filename at 50 chars (to make FAT-based drives happy)
        if len(filename_base) > 50:
            filename_base = filename_base[:50]

        to_file = filename_base + os.path.splitext(from_file)[1].lower()

        # Encode the file name to our system's
        # encoding and remove the characters that are invalid
        # for FAT-based drives (replace with the empty string)
        to_file = re.sub('[/|?*<>:+\[\]\"\\\]', '_', to_file.encode(self.enc, 'ignore'))

        # dirty workaround: on bad (empty) episode titles,
        # we simply use the from_file basename
        # (please, podcast authors, FIX YOUR RSS FEEDS!)
        if os.path.splitext(to_file)[0] == '':
            to_file = os.path.basename(from_file)

        to_file = os.path.join(folder, to_file)

        if not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except:
                log('Cannot create folder on MP3 player: %s', folder, sender=self)
                return False

        if not os.path.exists(to_file):
            log('Copying %s => %s', os.path.basename(from_file), to_file.decode(self.enc), sender=self)
            return self.copy_file_progress(from_file, to_file)

        return True

    def copy_file_progress(self, from_file, to_file):
        try:
            out_file = open(to_file, 'wb')
        except IOError, ioerror:
            self.errors.append(_('Error opening %s: %s') % (ioerror.filename, ioerror.strerror))
            self.cancel()
            return False

        try:
            in_file = open(from_file, 'rb')
        except IOError, ioerror:
            self.errors.append(_('Error opening %s: %s') % (ioerror.filename, ioerror.strerror))
            self.cancel()
            return False

        in_file.seek(0, 2)
        bytes = in_file.tell()
        in_file.seek(0)

        bytes_read = 0
        s = in_file.read(self.buffer_size)
        bytes_read += len(s)
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
            self.notify('sub-progress', int(max(100, 100*float(bytes_read)/float(bytes))))
            s = in_file.read(self.buffer_size)
        out_file.close()
        in_file.close()

        return True
    
    def get_all_tracks(self):
        tracks = []
        gl = libgpodder.gPodderLib()

        if gl.config.fssync_channel_subfolders:
            files = glob.glob(os.path.join(self.destination, '*', '*'))
        else:
            files = glob.glob(os.path.join(self.destination, '*'))

        for filename in files:
            (title, extension) = os.path.splitext(os.path.basename(filename))
            length = util.calculate_size(filename)
         
            age_in_days = util.file_age_in_days(filename)
            modified = util.file_age_to_string(age_in_days)
         
            t = SyncTrack(title, length, modified, filename=filename)
            tracks.append(t)
        return tracks

    def remove_track(self, track):
        self.notify('status', _('Removing %s') % track.title)
        util.delete_file(track.filename)
        directory = os.path.dirname(track.filename)
        gl = libgpodder.gPodderLib()
        if self.directory_is_empty(directory) and gl.config.fssync_channel_subfolders:
            try:
                os.rmdir(directory)
            except:
                log('Cannot remove %s', directory, sender=self)

    def directory_is_empty(self, directory):
        files = glob.glob(os.path.join(directory, '*'))
        dotfiles = glob.glob(os.path.join(directory, '.*'))
        return len(files+dotfiles) == 0

