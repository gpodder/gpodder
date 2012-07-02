# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
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

import gtk
import threading
import gpodder

_ = gpodder.gettext

from gpodder import util
from gpodder import sync
import logging
logger = logging.getLogger(__name__)

class gPodderSyncUI(object):
    def __init__(self, config, notification, 
            parent_window, show_confirmation, 
            update_episode_list_icons, 
            update_podcast_list_model, 
            preferences_widget, 
            episode_selector_class, download_status_model,
            download_queue_manager, 
            enable_download_list_update, 
            commit_changes_to_database):
        self._config = config
        self.notification = notification
        self.parent_window = parent_window
        self.show_confirmation = show_confirmation
        self.update_episode_list_icons = update_episode_list_icons
        self.update_podcast_list_model = update_podcast_list_model
        self.preferences_widget = preferences_widget
        self.episode_selector_class = episode_selector_class
        self.commit_changes_to_database = commit_changes_to_database
        self.download_status_model=download_status_model
        self.download_queue_manager=download_queue_manager
        self.enable_download_list_update=enable_download_list_update
        self.device=None
        

    def _filter_sync_episodes(self, channels, only_downloaded=False):
        """Return a list of episodes for device synchronization

        If only_downloaded is True, this will skip episodes that
        have not been downloaded yet and podcasts that are marked
        as "Do not synchronize to my device".
        """
        episodes = []
        for channel in channels:
            if only_downloaded:
                logger.info('Skipping channel: %s', channel.title)
                continue

            for episode in channel.get_all_episodes():
                if (episode.was_downloaded(and_exists=True) or 
                        not only_downloaded):
                    episodes.append(episode)
        return episodes

    def _show_message_unconfigured(self):
        title = _('No device configured')
        message = _('Please set up your device in the preferences dialog.')
        self.notification(message, title, widget=self.preferences_widget)

    def _show_message_cannot_open(self):
        title = _('Cannot open device')
        message = _('Please check the settings in the preferences dialog.')
        self.notification(message, title, widget=self.preferences_widget)

    def on_synchronize_episodes(self, channels, episodes=None, force_played=True):
        
        device = sync.open_device(self)

        if device is None:
            return self._show_message_unconfigured()

        if not device.open():
            return self._show_message_cannot_open()
        else:
            #only set if device is configured
            #and opened successfully
            self.device=device

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
                if (not force_played and 
                        self._config.device_sync.skip_played_episodes):
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
                message = _('You need to free up %s.\nDo you want to continue?') \
                                % (util.format_filesize(total_size-free_space),)
                if not self.show_confirmation(message, title):
                    device.cancel()
                    device.close()
                    return

            # Finally start the synchronization process              
            def sync_thread_func():
                self.enable_download_list_update()                
                device.add_sync_tasks(episodes, force_played=force_played)

            threading.Thread(target=sync_thread_func).start()

        # This function is used to remove files from the device
        def cleanup_episodes():
            # 'skip_played_episodes' must be used or else all the
            # played tracks will be copied then immediately deleted
            if (self._config.device_sync.delete_played_episodes and 
                    self._config.device_sync.skip_played_episodes):
                all_episodes = self._filter_sync_episodes(channels, 
                        only_downloaded=False)
                episodes_on_device = device.get_all_tracks()
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
        threading.Thread(target=cleanup_episodes).start()
