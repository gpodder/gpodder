# Copies cover art to a file based device
#
# (c) 2014-04-10 Alex Mayer <magictrick4906@aim.com>
# Released under the same license terms as gPodder itself.

# Use a logger for debug output - this will be managed by gPodder
import logging
import os
import shutil

from filelock import SoftFileLock, Timeout
from PIL import Image

import gpodder

logger = logging.getLogger(__name__)
_ = gpodder.gettext


# Provide some metadata that will be displayed in the gPodder GUI
__title__ = _('Rockbox Cover Art Sync')
__description__ = _('Copy Cover Art To Rockboxed Media Player')
__only_for__ = 'gtk, cli'
__authors__ = 'Alex Mayer <magictrick4906@aim.com>, Dana Conrad <dconrad@fastmail.com>'
__doc__ = 'https://gpodder.github.io/docs/extensions/rockbox_coverart.html'
__category__ = 'post-download'

DefaultConfig = {
    "art_name_on_device": "cover.jpg",  # The original setting
    "art_name_on_device_noext": "cover",
    "convert_and_resize_art": True,
    "convert_filetype": "jpeg",  # plese use "jpeg", will autocorrect if "jpg"
    "convert_size": 500,
    "convert_allow_upscale_art": False,
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

            # sanitize filetype
            if self.config.convert_filetype.lower() == "jpg":
                self.config.convert_filetype = "jpeg"

            # barring any way for gpodder core to tell us the source cover art name,
            # let's try to find it...
            if (self.config.convert_and_resize_art is True):
                if os.path.isfile(os.path.join(episode_folder, "folder.jpg")):
                    episode_art = os.path.join(episode_folder, "folder.jpg")
                elif os.path.isfile(os.path.join(episode_folder, "cover.jpg")):
                    episode_art = os.path.join(episode_folder, "cover.jpg")
                elif os.path.isfile(os.path.join(episode_folder, "folder.jpeg")):
                    episode_art = os.path.join(episode_folder, "folder.jpeg")
                elif os.path.isfile(os.path.join(episode_folder, "cover.jpeg")):
                    episode_art = os.path.join(episode_folder, "cover.jpeg")
                elif os.path.isfile(os.path.join(episode_folder, "folder.png")):
                    episode_art = os.path.join(episode_folder, "folder.png")
                elif os.path.isfile(os.path.join(episode_folder, "cover.png")):
                    episode_art = os.path.join(episode_folder, "cover.png")

                device_art = os.path.join(device_folder, "%s.%s" %
                    (self.config.art_name_on_device_noext, self.config.convert_filetype.lower()))
                device_lockpath = "%s%s" % (device_art, ".lock")
                device_lockfile = SoftFileLock(device_lockpath, blocking=False)

                if os.path.isfile(episode_art):
                    copyflag = False

                    # if already exists, check if it's what we want:
                    try:
                        # lock the file first, otherwise we can easily crash
                        device_lockfile.acquire()
                    except:
                        logger.info('info: Could not acquire file lock for %s', device_art)
                    else:
                        # file exists, assume it's good (see comment below)
                        if os.path.isfile(device_art):
                            try:
                                with Image.open(device_art) as img:
                                    if img.height != int(self.config.convert_size) and\
                                        self.config.convert_allow_upscale_art is True:
                                        copyflag = True
                                    elif img.height > int(self.config.convert_size) and\
                                        self.config.convert_allow_upscale_art is False:
                                        copyflag = True
                                    elif img.format.lower() != self.config.convert_filetype.lower():
                                        copyflag = True
                                    try:
                                        if img.info['progressive'] == 1:
                                            copyflag = True
                                    except:
                                        pass  # expected result if baseline jpeg or png
                            except OSError:
                                logger.info("%s check image error!", device_art)
                        # file does not exist, we will create it
                        else:
                            copyflag = True

                        if copyflag is True:
                            logger.info("%s %s" % (device_art, "copying"))
                            try:
                                # should we file lock the source file?
                                with Image.open(episode_art) as img:
                                    if img.height > int(self.config.convert_size)\
                                        or self.config.convert_allow_upscale_art is True:
                                        out = img.resize((int(self.config.convert_size), int(self.config.convert_size)))
                                    else:
                                        out = img.copy()
                                    out.save(device_art)
                            except OSError:
                                logger.info("%s image error!", episode_art)
                        else:
                            logger.info("%s %s" % (device_art, "already exists"))

                        device_lockfile.release()

            # original functionality
            else:
                episode_art = os.path.join(episode_folder, "folder.jpg")
                device_art = os.path.join(device_folder, self.config.art_name_on_device)

                # make sure we have art to copy and it doesn't already exist
                if os.path.isfile(episode_art) and not os.path.isfile(device_art):
                    logger.info('Fallback Syncing cover art for %s', episode.channel.title)
                    # copy and rename art
                    shutil.copy(episode_art, device_art)
