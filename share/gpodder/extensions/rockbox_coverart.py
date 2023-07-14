# Copies cover art to a file based device
#
# (c) 2014-04-10 Alex Mayer <magictrick4906@aim.com>
# Released under the same license terms as gPodder itself.

# Use a logger for debug output - this will be managed by gPodder
import logging
import os
import shutil

import gpodder

logger = logging.getLogger(__name__)
_ = gpodder.gettext


# Provide some metadata that will be displayed in the gPodder GUI
__title__ = _('Rockbox Cover Art Sync')
__description__ = _('Copy Cover Art To Rockboxed Media Player')
__only_for__ = 'gtk, cli'
__authors__ = 'Alex Mayer <magictrick4906@aim.com>'

DefaultConfig = {
    "art_name_on_device": "cover.jpg"  # The file name that will be used on the device for cover art
}


class gPodderExtension:

    def __init__(self, container):
        self.container = container
        self.config = self.container.config

    def on_episode_synced(self, device, episode):
        # check that we have the functions we need
        if hasattr(device, 'get_episode_folder_on_device'):
            # get the file and folder names we need
            episode_folder = os.path.dirname(episode.local_filename(False))
            device_folder = device.get_episode_folder_on_device(episode)
            episode_art = os.path.join(episode_folder, "folder.jpg")
            device_art = os.path.join(device_folder, self.config.art_name_on_device)
            # make sure we have art to copy and it doesn't already exist
            if os.path.isfile(episode_art) and not os.path.isfile(device_art):
                logger.info('Syncing cover art for %s', episode.channel.title)
                # copy and rename art
                shutil.copy(episode_art, device_art)
