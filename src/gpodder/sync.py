# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2018 The gPodder Team
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

import calendar
import glob
import logging
import os.path
import time
from urllib.parse import urlparse

import gpodder
from gpodder import download, services, util
import gi  # isort:skip
gi.require_version('Gtk', '3.0')  # isort:skip
from gi.repository import GLib, Gio, Gtk  # isort:skip


logger = logging.getLogger(__name__)


_ = gpodder.gettext

gpod_available = True
try:
    import gpod
except:
    gpod_available = False

mplayer_available = True if util.find_command('mplayer') is not None else False

eyed3mp3_available = True
try:
    import eyed3.mp3
except:
    eyed3mp3_available = False


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
                gui.download_queue_manager,
                gui.mount_volume_for_file)

    return None


def get_track_length(filename):
    attempted = False

    if mplayer_available:
        try:
            mplayer_output = os.popen('mplayer -msglevel all=-1 -identify -vo null -ao null -frames 0 "%s" 2>/dev/null' % filename).read()
            return int(float(mplayer_output[mplayer_output.index('ID_LENGTH'):].splitlines()[0][10:]) * 1000)
        except Exception:
            logger.error('MPlayer could not determine length: %s', filename, exc_info=True)
            attempted = True

    if eyd3mp3_available:
        try:
            length = int(eyed3.mp3.Mp3AudioFile(filename).info.time_secs * 1000)
            # Notify user on eyed3 success if mplayer failed.
            # A warning is used to make it visible in gpo or on console.
            if attempted:
                logger.warn('eyed3.mp3 successfully determined length: %s', filename)
            return length
        except Exception:
            logger.error('eyed3.mp3 could not determine length: %s', filename, exc_info=True)
            attempted = True

    if not attempted:
        logger.warn('Could not determine length: %s', filename)
        logger.warn('Please install MPlayer or the eyed3.mp3 module for track length detection.')

    return int(60 * 60 * 1000 * 3)
    # Default is three hours (to be on the safe side)


def episode_filename_on_device(config, episode):
    """
    :param gpodder.config.Config config: configuration (for sync options)
    :param gpodder.model.PodcastEpisode episode: episode to get filename for
    :return str: basename minus extension to use to save episode on device
    """
    # get the local file
    from_file = episode.local_filename(create=False)
    # get the formated base name
    filename_base = util.sanitize_filename(episode.sync_filename(
        config.device_sync.custom_sync_name_enabled,
        config.device_sync.custom_sync_name),
        config.device_sync.max_filename_length)
    # add the file extension
    to_file = filename_base + os.path.splitext(from_file)[1].lower()

    # dirty workaround: on bad (empty) episode titles,
    # we simply use the from_file basename
    # (please, podcast authors, FIX YOUR RSS FEEDS!)
    if os.path.splitext(to_file)[0] == '':
        to_file = os.path.basename(from_file)
    return to_file


def episode_foldername_on_device(config, episode):
    """
    :param gpodder.config.Config config: configuration (for sync options)
    :param gpodder.model.PodcastEpisode episode: episode to get folder name for
    :return str: folder name to save episode to on device
    """
    if config.device_sync.one_folder_per_podcast:
        # Add channel title as subfolder
        folder = episode.channel.title
        # Clean up the folder name for use on limited devices
        folder = util.sanitize_filename(folder, config.device_sync.max_filename_length)
    else:
        folder = None
    return folder


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

    def add_sync_tasks(self, tracklist, force_played=False, done_callback=None):
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
                    break

                # XXX: need to check if track is added properly?
                sync_task = SyncTask(track)

                sync_task.status = sync_task.QUEUED
                sync_task.device = self
                # New Task, we must wait on the GTK Loop
                self.download_status_model.register_task(sync_task)
                # Executes after task has been registered
                util.idle_add(self.download_queue_manager.queue_task, sync_task)
        else:
            logger.warning("No episodes to sync")

        if done_callback:
            done_callback()

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
        RESERVED_FOR_ITDB = 1024 * 1024 * 10
        result = util.get_free_disk_space(self.mountpoint)
        if result == -1:
            # Can't get free disk space
            return -1
        return result - RESERVED_FOR_ITDB

    def open(self):
        Device.open(self)
        if not gpod_available:
            logger.error('Please install the gpod module to sync with an iPod device.')
            return False
        if not os.path.isdir(self.mountpoint):
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
            elif track.playcount > 0 and not track.rating:
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
            except ValueError as ve:
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

    def add_track(self, episode, reporthook=None):
        self.notify('status', _('Adding %s') % episode.title)
        tracklist = gpod.sw_get_playlist_tracks(self.podcasts_playlist)
        podcasturls = [track.podcasturl for track in tracklist]

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
            message = _('Error copying %(episode)s: Not enough free space on %(mountpoint)s')
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
            download_queue_manager,
            mount_volume_for_file):
        Device.__init__(self, config)

        folder = self._config.device_sync.device_folder
        self.destination = util.new_gio_file(folder)
        self.mount_volume_for_file = mount_volume_for_file
        self.download_status_model = download_status_model
        self.download_queue_manager = download_queue_manager

    def get_free_space(self):
        info = self.destination.query_filesystem_info(Gio.FILE_ATTRIBUTE_FILESYSTEM_FREE, None)
        return info.get_attribute_uint64(Gio.FILE_ATTRIBUTE_FILESYSTEM_FREE)

    def open(self):
        Device.open(self)
        self.notify('status', _('Opening MP3 player'))

        if not self.mount_volume_for_file(self.destination):
            return False

        try:
            info = self.destination.query_info(
                Gio.FILE_ATTRIBUTE_ACCESS_CAN_WRITE + "," +
                Gio.FILE_ATTRIBUTE_STANDARD_TYPE,
                Gio.FileQueryInfoFlags.NONE,
                None)
        except GLib.Error as err:
            logger.error('querying destination info for %s failed with %s',
                self.destination.get_uri(), err.message)
            return False

        # open is ok if the target is a directory, and it can be written to
        # for smb, query_info doesn't return FILE_ATTRIBUTE_ACCESS_CAN_WRITE,
        # -- if that's the case, just assume that it's writable
        if (info.get_file_type() == Gio.FileType.DIRECTORY and (
            not info.has_attribute(Gio.FILE_ATTRIBUTE_ACCESS_CAN_WRITE) or
                info.get_attribute_boolean(Gio.FILE_ATTRIBUTE_ACCESS_CAN_WRITE))):
            self.notify('status', _('MP3 player opened'))
            self.tracks_list = self.get_all_tracks()
            return True

        return False

    def get_episode_folder_on_device(self, episode):
        folder = episode_foldername_on_device(self._config, episode)
        if folder:
            folder = self.destination.get_child(folder)
        else:
            folder = self.destination

        return folder

    def get_episode_file_on_device(self, episode):
        return episode_filename_on_device(self._config, episode)

    def add_track(self, episode, reporthook=None):
        self.notify('status', _('Adding %s') % episode.title)

        # get the folder on the device
        folder = self.get_episode_folder_on_device(episode)

        filename = episode.local_filename(create=False)
        # The file has to exist, if we ought to transfer it, and therefore,
        # local_filename(create=False) must never return None as filename
        assert filename is not None

        from_file = filename

        # verify free space
        needed = util.calculate_size(from_file)
        free = self.get_free_space()
        if free == -1:
            logger.warn('Cannot determine free disk space on device')
        elif needed > free:
            d = {'path': self.destination, 'free': util.format_filesize(free), 'need': util.format_filesize(needed)}
            message = _('Not enough space in %(path)s: %(free)s available, but need at least %(need)s')
            raise SyncFailedException(message % d)

        # get the filename that will be used on the device
        to_file = self.get_episode_file_on_device(episode)
        to_file = folder.get_child(to_file)

        util.make_directory(folder)

        if not to_file.query_exists():
            logger.info('Copying %s => %s',
                    os.path.basename(from_file),
                    to_file.get_uri())
            from_file = Gio.File.new_for_path(from_file)
            try:
                hookconvert = lambda current_bytes, total_bytes, user_data : reporthook(current_bytes, 1, total_bytes)
                from_file.copy(to_file, Gio.FileCopyFlags.OVERWRITE, None, hookconvert, None)
            except GLib.Error as err:
                logger.error('Error copying %s to %s: %s', from_file.get_uri(), to_file.get_uri(), err.message)
                d = {'from_file': from_file.get_uri(), 'to_file': to_file.get_uri(), 'message': err.message}
                self.errors.append(_('Error copying %(from_file)s to %(to_file)s: %(message)s') % d)
                return False

        return True

    def add_sync_track(self, tracks, file, info, podcast_name):
        (title, extension) = os.path.splitext(info.get_name())
        timestamp = info.get_modification_time()
        modified = util.format_date(timestamp.tv_sec)

        t = SyncTrack(title, info.get_size(), modified,
                modified_sort=timestamp,
                filename=file.get_uri(),
                podcast=podcast_name)
        tracks.append(t)

    def get_all_tracks(self):
        tracks = []

        attributes = (
            Gio.FILE_ATTRIBUTE_STANDARD_NAME + "," +
            Gio.FILE_ATTRIBUTE_STANDARD_TYPE + "," +
            Gio.FILE_ATTRIBUTE_STANDARD_SIZE + "," +
            Gio.FILE_ATTRIBUTE_TIME_MODIFIED)

        root_path = self.destination
        for path_info in root_path.enumerate_children(attributes, Gio.FileQueryInfoFlags.NONE, None):
            if self._config.one_folder_per_podcast:
                if path_info.get_file_type() == Gio.FileType.DIRECTORY:
                    path_file = root_path.get_child(path_info.get_name())
                    for child_info in path_file.enumerate_children(attributes, Gio.FileQueryInfoFlags.NONE, None):
                        if child_info.get_file_type() == Gio.FileType.REGULAR:
                            child_file = path_file.get_child(child_info.get_name())
                            self.add_sync_track(tracks, child_file, child_info, path_info.get_name())

            else:
                if path_info.get_file_type() == Gio.FileTypeFlags.REGULAR:
                    path_file = root_path.get_child(path_info.get_name())
                    self.add_sync_track(tracks, path_file, path_info, None)
        return tracks

    def episode_on_device(self, episode):
        e = util.sanitize_filename(episode.sync_filename(
            self._config.device_sync.custom_sync_name_enabled,
            self._config.device_sync.custom_sync_name),
            self._config.device_sync.max_filename_length)
        return self._track_on_device(e)

    def remove_track(self, track):
        self.notify('status', _('Removing %s') % track.title)

        # get the folder on the device
        file = Gio.File.new_for_uri(track.filename)
        folder = file.get_parent()
        if file.query_exists():
            try:
                file.delete()
            except GLib.Error as err:
                # if the file went away don't worry about it
                if not err.matches(Gio.io_error_quark(), Gio.IOErrorEnum.NOT_FOUND):
                    logger.error('deleting file %s failed: %s', file.get_uri(), err.message)
                return

        if self._config.one_folder_per_podcast:
            try:
                if self.directory_is_empty(folder):
                    folder.delete()
            except GLib.Error as err:
                # if the folder went away don't worry about it (multiple threads could
                # make this happen if they both notice the folder is empty simultaneously)
                if not err.matches(Gio.io_error_quark(), Gio.IOErrorEnum.NOT_FOUND):
                    logger.error('deleting folder %s failed: %s', folder.get_uri(), err.message)

    def directory_is_empty(self, directory):
        for child in directory.enumerate_children(Gio.FILE_ATTRIBUTE_STANDARD_NAME, Gio.FileQueryInfoFlags.NONE, None):
            return False
        return True


class SyncCancelledException(Exception): pass


class SyncFailedException(Exception): pass


class SyncTask(download.DownloadTask):
    # An object representing the synchronization task of an episode

    # Possible states this sync task can be in
    STATUS_MESSAGE = (_('Added'), _('Queued'), _('Synchronizing'),
            _('Finished'), _('Failed'), _('Cancelled'), _('Paused'))
    (INIT, QUEUED, DOWNLOADING, DONE, FAILED, CANCELLED, PAUSED) = list(range(7))

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
            self.progress = max(0.0, min(1.0, (count * blockSize) / self.total_size))
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

        # We only start this download if its status is "downloading"
        if self.status != SyncTask.DOWNLOADING:
            return False

        # We are synching this file right now
        self.status = SyncTask.DOWNLOADING
        self._notification_shown = False

        try:
            logger.info('Starting SyncTask')
            self.device.add_track(self.episode, reporthook=self.status_updated)
        except Exception as e:
            self.status = SyncTask.FAILED
            logger.error('Sync failed: %s', str(e), exc_info=True)
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
