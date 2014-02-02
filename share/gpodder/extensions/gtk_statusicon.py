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

class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.status_icon = None
        self.icon_name = None
        self.icon_size = None
        self.gpodder = None
        self.last_progress = 0

    def set_icon(self):
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'icons')
        icon_path = os.path.abspath(path)

        theme = gtk.icon_theme_get_default()
        theme.append_search_path(icon_path)

        if self.icon_name is None:
            if theme.has_icon('gpodder'):
                self.icon_name = 'gpodder'
            else:
                self.icon_name = 'stock_mic'

        if self.icon_size is None:
            # first load from icon name to get the automatically determined size
            self.status_icon = gtk.status_icon_new_from_icon_name(self.icon_name)
            self.icon_size = self.status_icon.get_size()
        
        icon_pixbuf = theme.load_icon(self.icon_name, self.icon_size, gtk.ICON_LOOKUP_USE_BUILTIN)

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
            self.icon_size = None

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            self.gpodder = ui_object

    def on_download_progress(self, progress):
        logger.debug("download progress: %f", progress)

        if progress == 1:
            self.set_icon() # no progress bar
            self.last_progress = progress
            return

        # Only update in 3-percent-steps to save some resources
        if abs(progress-self.last_progress) < 0.03 and progress > self.last_progress:
            return

        icon = self.status_icon.get_pixbuf().copy()
        progressbar = draw.progressbar_pixbuf(icon.get_width(), icon.get_height(), progress)
        progressbar.composite(icon, 0, 0, icon.get_width(), icon.get_height(), 0, 0, 1, 1, gtk.gdk.INTERP_NEAREST, 255)

        self.status_icon.set_from_pixbuf(icon)
        self.last_progress = progress

