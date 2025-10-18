# -*- coding: utf-8 -*-

# Ubuntu AppIndicator Icon
# Thomas Perl <thp@gpodder.org>; 2012-02-24

import logging

import gi  # isort:skip
gi.require_version('AppIndicator3', '0.1')
from gi.repository import AppIndicator3 as appindicator
from gi.repository import Gtk

import gpodder

_ = gpodder.gettext

__title__ = _('Ubuntu App Indicator')
__description__ = _('Show a status indicator in the top bar.')
__authors__ = 'Thomas Perl <thp@gpodder.org>'
__category__ = 'desktop-integration'
__only_for__ = 'gtk'
__mandatory_in__ = 'unity'
__disable_in__ = 'win32'


logger = logging.getLogger(__name__)


DefaultConfig = {
    'visible': True,  # Set to False if you don't want to show the appindicator
}


class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.config = container.config
        self.indicator = None
        self.gpodder = None

    def on_load(self):
        if self.config.visible:
            self.indicator = appindicator.Indicator.new('gpodder', 'gpodder',
                    appindicator.IndicatorCategory.APPLICATION_STATUS)
            self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)

    def _rebuild_menu(self):
        menu = Gtk.Menu()
        toggle_visible = Gtk.CheckMenuItem(_('Show main window'))
        toggle_visible.set_active(True)

        def on_toggle_visible(menu_item):
            if menu_item.get_active():
                self.gpodder.main_window.show()
            else:
                self.gpodder.main_window.hide()
        toggle_visible.connect('activate', on_toggle_visible)
        menu.append(toggle_visible)
        menu.append(Gtk.SeparatorMenuItem())
        quit_gpodder = Gtk.MenuItem(_('Quit'))

        def on_quit(menu_item):
            self.gpodder.on_gPodder_delete_event(self.gpodder.main_window)
        quit_gpodder.connect('activate', on_quit)
        menu.append(quit_gpodder)
        menu.show_all()
        self.indicator.set_menu(menu)

    def on_unload(self):
        self.indicator = None

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            self.gpodder = ui_object
            self._rebuild_menu()
