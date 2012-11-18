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

class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.status_icon = None
        self.gpodder = None

    def on_load(self):
        self.status_icon = gtk.status_icon_new_from_icon_name('gpodder')
        self.status_icon.connect('activate', self.on_toggle_visible)

    def on_toggle_visible(self, status_icon):
        if self.gpodder is None:
            return

        if self.gpodder.main_window.get_property('visible'):
            self.gpodder.main_window.hide()
        else:
            self.gpodder.main_window.show()

    def on_unload(self):
        if self.status_icon is not None:
            self.status_icon.hide()
            self.status_icon = None

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            self.gpodder = ui_object


