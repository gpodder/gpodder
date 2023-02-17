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

# gpodder.gtkui.desktop.sync - Glue code between GTK+ UI and sync module
# Thomas Perl <thp@gpodder.org>; 2009-09-05 (based on code from gui.py)
# Ported to gPodder 3 by Joseph Wickremasinghe in June 2012

import logging

import gpodder
from gpodder import sync, util
from gpodder.deviceplaylist import gPodderDevicePlaylist

_ = gpodder.gettext


logger = logging.getLogger(__name__)


class gPodderSyncUI(object):
    # download list states
    (DL_ONEOFF, DL_ADDING_TASKS, DL_ADDED_TASKS) = list(range(3))

    def __init__(self, config, notification, parent_window,
                 show_confirmation,
                 show_preferences,
                 channels,
                 download_status_model,
                 download_queue_manager,
                 set_download_list_state,
                 commit_changes_to_database,
                 delete_episode_list,
                 select_episodes_to_delete,
                 mount_volume_for_file):
        self.device = None

        self._config = config
        self.notification = notification
        self.parent_window = parent_window
        self.show_confirmation = show_confirmation

        self.show_preferences = show_preferences
        self.channels = channels
        self.download_status_model = download_status_model
        self.download_queue_manager = download_queue_manager
        self.set_download_list_state = set_download_list_state
        self.commit_changes_to_database = commit_changes_to_database
        self.delete_episode_list = delete_episode_list
        self.select_episodes_to_delete = select_episodes_to_delete
        self.mount_volume_for_file = mount_volume_for_file

    def _filter_sync_episodes(self, channels, only_downloaded=False):
        """Return a list of episodes for device synchronization

        If only_downloaded is True, this will skip episodes that
        have not been downloaded yet and podcasts that are marked
        as "Do not synchronize to my device".
        """
        episodes = []
        for channel in channels:
            if only_downloaded or not channel.sync_to_mp3_player:
                logger.info('Skipping channel: %s', channel.title)
                continue

            for episode in channel.get_all_episodes():
                if (episode.was_downloaded(and_exists=True)
                        or not only_downloaded):
                    episodes.append(episode)
        return episodes

    def _show_message_unconfigured(self):
        title = _('No device configured')
        message = _('Please set up your device in the preferences dialog.')
        if self.show_confirmation(message, title):
            self.show_preferences(self.parent_window, None)

    def _show_message_cannot_open(self):
        title = _('Cannot open device')
        message = _('Please check logs and the settings in the preferences dialog.')
        self.notification(message, title, important=True)

    def on_synchronize_episodes(self, channels, episodes=None, force_played=True, done_callback=None):
        device = sync.open_device(self)

        if device is None:
            self._show_message_unconfigured()
            if done_callback:
                done_callback()
            return

        try:
            if not device.open():
                self._show_message_cannot_open()
                if done_callback:
                    done_callback()
                return
            else:
                # Only set if device is configured and opened successfully
                self.device = device
        except Exception as err:
            logger.error('opening destination %s failed with %s',
                device.destination.get_uri(), err.message)
            self._show_message_cannot_open()
            if done_callback:
                done_callback()
            return

        if episodes is None:
            force_played = False
            episodes = self._filter_sync_episodes(channels)

        def check_free_space():
            # "Will we add this episode to the device?"
            def will_add(episode):
                # If already on-device, it won't take up any space
                if device.episode_on_device(episode):
                    return False

                # Might not be synced if it's played already
                if (not force_played
                        and self._config.device_sync.skip_played_episodes):
                    return False

                # In all other cases, we expect the episode to be
                # synchronized to the device, so "answer" positive
                return True

            # "What is the file size of this episode?"
            def file_size(episode):
                filename = episode.local_filename(create=False)
                if filename is None:
                    return 0
                return util.calculate_size(str(filename))

            # Calculate total size of sync and free space on device
            total_size = sum(file_size(e) for e in episodes if will_add(e))
            free_space = max(device.get_free_space(), 0)

            if total_size > free_space:
                title = _('Not enough space left on device')
                message = (_('Additional free space required: %(required_space)s\nDo you want to continue?') %
               {'required_space': util.format_filesize(total_size - free_space)})
                if not self.show_confirmation(message, title):
                    device.cancel()
                    device.close()
                    return

            # enable updating of UI
            self.set_download_list_state(gPodderSyncUI.DL_ONEOFF)

            """Update device playlists
            General approach is as follows:

            When a episode is downloaded and synched, it is added to the
            standard playlist for that podcast which is then written to
            the device.

            After the user has played that episode on their device, they
            can delete that episode from their device.

            At the next sync, gPodder will then compare the standard
            podcast-specific playlists on the device (as written by
            gPodder during the last sync), with the episodes on the
            device.If there is an episode referenced in the playlist
            that is no longer on the device, gPodder will assume that
            the episode has already been synced and subsequently deleted
            from the device, and will hence mark that episode as deleted
            in gPodder. If there are no playlists, nothing is deleted.

            At the next sync, the playlists will be refreshed based on
            the downloaded, undeleted episodes in gPodder, and the
            cycle begins again...
            """

            def resume_sync(episode_urls, channel_urls, progress):
                if progress is not None:
                    progress.on_finished()

                # rest of sync process should continue here
                self.commit_changes_to_database()
                for current_channel in self.channels:
                    # only sync those channels marked for syncing
                    if (self._config.device_sync.device_type == 'filesystem'
                            and current_channel.sync_to_mp3_player
                            and self._config.device_sync.playlists.create):

                        # get playlist object
                        playlist = gPodderDevicePlaylist(self._config,
                                                         current_channel.title)
                        # need to refresh episode list so that
                        # deleted episodes aren't included in playlists
                        episodes_for_playlist = sorted(current_channel.get_episodes(gpodder.STATE_DOWNLOADED),
                                                       key=lambda ep: ep.published)
                        # don't add played episodes to playlist if skip_played_episodes is True
                        if self._config.device_sync.skip_played_episodes:
                            episodes_for_playlist = [ep for ep in episodes_for_playlist if ep.is_new]
                        playlist.write_m3u(episodes_for_playlist)

                # enable updating of UI, but mark it as tasks being added so that a
                # adding a single task that completes immediately doesn't turn off the
                # ui updates again
                self.set_download_list_state(gPodderSyncUI.DL_ADDING_TASKS)

                if (self._config.device_sync.device_type == 'filesystem' and self._config.device_sync.playlists.create):
                    title = _('Update successful')
                    message = _('The playlist on your MP3 player has been updated.')
                    self.notification(message, title)

                # called from the main thread to complete adding tasks
                def add_downloads_complete():
                    self.set_download_list_state(gPodderSyncUI.DL_ADDED_TASKS)

                # Finally start the synchronization process
                @util.run_in_background
                def sync_thread_func():
                    device.add_sync_tasks(episodes, force_played=force_played,
                                          done_callback=done_callback)
                    util.idle_add(add_downloads_complete)
                return

            if self._config.device_sync.playlists.create:
                try:
                    episodes_to_delete = []
                    if self._config.device_sync.playlists.two_way_sync:
                        for current_channel in self.channels:
                            # only include channels that are included in the sync
                            if current_channel.sync_to_mp3_player:
                                # get playlist object
                                playlist = gPodderDevicePlaylist(self._config, current_channel.title)
                                # get episodes to be written to playlist
                                episodes_for_playlist = sorted(current_channel.get_episodes(gpodder.STATE_DOWNLOADED),
                                                               key=lambda ep: ep.published)
                                episode_keys = list(map(playlist.get_absolute_filename_for_playlist,
                                                        episodes_for_playlist))

                                episode_dict = dict(list(zip(episode_keys, episodes_for_playlist)))

                                # then get episodes in playlist (if it exists) already on device
                                episodes_in_playlists = playlist.read_m3u()
                                # if playlist doesn't exist (yet) episodes_in_playlist will be empty
                                if episodes_in_playlists:
                                    for episode_filename in episodes_in_playlists:
                                        if ((not self._config.device_sync.playlists.use_absolute_path
                                        and not playlist.playlist_folder.resolve_relative_path(episode_filename).query_exists()) or
                                        (self._config.device_sync.playlists.use_absolute_path
                                        and not playlist.mountpoint.resolve_relative_path(episode_filename).query_exists())):
                                            # episode was synced but no longer on device
                                            # i.e. must have been deleted by user, so delete from gpodder
                                            try:
                                                episodes_to_delete.append(episode_dict[episode_filename])
                                            except KeyError as ioe:
                                                logger.warning('Episode %s, removed from device has already been deleted from gpodder',
                                                            episode_filename)
                    # delete all episodes from gpodder (will prompt user)

                    # not using playlists to delete
                    def auto_delete_callback(episodes):

                        if not episodes:
                            # episodes were deleted on device
                            # but user decided not to delete them from gpodder
                            # so jump straight to sync
                            logger.info('Starting sync - no episodes selected for deletion')
                            resume_sync([], [], None)
                        else:
                            # episodes need to be deleted from gpodder
                            for episode_to_delete in episodes:
                                logger.info("Deleting episode %s",
                                            episode_to_delete.title)

                            logger.info('Will start sync - after deleting episodes')
                            self.delete_episode_list(episodes, False, resume_sync)

                        return

                    if episodes_to_delete:
                        columns = (
                            ('markup_delete_episodes', None, None, _('Episode')),
                        )

                        self.select_episodes_to_delete(
                            self.parent_window,
                            title=_('Episodes have been deleted on device'),
                            instructions='Select the episodes you want to delete:',
                            episodes=episodes_to_delete,
                            selected=[True, ] * len(episodes_to_delete),
                            columns=columns,
                            callback=auto_delete_callback,
                            _config=self._config)
                    else:
                        logger.warning("Starting sync - no episodes to delete")
                        resume_sync([], [], None)

                except IOError as ioe:
                    title = _('Error writing playlist files')
                    message = _(str(ioe))
                    self.notification(message, title)
            else:
                logger.info('Not creating playlists - starting sync')
                resume_sync([], [], None)

        # This function is used to remove files from the device
        def cleanup_episodes():
            # 'skip_played_episodes' must be used or else all the
            # played tracks will be copied then immediately deleted
            if (self._config.device_sync.delete_deleted_episodes
                or (self._config.device_sync.delete_played_episodes
                    and self._config.device_sync.skip_played_episodes)):
                all_episodes = self._filter_sync_episodes(
                    channels, only_downloaded=False)
                for local_episode in all_episodes:
                    episode = device.episode_on_device(local_episode)
                    if episode is None:
                        continue

                    if local_episode.state == gpodder.STATE_DELETED:
                        logger.info('Removing episode from device: %s',
                                    episode.title)
                        device.remove_track(episode)

            # When this is done, start the callback in the UI code
            util.idle_add(check_free_space)

        # This will run the following chain of actions:
        #  1. Remove old episodes (in worker thread)
        #  2. Check for free space (in UI thread)
        #  3. Sync the device (in UI thread)
        util.run_in_background(cleanup_episodes)
