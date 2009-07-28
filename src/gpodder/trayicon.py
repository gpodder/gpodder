# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
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
import datetime

import gpodder
from gpodder.liblogger import log

_ = gpodder.gettext

try:
    import pynotify
    have_pynotify = True
except:
    log('Cannot find pynotify. Please install the python-notify package.')
    log('Notification bubbles have been disabled.')
    have_pynotify = False

from gpodder import services
from gpodder import util

from gpodder.gtkui import draw

from xml.sax import saxutils

if gpodder.interface == gpodder.MAEMO:
    import hildon

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
        self.__synchronisation_device = None
        self.__sync_progress = ''

        self.__previous_notification = None

        # try getting the icon
        try:
            if gpodder.interface == gpodder.GUI:
                self.__icon = gtk.gdk.pixbuf_new_from_file(self.__icon_filename)
            elif gpodder.interface == gpodder.MAEMO:
                self.__icon = gtk.gdk.pixbuf_new_from_file_at_size(self.__icon_filename, 36, 36)
        except Exception, exc:
            log('Warning: Cannot load gPodder icon, will use the default icon (%s)', exc, sender=self)
            self.__icon = gtk.icon_theme_get_default().load_icon(gtk.STOCK_DIALOG_QUESTION, 30, 30)

        # Reset trayicon (default icon, default tooltip)
        self.__current_pixbuf = None
        self.__last_ratio = 1.0
        self.set_status()
 
        menu = self.__create_context_menu()
        if gpodder.interface == gpodder.GUI:
            self.connect('activate', self.__on_left_click)
            self.connect('popup-menu', self.__on_right_click, menu)
        elif gpodder.interface == gpodder.MAEMO:
            # On Maemo, we show the popup menu on left-click
            self.connect('activate', self.__on_right_click, menu)

        self.set_visible(True)

        # initialise pynotify
        if have_pynotify:
            if not pynotify.init('gPodder'):
                log('Error: unable to initialise pynotify', sender=self)

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
        
        self.menuItem_previous_msg = gtk.ImageMenuItem(_('Show previous message again'))
        self.menuItem_previous_msg.set_image(gtk.image_new_from_stock(gtk.STOCK_INFO, gtk.ICON_SIZE_MENU))       
        self.menuItem_previous_msg.connect('activate',  self.__on_show_previous_message_callback)
        self.menuItem_previous_msg.set_sensitive(False)
        menu.append(self.menuItem_previous_msg)
        
        menu.append( gtk.SeparatorMenuItem())
        
        menuItem = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        menuItem.connect('activate',  self.__gpodder.on_itemPreferences_activate)
        menu.append(menuItem)
        
        menuItem = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        menuItem.connect('activate',  self.__gpodder.on_itemAbout_activate)
        menu.append(menuItem)
        menu.append( gtk.SeparatorMenuItem())
        
        if gpodder.interface == gpodder.MAEMO:
            # On Maemo, we map the left-click to the popup-menu,
            # so add a menu item to do the left-click action
            menuItem = gtk.ImageMenuItem(_('Hide gPodder'))
            self.item_showhide = menuItem

            def show_hide_gpodder_maemo(menu_item):
                visible = self.__gpodder.gPodder.get_property('visible')
                (label, image) = menu_item.get_children()
                if visible:
                    label.set_text(_('Show gPodder'))
                    menu_item.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_UP, gtk.ICON_SIZE_MENU))
                else:
                    label.set_text(_('Hide gPodder'))
                    menu_item.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_DOWN, gtk.ICON_SIZE_MENU))
                self.__gpodder.gPodder.set_property('visible', not visible)
                
            menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_DOWN, gtk.ICON_SIZE_MENU))
            menuItem.connect('activate', lambda widget: show_hide_gpodder_maemo(self.item_showhide))
            menu.append(menuItem)
        
        menuItem = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        menuItem.connect('activate',  self.__on_exit_callback)
        menu.append(menuItem)
        
        return menu

    def __on_exit_callback(self, widget, *args):
        self.__gpodder.close_gpodder()

    def __on_show_previous_message_callback(self, widget, *args):
        if self.__previous_notification is not None:
            message, title, is_error = self.__previous_notification
            self.send_notification(message, title, is_error)

    def __on_right_click(self, widget, button=None, time=0, data=None):
        """Open popup menu on right-click
        """
        if gpodder.interface == gpodder.MAEMO and data is None and button is not None:
            # The left-click action has a different function
            # signature, so we have to swap parameters here
            data = button
        if data is not None:
            data.show_all()
            data.popup(None, None, None, 3, time)

    def __on_left_click(self, widget, data=None):
        """Hide/unhide gPodder on left-click
        """
        if self.__gpodder.minimized:
            self.__gpodder.uniconify_main_window()
        else:
            if not self.__gpodder.gpodder_main_window.is_active(): 
                self.__gpodder.gpodder_main_window.present()
            else:            
                self.__gpodder.iconify_main_window()

    def downloads_finished(self, download_tasks_seen):
        # FIXME: Filter all tasks that have already been reported
        finished_downloads = [str(task) for task in download_tasks_seen if task.status == task.DONE]
        failed_downloads = [str(task)+' ('+task.error_message+')' for task in download_tasks_seen if task.status == task.FAILED]

        if finished_downloads and failed_downloads:
            message = self.format_episode_list(finished_downloads, 5)
            message += '\n\n<i>%s</i>\n' % _('These downloads failed:')
            message += self.format_episode_list(failed_downloads, 5)
            self.send_notification(message, _('gPodder downloads finished'), True)
        elif finished_downloads:
            message = self.format_episode_list(finished_downloads)
            self.send_notification(message, _('gPodder downloads finished'))
        elif failed_downloads:
            message = self.format_episode_list(failed_downloads)
            self.send_notification(message, _('gPodder downloads failed'), True)

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

    def __is_notification_on(self):
        # tray icon not visible or notifications disabled
        if not self.get_visible() or not self._config.enable_notifications:
            return False
        return True
    
    def send_notification( self, message, title = "gPodder", is_error=False):
        if not self.__is_notification_on(): return

        message = message.strip()
        log('Notification: %s', message, sender=self)
        if gpodder.interface == gpodder.MAEMO:
            pango_markup = '<b>%s</b>\n<small>%s</small>' % (title, message)
            hildon.hildon_banner_show_information_with_markup(gtk.Label(''), None, pango_markup)
        elif gpodder.interface == gpodder.GUI and have_pynotify:
            notification = pynotify.Notification(title, message, self.__icon_filename)
            if is_error: notification.set_urgency(pynotify.URGENCY_CRITICAL)
            try:
                notification.attach_to_status_icon(self)
            except:
                log('Warning: Cannot attach notification to status icon.', sender=self)
            if not notification.show():
                log("Error: enable to send notification %s", message)
        else:
            return
        
        # If we showed any kind of notification, remember it for next time
        self.__previous_notification = (message, title, is_error)
        self.menuItem_previous_msg.set_sensitive(True)
        
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

    def format_episode_list(self, episode_list, max_episodes=10):
        """
        Format a list of episode names for notifications

        Will truncate long episode names and limit the amount of
        episodes displayed (max_episodes=10).

        The episode_list parameter should be a list of strings.
        """
        MAX_TITLE_LENGTH = 100

        result = []
        for title in episode_list[:min(len(episode_list), max_episodes)]:
            if len(title) > MAX_TITLE_LENGTH:
                middle = (MAX_TITLE_LENGTH/2)-2
                title = '%s...%s' % (title[0:middle], title[-middle:])
            result.append(saxutils.escape(title))
            result.append('\n')
 
        more_episodes = len(episode_list) - max_episodes
        if more_episodes > 0:
            result.append('(...')
            if more_episodes == 1:
                result.append(_('one more episode'))
            else:
                result.append(_('%d more episodes') % more_episodes)
            result.append('...)')

        return (''.join(result)).strip()
    
    def set_synchronisation_device(self, synchronisation_device):
        assert not self.__synchronisation_device, "a device was already set without have been released"
        
        self.__synchronisation_device = synchronisation_device
        self.__synchronisation_device.register('progress', self.__on_synchronisation_progress)
        self.__synchronisation_device.register('status', self.__on_synchronisation_status)
        self.__synchronisation_device.register('done', self.__on_synchronisation_done)
        
    def release_synchronisation_device(self):
        assert self.__synchronisation_device, "request for releasing a device which was never set"
        
        self.__synchronisation_device.unregister('progress', self.__on_synchronisation_progress)
        self.__synchronisation_device.unregister('status', self.__on_synchronisation_status)
        self.__synchronisation_device.unregister('done', self.__on_synchronisation_done)        
        self.__synchronisation_device = None
        
    def __on_synchronisation_progress(self, pos, max, text=None):
        if text is None:
            text = _('%d of %d done') % (pos, max)
        self.__sync_progress = text

    def __on_synchronisation_status(self, status):
        tooltip = _('%s\n%s') % (status, self.__sync_progress)
        self.set_status(self.STATUS_SYNCHRONIZING, tooltip)
        log("tooltip: %s", tooltip, sender=self) 

    def __on_synchronisation_done(self):
        # this might propably never appends so long gPodder synchronizes in a modal windows
        self.send_notification(_('Your device has been updated by gPodder.'), _('Operation finished'))
        self.set_status()
        
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

