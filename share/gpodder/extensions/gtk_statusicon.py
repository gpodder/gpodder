# -*- coding: utf-8 -*-
#
# Gtk Status Icon (gPodder bug 1495)
# Thomas Perl <thp@gpodder.org>; 2012-07-31
#

import gpodder

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Gtk Status Icon')
__description__ = _('Show a status icon for Gtk-based Desktops.')
__category__ = 'desktop-integration'
__only_for__ = 'gtk'
__disable_in__ = 'unity,win32'

import gtk
import os.path

from gpodder.gtkui import draw

DefaultConfig = {
    'download_progress_bar': False, # draw progress bar on icon while downloading?
}

class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.config = self.container.config
        self.status_icon = None
        self.icon_name = None
        self.gpodder = None
        self.last_progress = 1

    def set_icon(self, use_pixbuf=False):
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'icons')
        icon_path = os.path.abspath(path)

        theme = gtk.icon_theme_get_default()
        theme.append_search_path(icon_path)

        if self.icon_name is None:
            if theme.has_icon('gpodder'):
                self.icon_name = 'gpodder'
            else:
                self.icon_name = 'stock_mic'

        if self.status_icon is None:
            self.status_icon = gtk.status_icon_new_from_icon_name(self.icon_name)
            return

        # If current mode matches desired mode, nothing to do.
        is_pixbuf = (self.status_icon.get_storage_type() == gtk.IMAGE_PIXBUF)
        if is_pixbuf == use_pixbuf:
            return

        if not use_pixbuf:
            self.status_icon.set_from_icon_name(self.icon_name)
        else:
            # Currently icon is not a pixbuf => was loaded by name, at which
            # point size was automatically determined.
            icon_size = self.status_icon.get_size()
            icon_pixbuf = theme.load_icon(self.icon_name, icon_size, gtk.ICON_LOOKUP_USE_BUILTIN)
            self.status_icon.set_from_pixbuf(icon_pixbuf)

    def on_load(self):
        self.set_icon()
        self.status_icon.connect('activate', self.on_toggle_visible)
        self.status_icon.set_has_tooltip(True)
        self.status_icon.set_tooltip_text("gPodder")

    def on_toggle_visible(self, status_icon):
        if self.gpodder is None:
            return

        visibility = self.gpodder.main_window.get_visible()
        self.gpodder.main_window.set_visible(not visibility)

    def on_unload(self):
        if self.status_icon is not None:
            self.status_icon.set_visible(False)
            self.status_icon = None
            self.icon_name = None

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            self.gpodder = ui_object

    def get_icon_pixbuf(self):
        assert self.status_icon is not None
        if self.status_icon.get_storage_type() != gtk.IMAGE_PIXBUF:
            self.set_icon(use_pixbuf=True)
        return self.status_icon.get_pixbuf()

    def on_download_progress(self, progress):
        logger.debug("download progress: %f", progress)

        if not self.config.download_progress_bar:
            # reset the icon in case option was turned off during download
            if self.last_progress < 1:
                self.last_progress = 1
                self.set_icon()
            # in any case, we're now done
            return

        if progress == 1:
            self.set_icon() # no progress bar
            self.last_progress = progress
            return

        # Only update in 3-percent-steps to save some resources
        if abs(progress-self.last_progress) < 0.03 and progress > self.last_progress:
            return

        icon = self.get_icon_pixbuf().copy()
        progressbar = draw.progressbar_pixbuf(icon.get_width(), icon.get_height(), progress)
        progressbar.composite(icon, 0, 0, icon.get_width(), icon.get_height(), 0, 0, 1, 1, gtk.gdk.INTERP_NEAREST, 255)

        self.status_icon.set_from_pixbuf(icon)
        self.last_progress = progress

