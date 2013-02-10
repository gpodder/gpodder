# -*- coding: utf-8 -*-
#
# Gtk Status Icon (gPodder bug 1495)
# Thomas Perl <thp@gpodder.org>; 2012-07-31
#

import gpodder

_ = gpodder.gettext

__title__ = _('Gtk Status Icon')
__description__ = _('Show a status icon for Gtk-based Desktops.')
__category__ = 'desktop-integration'
__only_for__ = 'gtk'
__disable_in__ = 'unity'

import gtk
import os.path

class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.status_icon = None
        self.gpodder = None

    def on_load(self):
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'icons')
        icon_path = os.path.abspath(path)

        theme = gtk.icon_theme_get_default()
        theme.append_search_path(icon_path)

        if theme.has_icon('gpodder'):
            self.status_icon = gtk.status_icon_new_from_icon_name('gpodder')
        else:
            self.status_icon = gtk.status_icon_new_from_icon_name('stock_mic')

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

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            self.gpodder = ui_object


