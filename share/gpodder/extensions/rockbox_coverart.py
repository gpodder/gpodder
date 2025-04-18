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

import gi  # isort:skip
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

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
            device_filename, device_filetype = self.config.art_name_on_device.rsplit(".", 1)

            # only allow jpeg, jpg, and png - if invalid, default to jpg
            if device_filetype.lower() not in ("jpeg", "jpg", "png"):
                device_filetype = "jpg"

            # sanitize for filetype checking - "jpg" will not match "jpeg"
            if device_filetype.upper() == "JPG":
                device_match_filetype = "JPEG"
            else:
                device_match_filetype = device_filetype.upper()

            if self.config.convert_and_resize_art:
                # episode.channel.cover_file gives us the file and path (no extension!),
                # get the real file and path from CoverDownloader()
                episode_art = coverart.CoverDownloader().get_cover(episode.channel.cover_file,
                                                            None, None, None, download=False)
                logger.info("episode_art file: %s", episode_art)

                device_art = os.path.join(device_folder, "%s.%s" %
                    (device_filename, device_filetype))
                device_lockpath = "%s.lock" % device_art
                device_lockfile = SoftFileLock(device_lockpath, blocking=False)

                if os.path.isfile(episode_art):
                    copyflag = False

                    # if already exists, check if it's what we want:
                    try:
                        # lock the file first, otherwise we can easily crash
                        # N.B. Be careful when modifying anything within this try: except
                        # block - All branches should catch their own exceptions so that
                        # we always release the lockfile!
                        device_lockfile.acquire()
                    except:
                        logger.info('Could not acquire file lock for %s', device_art)
                    else:
                        # file exists, check if it's what we want or not
                        if os.path.isfile(device_art):
                            try:
                                with Image.open(device_art) as img:
                                    imgsize = max(img.height, img.width)
                                    if imgsize != int(self.config.convert_size) and\
                                            self.config.convert_allow_upscale_art:
                                        copyflag = True
                                    elif imgsize > int(self.config.convert_size) and\
                                            not self.config.convert_allow_upscale_art:
                                        copyflag = True
                                    elif img.format.upper() != device_match_filetype:
                                        copyflag = True
                                    try:
                                        if img.info['progressive'] == 1:
                                            copyflag = True
                                    except:
                                        pass  # expected result if baseline jpeg or png
                            except OSError:
                                copyflag = False
                                logger.info("%s check image error: %r", device_art, e)
                        # file does not exist, we will create it
                        else:
                            copyflag = True

                        if copyflag:
                            logger.info("%s %s" % (device_art, "copying"))
                            try:
                                # should we file lock the source file?
                                with Image.open(episode_art) as img:
                                    if img.height > int(self.config.convert_size)\
                                            or self.config.convert_allow_upscale_art:
                                        ratio = min(self.config.convert_size / img.height, self.config.convert_size / img.width)
                                        newsize = (int(ratio * img.width), int(ratio * img.height))
                                        out = img.resize(newsize)
                                    else:
                                        out = img.copy()
                                    out.save(device_art)
                            except OSError as e:
                                logger.info("%s copy image error: %r", episode_art, e)
                        else:
                            logger.info("%s already exists" % device_art)

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

    def toggle_sensitivity_of_widgets(self):
        # all options rely on convert_and_resize_art being true
        self.container.convert_allow_upscale.set_sensitive(self.config.convert_and_resize_art)
        self.container.convert_size.set_sensitive(self.config.convert_and_resize_art)
        self.container.convert_size_label.set_sensitive(self.config.convert_and_resize_art)
        self.container.art_name_on_device.set_sensitive(self.config.convert_and_resize_art)
        self.container.art_name_on_device_label.set_sensitive(self.config.convert_and_resize_art)
        self.container.note2.set_sensitive(self.config.convert_and_resize_art)

    def toggle_convert_and_resize_art(self, widget):
        self.config.convert_and_resize_art = widget.get_active()
        self.toggle_sensitivity_of_widgets()

    def toggle_convert_allow_upscale_art(self, widget):
        self.config.convert_allow_upscale_art = widget.get_active()

    def on_convert_size_changed(self, widget):
        self.config.convert_size = widget.get_value_as_int()

    def on_art_name_on_device_changed(self, widget):
        self.config.art_name_on_device = widget.get_text()

    def show_preferences(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        title = Gtk.Label(use_markup=True, label=_('<b><big>Rockbox Coverart Extension</big></b>'))
        title.set_halign(Gtk.Align.CENTER)
        box.add(title)

        whatisthis = Gtk.Label(use_markup=True, wrap=True, label=_(
            'This extension writes podcast cover art to a media player.'
            ' This extension assumes that each podcast has its own folder on device.'
            ' Only folder-wide coverart is written - this extension does not do anything'
            ' about embedded cover art.'
        ))
        whatisthis.set_property('xalign', 0.0)
        box.add(whatisthis)

        box.pack_start(Gtk.HSeparator(), False, False, 0)

        self.container.convert_enable = Gtk.CheckButton(_('Process art: convert, resize, and make baseline'))
        self.container.convert_enable.set_active(self.config.convert_and_resize_art)
        self.container.convert_enable.connect('toggled', self.toggle_convert_and_resize_art)
        box.pack_start(self.container.convert_enable, False, False, 0)

        self.container.note1 = Gtk.Label(use_markup=True, wrap=True, label=_(
            'Enable conversion and resizing of art.\n\n'
            ' If enabled, convert art to desired format (default JPEG) and size (default 500px),\n'
            ' and if format is JPEG, write as Baseline (rather than Progressive) format.\n'
            ' If disabled, fall back to simple behavior.'))
        self.container.note1.set_property('xalign', 0.0)
        box.add(self.container.note1)

        self.container.convert_allow_upscale = Gtk.CheckButton(_('Allow upscaling of art'))
        self.container.convert_allow_upscale.set_active(self.config.convert_allow_upscale_art)
        self.container.convert_allow_upscale.connect('toggled', self.toggle_convert_allow_upscale_art)
        box.pack_start(self.container.convert_allow_upscale, False, False, 0)

        self.container.convert_size = Gtk.SpinButton()
        self.container.convert_size.set_numeric(True)
        self.container.convert_size.set_range(100, 2000)
        self.container.convert_size.set_digits(0)
        self.container.convert_size.set_increments(50, 100)
        self.container.convert_size.set_snap_to_ticks(True)
        self.container.convert_size.set_value(float(self.config.convert_size))
        self.container.convert_size.set_halign(Gtk.Align.END)
        self.container.convert_size.set_size_request(200, -1)
        self.container.convert_size.connect("value-changed", self.on_convert_size_changed)
        self.container.convert_size.set_sensitive(self.config.convert_and_resize_art)
        self.container.convert_size_label = Gtk.Label(_('Image size (px):'))
        self.container.hbox_convert_size = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.container.hbox_convert_size.pack_start(self.container.convert_size_label, False, False, 0)
        self.container.hbox_convert_size.pack_start(self.container.convert_size, True, True, 0)
        box.pack_start(self.container.hbox_convert_size, False, False, 0)

        self.container.art_name_on_device = Gtk.Entry()
        self.container.art_name_on_device.set_text(self.config.art_name_on_device)
        self.container.art_name_on_device.connect("changed", self.on_art_name_on_device_changed)
        self.container.art_name_on_device.set_halign(Gtk.Align.END)
        self.container.art_name_on_device.set_size_request(200, -1)
        self.container.art_name_on_device_label = Gtk.Label(_('Art name on device:'))
        self.container.hbox_art_name = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.container.hbox_art_name.pack_start(self.container.art_name_on_device_label, False, False, 0)
        self.container.hbox_art_name.pack_start(self.container.art_name_on_device, True, True, 0)
        box.pack_start(self.container.hbox_art_name, False, False, 0)

        self.container.note2 = Gtk.Label(use_markup=True, wrap=True, label=_(
            'Only JPEG and PNG formats are allowed. Note that Rockbox only supports'
            ' JPEG format images, so PNG is not recommended if using a Rockbox player.'
            ' Typically, devices look for art named either \"cover.jpg\" or \"folder.jpg\".'))
        self.container.note2.set_property('xalign', 0.0)
        box.add(self.container.note2)

        self.toggle_sensitivity_of_widgets()

        box.show_all()
        return box

    def on_preferences(self):
        return [(_('Rockbox Coverart'), self.show_preferences)]
