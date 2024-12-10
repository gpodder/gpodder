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
from gpodder import coverart

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
    "art_name_on_device": "cover.jpg",
    "convert_and_resize_art": True,
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

            # discover desired filetype
            device_filetype = self.config.art_name_on_device.split(".")[-1]
            device_filename = self.config.art_name_on_device.strip(".%s" % (device_filetype))

            # only allow jpeg, jpg, and png - if invalid, default to jpg
            if device_filetype.lower() != "jpeg" and device_filetype.lower() != "jpg"\
                    and device_filetype.lower() != "png":
                device_filetype = "jpg"

            # sanitize for filetype checking - "jpg" will not match "jpeg"
            if device_filetype.upper() == "JPG":
                device_match_filetype = "JPEG"
            else:
                device_match_filetype = device_filetype.upper()

            if (self.config.convert_and_resize_art is True):
                # episode.channel.cover_file gives us the file and path (no extension!),
                # get the real file and path from CoverDownloader()
                episode_art = coverart.CoverDownloader().get_cover(episode.channel.cover_file,
                                                            None, None, None, download=False)
                logger.info("episode_art file: %s", episode_art)

                device_art = os.path.join(device_folder, "%s.%s" %
                    (device_filename, device_filetype))
                device_lockpath = "%s%s" % (device_art, ".lock")
                device_lockfile = SoftFileLock(device_lockpath, blocking=False)

                if os.path.isfile(episode_art):
                    copyflag = False

                    # if already exists, check if it's what we want:
                    try:
                        # lock the file first, otherwise we can easily crash
                        device_lockfile.acquire()
                    except:
                        logger.info('Could not acquire file lock for %s', device_art)
                    else:
                        # file exists, check if it's what we want or not
                        if os.path.isfile(device_art):
                            try:
                                with Image.open(device_art) as img:
                                    if img.height != int(self.config.convert_size) and\
                                            self.config.convert_allow_upscale_art is True:
                                        copyflag = True
                                    elif img.height > int(self.config.convert_size) and\
                                            self.config.convert_allow_upscale_art is False:
                                        copyflag = True
                                    elif img.format.upper() != device_match_filetype:
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
