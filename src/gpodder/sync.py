# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2015 Thomas Perl and the gPodder Team
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
# Ported to gPodder 3 by Joseph Wickremasinghe in June 2012

import gpodder

from gpodder import util
from gpodder import services
from gpodder import download

import logging
logger = logging.getLogger(__name__)

import calendar

_ = gpodder.gettext

#
# TODO: Re-enable iPod and MTP sync support
#

pymtp_available = False
gpod_available = True
try:
    import gpod
except:
    gpod_available = False
    logger.warning('Could not find gpod')

#pymtp_available = True
#try:
#    import gpodder.gpopymtp as pymtp
#except:
#    pymtp_available = False
#    logger.warning('Could not load gpopymtp (libmtp not installed?).')

try:
    import eyed3.mp3
except:
    logger.warning('Could not find eyed3.mp3')

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
                    # logger.info('Creating subfolder %s in %s (id=%u)' % (parts[0], self.sep.join(prefix), folder_id))
                    tmpath = self.sep.join(prefix + [parts[0]])
                    self.folders[tmpath] = folder_id
                # logger.info(">>> %s = %s" % (tmpath, folder_id))
                del parts[0]
            # logger.info('MTP.mkdir: %s = %u' % (path, folder_id))
            return folder_id

def open_device(gui):
    config = gui._config
    device_type = gui._config.device_sync.device_type
    if device_type == 'ipod':
        return iPodDevice(config,
                gui.download_status_model,
                gui.download_queue_manager)
    elif device_type == 'filesystem':
        return MP3PlayerDevice(config,
                gui.download_status_model,
                gui.download_queue_manager)

    return None

def get_track_length(filename):
    if util.find_command('mplayer') is not None:
        try:
            mplayer_output = os.popen('mplayer -msglevel all=-1 -identify -vo null -ao null -frames 0 "%s" 2>/dev/null' % filename).read()
            return int(float(mplayer_output[mplayer_output.index('ID_LENGTH'):].splitlines()[0][10:])*1000)
        except:
            pass
    else:
        logger.info('Please install MPlayer for track length detection.')

    try:
        mp3file = eyed3.mp3.Mp3AudioFile(filename)
        return int(mp3file.info.time_secs * 1000)
    except Exception, e:
        logger.warn('Could not determine length: %s', filename, exc_info=True)

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
        self.playcount = 0
        self.podcast = None
        self.released = None

        # Convert keyword arguments to object attributes
        self.__dict__.update(kwargs)

    @property
    def playcount_str(self):
        return str(self.playcount)


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
        if self._config.device_sync.after_sync.sync_disks and not gpodder.ui.win32:
            os.system('sync')
        else:
            logger.warning('Not syncing disks. Unmount your device before unplugging.')
        return True

    def add_sync_tasks(self,tracklist, force_played=False, done_callback=None):
        for track in list(tracklist):
            # Filter tracks that are not meant to be synchronized
            does_not_exist = not track.was_downloaded(and_exists=True)
            exclude_played = (not track.is_new and
                    self._config.device_sync.skip_played_episodes)
            wrong_type = track.file_type() not in self.allowed_types

            if does_not_exist or exclude_played or wrong_type:
                logger.info('Excluding %s from sync', track.title)
                tracklist.remove(track)
        
        if tracklist:
            for track in sorted(tracklist, key=lambda e: e.pubdate_prop):
                if self.cancelled:
                    return False
    
                # XXX: need to check if track is added properly?
                sync_task=SyncTask(track)
    
                sync_task.status=sync_task.QUEUED
                sync_task.device=self
                self.download_status_model.register_task(sync_task)
                self.download_queue_manager.add_task(sync_task)
        else:
            logger.warning("No episodes to sync")

        if done_callback:
            done_callback()

        return True

    def remove_tracks(self, tracklist):
        for idx, track in enumerate(tracklist):
            if self.cancelled:
                return False
            self.notify('progress', idx, len(tracklist))
            self.remove_track(track)

        return True

    def get_all_tracks(self):
        pass

    def add_track(self, track, reporthook=None):
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
    def __init__(self, config,
            download_status_model,
            download_queue_manager):
        Device.__init__(self, config)

        self.mountpoint = self._config.device_sync.device_folder
        self.download_status_model = download_status_model
        self.download_queue_manager = download_queue_manager
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
                itunes_folder = os.path.join(self.mountpoint, 'iPod_Control', 'iTunes')
                ext_filename = os.path.join(itunes_folder, 'iTunesDB.ext')
                idb_filename = os.path.join(itunes_folder, 'iTunesDB')
                if os.path.exists(ext_filename) and os.path.exists(idb_filename):
                    try:
                        db = gpod.ipod.Database(self.mountpoint)
                        gpod.gtkpod.parse(ext_filename, db, idb_filename)
                        gpod.gtkpod.write(ext_filename, db, idb_filename)
                        db.close()
                    except:
                        logger.error('Error writing iTunesDB.ext')
                else:
                    logger.warning('Could not find %s or %s.',
                            ext_filename, idb_filename)

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
                        logger.info('Deleting episode from db %s', gtrack.title)
                        channel.delete_episode(episode)
                    else:
                        logger.info('Marking episode as played %s', gtrack.title)

    def purge(self):
        for track in gpod.sw_get_playlist_tracks(self.podcasts_playlist):
            if gpod.itdb_filename_on_ipod(track) is None:
                logger.info('Episode has no file: %s', track.title)
                # self.remove_track_gpod(track)
            elif track.playcount > 0  and not track.rating:
                logger.info('Purging episode: %s', track.title)
                self.remove_track_gpod(track)

    def get_all_tracks(self):
        tracks = []
        for track in gpod.sw_get_playlist_tracks(self.podcasts_playlist):
            filename = gpod.itdb_filename_on_ipod(track)

            if filename is None:
                # This can happen if the episode is deleted on the device
                logger.info('Episode has no file: %s', track.title)
                self.remove_track_gpod(track)
                continue

            length = util.calculate_size(filename)
            timestamp = util.file_modification_timestamp(filename)
            modified = util.format_date(timestamp)
            try:
                released = gpod.itdb_time_mac_to_host(track.time_released)
                released = util.format_date(released)
            except ValueError, ve:
                # timestamp out of range for platform time_t (bug 418)
                logger.info('Cannot convert track time: %s', ve)
                released = 0

            t = SyncTrack(track.title, length, modified,
                    modified_sort=timestamp,
                    libgpodtrack=track,
                    playcount=track.playcount,
                    released=released,
                    podcast=track.artist)
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
            logger.info('Track %s not in playlist', track.title)

        gpod.itdb_track_unlink(track)
        util.delete_file(filename)

    def add_track(self, episode,reporthook=None):
        self.notify('status', _('Adding %s') % episode.title)
        tracklist = gpod.sw_get_playlist_tracks(self.podcasts_playlist)
        podcasturls=[track.podcasturl for track in tracklist]

        if episode.url in podcasturls:
            # Mark as played on iPod if played locally (and set podcast flags)
            self.set_podcast_flags(tracklist[podcasturls.index(episode.url)], episode)
            return True

        original_filename = episode.local_filename(create=False)
        # The file has to exist, if we ought to transfer it, and therefore,
        # local_filename(create=False) must never return None as filename
        assert original_filename is not None
        local_filename = original_filename

        if util.calculate_size(original_filename) > self.get_free_space():
            logger.error('Not enough space on %s, sync aborted...', self.mountpoint)
            d = {'episode': episode.title, 'mountpoint': self.mountpoint}
            message =_('Error copying %(episode)s: Not enough free space on %(mountpoint)s')
            self.errors.append(message % d)
            self.cancelled = True
            return False

        local_filename = episode.local_filename(create=False)

        (fn, extension) = os.path.splitext(local_filename)
        if extension.lower().endswith('ogg'):
            logger.error('Cannot copy .ogg files to iPod.')
            return False

        track = gpod.itdb_track_new()

        # Add release time to track if episode.published has a valid value
        if episode.published > 0:
            try:
                # libgpod>= 0.5.x uses a new timestamp format
                track.time_released = gpod.itdb_time_host_to_mac(int(episode.published))
            except:
                # old (pre-0.5.x) libgpod versions expect mactime, so
                # we're going to manually build a good mactime timestamp here :)
                #
                # + 2082844800 for unixtime => mactime (1970 => 1904)
                track.time_released = int(episode.published + 2082844800)

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

        gpod.itdb_track_add(self.itdb, track, -1)
        gpod.itdb_playlist_add_track(self.master_playlist, track, -1)
        gpod.itdb_playlist_add_track(self.podcasts_playlist, track, -1)
        copied = gpod.itdb_cp_track_to_ipod(track, str(local_filename), None)
        reporthook(episode.file_size, 1, episode.file_size)

        # If the file has been converted, delete the temporary file here
        if local_filename != original_filename:
            util.delete_file(local_filename)

        return True

    def set_podcast_flags(self, track, episode):
        try:
            # Set several flags for to podcast values
            track.remember_playback_position = 0x01
            track.flag1 = 0x02
            track.flag2 = 0x01
            track.flag3 = 0x01
            track.flag4 = 0x01
        except:
            logger.warning('Seems like your python-gpod is out-of-date.')


class MP3PlayerDevice(Device):
    def __init__(self, config,
            download_status_model,
            download_queue_manager):
        Device.__init__(self, config)
        self.destination = util.sanitize_encoding(self._config.device_sync.device_folder)
        self.buffer_size = 1024*1024 # 1 MiB
        self.download_status_model = download_status_model
        self.download_queue_manager = download_queue_manager

    def get_free_space(self):
        return util.get_free_disk_space(self.destination)

    def open(self):
        Device.open(self)
        self.notify('status', _('Opening MP3 player'))

        if util.directory_is_writable(self.destination):
            self.notify('status', _('MP3 player opened'))
            self.tracks_list = self.get_all_tracks()
            return True

        return False

    def get_episode_folder_on_device(self, episode):
        if self._config.device_sync.one_folder_per_podcast:
            # Add channel title as subfolder
            folder = episode.channel.title
            # Clean up the folder name for use on limited devices
            folder = util.sanitize_filename(folder,
                self._config.device_sync.max_filename_length)
            folder = os.path.join(self.destination, folder)
        else:
            folder = self.destination

        return util.sanitize_encoding(folder)

    def get_episode_file_on_device(self, episode):
        # get the local file
        from_file = util.sanitize_encoding(episode.local_filename(create=False))
        # get the formated base name
        filename_base = util.sanitize_filename(episode.sync_filename(
            self._config.device_sync.custom_sync_name_enabled,
            self._config.device_sync.custom_sync_name),
            self._config.device_sync.max_filename_length)
        # add the file extension
        to_file = filename_base + os.path.splitext(from_file)[1].lower()

        # dirty workaround: on bad (empty) episode titles,
        # we simply use the from_file basename
        # (please, podcast authors, FIX YOUR RSS FEEDS!)
        if os.path.splitext(to_file)[0] == '':
            to_file = os.path.basename(from_file)

        return to_file

    def add_track(self, episode,reporthook=None):
        self.notify('status', _('Adding %s') % episode.title.decode('utf-8', 'ignore'))

        # get the folder on the device
        folder = self.get_episode_folder_on_device(episode)

        filename = episode.local_filename(create=False)
        # The file has to exist, if we ought to transfer it, and therefore,
        # local_filename(create=False) must never return None as filename
        assert filename is not None

        from_file = util.sanitize_encoding(filename)
        # get the filename that will be used on the device
        to_file = self.get_episode_file_on_device(episode)
        to_file = util.sanitize_encoding(os.path.join(folder, to_file))

        if not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except:
                logger.error('Cannot create folder on MP3 player: %s', folder)
                return False

        if not os.path.exists(to_file):
            logger.info('Copying %s => %s',
                    os.path.basename(from_file),
                    to_file.decode(util.encoding))
            self.copy_file_progress(from_file, to_file, reporthook)

        return True

    def copy_file_progress(self, from_file, to_file, reporthook=None):
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

        in_file.seek(0, os.SEEK_END)
        total_bytes = in_file.tell()
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
                    logger.info('Trying to remove partially copied file: %s' % to_file)
                    os.unlink( to_file)
                    logger.info('Yeah! Unlinked %s at least..' % to_file)
                except:
                    logger.error('Error while trying to unlink %s. OH MY!' % to_file)
                self.cancel()
                return False
            reporthook(bytes_read, 1, total_bytes)
            s = in_file.read(self.buffer_size)
        out_file.close()
        in_file.close()

        return True

    def get_all_tracks(self):
        tracks = []

        if self._config.one_folder_per_podcast:
            files = glob.glob(os.path.join(self.destination, '*', '*'))
        else:
            files = glob.glob(os.path.join(self.destination, '*'))

        for filename in files:
            (title, extension) = os.path.splitext(os.path.basename(filename))
            length = util.calculate_size(filename)

            timestamp = util.file_modification_timestamp(filename)
            modified = util.format_date(timestamp)
            if self._config.one_folder_per_podcast:
                podcast_name = os.path.basename(os.path.dirname(filename))
            else:
                podcast_name = None

            t = SyncTrack(title, length, modified,
                    modified_sort=timestamp,
                    filename=filename,
                    podcast=podcast_name)
            tracks.append(t)
        return tracks

    def episode_on_device(self, episode):
        e = util.sanitize_filename(episode.sync_filename(
            self._config.device_sync.custom_sync_name_enabled,
            self._config.device_sync.custom_sync_name),
            self._config.device_sync.max_filename_length)
        return self._track_on_device(e)

    def remove_track(self, track):
        self.notify('status', _('Removing %s') % track.title)
        util.delete_file(track.filename)
        directory = os.path.dirname(track.filename)
        if self.directory_is_empty(directory) and self._config.one_folder_per_podcast:
            try:
                os.rmdir(directory)
            except:
                logger.error('Cannot remove %s', directory)

    def directory_is_empty(self, directory):
        files = glob.glob(os.path.join(directory, '*'))
        dotfiles = glob.glob(os.path.join(directory, '.*'))
        return len(files+dotfiles) == 0

class MTPDevice(Device):
    def __init__(self, config):
        Device.__init__(self, config)
        self.__model_name = None
        try:
            self.__MTPDevice = MTP()
        except NameError, e:
            # pymtp not available / not installed (see bug 924)
            logger.error('pymtp not found: %s', str(e))
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
            logger.error('ERROR: An error has happend while trying to convert date to an mtp string')
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
                    logger.warning('WARNING: ignoring invalid time zone information for %s (%s)')
            return max( 0, _date )
        except Exception, exc:
            logger.warning('WARNING: the mtp date "%s" can not be parsed against mtp specification (%s)')
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
        logger.info("opening the MTP device")
        self.notify('status', _('Opening the MTP device'), )

        try:
            self.__MTPDevice.connect()
            # build the initial tracks_list
            self.tracks_list = self.get_all_tracks()
        except Exception, exc:
            logger.error('unable to find an MTP device (%s)')
            return False

        self.notify('status', _('%s opened') % self.get_name())
        return True

    def close(self):
        logger.info("closing %s", self.get_name())
        self.notify('status', _('Closing %s') % self.get_name())

        try:
            self.__MTPDevice.disconnect()
        except Exception, exc:
            logger.error('unable to close %s (%s)', self.get_name())
            return False

        self.notify('status', _('%s closed') % self.get_name())
        Device.close(self)
        return True

    def add_track(self, episode):
        self.notify('status', _('Adding %s...') % episode.title)
        filename = str(self.convert_track(episode))
        logger.info("sending %s (%s).", filename, episode.title)

        try:
            # verify free space
            needed = util.calculate_size(filename)
            free = self.get_free_space()
            if needed > free:
                logger.error('Not enough space on device %s: %s available, but need at least %s', self.get_name(), util.format_filesize(free), util.format_filesize(needed))
                self.cancelled = True
                return False

            # fill metadata
            metadata = pymtp.LIBMTP_Track()
            metadata.title = str(episode.title)
            metadata.artist = str(episode.channel.title)
            metadata.album = str(episode.channel.title)
            metadata.genre = "podcast"
            metadata.date = self.__date_to_mtp(episode.published)
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
            logger.error('unable to add episode %s', episode.title)
            return False

        return True

    def remove_track(self, sync_track):
        self.notify('status', _('Removing %s') % sync_track.mtptrack.title)
        logger.info("removing %s", sync_track.mtptrack.title)

        try:
            self.__MTPDevice.delete_object(sync_track.mtptrack.item_id)
        except Exception, exc:
            logger.error('unable remove file %s (%s)', sync_track.mtptrack.filename)

        logger.info('%s removed', sync_track.mtptrack.title)

    def get_all_tracks(self):
        try:
            listing = self.__MTPDevice.get_tracklisting(callback=self.__callback)
        except Exception, exc:
            logger.error('unable to get file listing %s (%s)')

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

class SyncCancelledException(Exception): pass

class SyncTask(download.DownloadTask):
    # An object representing the synchronization task of an episode

    # Possible states this sync task can be in
    STATUS_MESSAGE = (_('Added'), _('Queued'), _('Synchronizing'),
            _('Finished'), _('Failed'), _('Cancelled'), _('Paused'))
    (INIT, QUEUED, DOWNLOADING, DONE, FAILED, CANCELLED, PAUSED) = range(7)


    def __str__(self):
        return self.__episode.title

    def __get_status(self):
        return self.__status

    def __set_status(self, status):
        if status != self.__status:
            self.__status_changed = True
            self.__status = status

    status = property(fget=__get_status, fset=__set_status)

    def __get_device(self):
        return self.__device

    def __set_device(self, device):
        self.__device = device

    device = property(fget=__get_device, fset=__set_device)

    def __get_status_changed(self):
        if self.__status_changed:
            self.__status_changed = False
            return True
        else:
            return False

    status_changed = property(fget=__get_status_changed)

    def __get_activity(self):
        return self.__activity

    def __set_activity(self, activity):
        self.__activity = activity

    activity = property(fget=__get_activity, fset=__set_activity)

    def __get_empty_string(self):
        return ''

    url = property(fget=__get_empty_string)
    podcast_url = property(fget=__get_empty_string)

    def __get_episode(self):
        return self.__episode

    episode = property(fget=__get_episode)

    def cancel(self):
        if self.status in (self.DOWNLOADING, self.QUEUED):
            self.status = self.CANCELLED

    def removed_from_list(self):
        # XXX: Should we delete temporary/incomplete files here?
        pass

    def __init__(self, episode):
        self.__status = SyncTask.INIT
        self.__activity = SyncTask.ACTIVITY_SYNCHRONIZE
        self.__status_changed = True
        self.__episode = episode

        # Create the target filename and save it in the database
        self.filename = self.__episode.local_filename(create=False)
        self.tempname = self.filename + '.partial'

        self.total_size = self.__episode.file_size
        self.speed = 0.0
        self.progress = 0.0
        self.error_message = None

        # Have we already shown this task in a notification?
        self._notification_shown = False

        # Variables for speed limit and speed calculation
        self.__start_time = 0
        self.__start_blocks = 0
        self.__limit_rate_value = 999
        self.__limit_rate = 999

        # Callbacks
        self._progress_updated = lambda x: None

    def notify_as_finished(self):
        if self.status == SyncTask.DONE:
            if self._notification_shown:
                return False
            else:
                self._notification_shown = True
                return True

        return False

    def notify_as_failed(self):
        if self.status == SyncTask.FAILED:
            if self._notification_shown:
                return False
            else:
                self._notification_shown = True
                return True

        return False

    def add_progress_callback(self, callback):
        self._progress_updated = callback

    def status_updated(self, count, blockSize, totalSize):
        # We see a different "total size" while downloading,
        # so correct the total size variable in the thread
        if totalSize != self.total_size and totalSize > 0:
            self.total_size = float(totalSize)

        if self.total_size > 0:
            self.progress = max(0.0, min(1.0, float(count*blockSize)/self.total_size))
            self._progress_updated(self.progress)

        if self.status == SyncTask.CANCELLED:
            raise SyncCancelledException()

        if self.status == SyncTask.PAUSED:
            raise SyncCancelledException()

    def recycle(self):
        self.episode.download_task = None

    def run(self):
        # Speed calculation (re-)starts here
        self.__start_time = 0
        self.__start_blocks = 0

        # If the download has already been cancelled, skip it
        if self.status == SyncTask.CANCELLED:
            util.delete_file(self.tempname)
            self.progress = 0.0
            self.speed = 0.0
            return False

        # We only start this download if its status is "queued"
        if self.status != SyncTask.QUEUED:
            return False

        # We are synching this file right now
        self.status = SyncTask.DOWNLOADING
        self._notification_shown = False

        try:
            logger.info('Starting SyncTask')
            self.device.add_track(self.episode, reporthook=self.status_updated)
        except Exception, e:
            self.status = SyncTask.FAILED
            logger.error('Download failed: %s', str(e), exc_info=True)
            self.error_message = _('Error: %s') % (str(e),)

        if self.status == SyncTask.DOWNLOADING:
            # Everything went well - we're done
            self.status = SyncTask.DONE
            if self.total_size <= 0:
                self.total_size = util.calculate_size(self.filename)
                logger.info('Total size updated to %d', self.total_size)
            self.progress = 1.0
            gpodder.user_extensions.on_episode_synced(self.device, self.__episode)
            return True

        self.speed = 0.0

        # We finished, but not successfully (at least not really)
        return False

