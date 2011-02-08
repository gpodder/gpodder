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


# trayicon.py -- Tray icon and notification support
# Jérôme Chabod (JCH) <jerome.chabod@ifrance.com>  2007-12-20


import gtk

import gpodder
from gpodder.liblogger import log

_ = gpodder.gettext
N_ = gpodder.ngettext

from gpodder.gtkui import draw

class GPodderStatusIcon(gtk.StatusIcon):
    """ this class display a status icon in the system tray
    this icon serves to show or hide gPodder, notify dowload status
    and provide a popupmenu for quick acces to some
    gPodder functionalities

    author: Jérôme Chabod <jerome.chabod at ifrance.com>
    """

    DEFAULT_TOOLTIP = _('gPodder media aggregator')

    # status: they are displayed as tooltip and add a small icon to the main icon
    STATUS_DOWNLOAD_IN_PROGRESS = (_('Downloading episodes'), gtk.STOCK_GO_DOWN)
    STATUS_UPDATING_FEED_CACHE = (_('Looking for new episodes'), gtk.STOCK_REFRESH)
    STATUS_SYNCHRONIZING = (_('Synchronizing to player'), 'multimedia-player')
    STATUS_DELETING = (_('Cleaning files'), gtk.STOCK_DELETE)

    def __init__(self, gp, icon_filename, config):
        gtk.StatusIcon.__init__(self)
        log('Creating tray icon', sender=self)
        
        self._config = config
        self.__gpodder = gp
        self.__icon_cache = {}
        self.__icon_filename = icon_filename
        self.__current_icon = -1

        # try getting the icon
        try:
            self.__icon = gtk.gdk.pixbuf_new_from_file(self.__icon_filename)
        except Exception, exc:
            log('Warning: Cannot load gPodder icon, will use the default icon (%s)', exc, sender=self)
            self.__icon = gtk.icon_theme_get_default().load_icon(gtk.STOCK_DIALOG_QUESTION, 30, 30)

        # Reset trayicon (default icon, default tooltip)
        self.__current_pixbuf = None
        self.__last_ratio = 1.0
        self.set_status()
 
        menu = self.__create_context_menu()
        self.connect('activate', self.__on_left_click)
        self.connect('popup-menu', self.__on_right_click, menu)

        self.set_visible(True)

    def __create_context_menu(self):
        # build and connect the popup menu
        menu = gtk.Menu()
        menuItem = gtk.ImageMenuItem(_("Check for new episodes"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_FIND, gtk.ICON_SIZE_MENU))
        menuItem.connect('activate',  self.__gpodder.on_itemUpdate_activate)
        menu.append(menuItem)
        
        menuItem = gtk.ImageMenuItem(_("Download all new episodes"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_DOWN, gtk.ICON_SIZE_MENU))
        menuItem.connect('activate',  self.__gpodder.on_itemDownloadAllNew_activate)
        menu.append(menuItem)

        # menus's label will adapt to the synchronisation device name
        if self._config.device_type != 'none':
            menuItem = gtk.ImageMenuItem(_('Synchronize to device'))
            menuItem.set_sensitive(self._config.device_type != 'none')
            menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_REFRESH, gtk.ICON_SIZE_MENU))
            menuItem.connect('activate',  self.__gpodder.on_sync_to_ipod_activate)
            menu.append(menuItem)
            menu.append( gtk.SeparatorMenuItem())
        
        menuItem = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        menuItem.connect('activate',  self.__gpodder.on_itemPreferences_activate)
        menu.append(menuItem)
        
        menuItem = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        menuItem.connect('activate',  self.__gpodder.on_itemAbout_activate)
        menu.append(menuItem)
        menu.append( gtk.SeparatorMenuItem())
        
        menuItem = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        menuItem.connect('activate',  self.__on_exit_callback)
        menu.append(menuItem)
        
        return menu

    def __on_exit_callback(self, widget, *args):
        self.__gpodder.close_gpodder()

    def __on_right_click(self, widget, button=None, time=0, data=None):
        """Open popup menu on right-click
        """
        if data is not None:
            data.show_all()
            data.popup(None, None, None, 3, time)

    def __on_left_click(self, widget, data=None):
        """Hide/unhide gPodder on left-click
        """
        if self.__gpodder.is_iconified():
            self.__gpodder.uniconify_main_window()
        else:
            if not self.__gpodder.gPodder.is_active():
		self.__gpodder.uniconify_main_window()
            else:
                self.__gpodder.iconify_main_window()


    def __get_status_icon(self, icon):
        if icon in self.__icon_cache:
            return self.__icon_cache[icon]

        try:
            new_icon = self.__icon.copy()
            emblem = gtk.icon_theme_get_default().load_icon(icon, int(new_icon.get_width()/1.5), 0)
            (width, height) = (emblem.get_width(), emblem.get_height())
            xpos = new_icon.get_width()-width
            ypos = new_icon.get_height()-height
            emblem.composite(new_icon, xpos, ypos, width, height, xpos, ypos, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)
            self.__icon_cache[icon] = new_icon
            return new_icon
        except Exception, exc:
            pass

        log('Warning: Cannot create status icon: %s', icon, sender=self)
        return self.__icon

    def set_status(self, status=None, tooltip=None):
        if status is None:
            if tooltip is None:
                tooltip = self.DEFAULT_TOOLTIP
            else:
                tooltip = 'gPodder - %s' % tooltip
            if self.__current_icon is not None:
                self.__current_pixbuf = self.__icon
                self.set_from_pixbuf(self.__current_pixbuf)
                self.__current_icon = None
        else:
            (status_tooltip, icon) = status
            if tooltip is None:
                tooltip = 'gPodder - %s' % status_tooltip
            else:
                tooltip = 'gPodder - %s' % tooltip
            if self.__current_icon != icon:
                self.__current_pixbuf = self.__get_status_icon(icon)
                self.set_from_pixbuf(self.__current_pixbuf)
                self.__current_icon = icon
        self.set_tooltip(tooltip)

    def draw_progress_bar(self, ratio):
        """
        Draw a progress bar on top of this tray icon.
        The ratio parameter should be a value from 0 to 1.
        """

        # Only update in 3-percent-steps to save some resources
        if abs(ratio-self.__last_ratio) < 0.03 and ratio > self.__last_ratio:
            return

        icon = self.__current_pixbuf.copy()
        progressbar = draw.progressbar_pixbuf(icon.get_width(), icon.get_height(), ratio)
        progressbar.composite(icon, 0, 0, icon.get_width(), icon.get_height(), 0, 0, 1, 1, gtk.gdk.INTERP_NEAREST, 255)
        
        self.set_from_pixbuf(icon)
        self.__last_ratio = ratio

