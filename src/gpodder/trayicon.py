# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (C) 2005-2007 Thomas Perl <thp at perli.net>
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

from gpodder.liblogger import log

try:
    import pynotify
    have_pynotify = True
except:
    log('Cannot find pynotify. Please install the python-notify package.')
    log('Notification bubbles have been disabled.')
    have_pynotify = False

from gpodder import services
from gpodder import util

from libgpodder import gPodderLib

class GPodderStatusIcon(gtk.StatusIcon):
    """ this class display a status icon in the system tray
    this icon serves to show or hide gPodder, notify dowload status
    and provide a popupmenu for quick acces to some
    gPodder functionalities

    author: Jérôme Chabod <jerome.chabod at ifrance.com>
    01/01/2008
    """

    DEFAULT_TOOLTIP = _('gPodder media aggregator')

    # status: they are displayed as tooltip and add a small icon to the main icon
    STATUS_DOWNLOAD_IN_PROGRESS = (_('Downloading episodes'), gtk.STOCK_GO_DOWN)
    STATUS_UPDATING_FEED_CACHE = (_('Looking for new episodes'), gtk.STOCK_FIND)
    STATUS_SYNCHRONIZING = (_('Synchronizing to player'), gtk.STOCK_REFRESH)
    STATUS_DELETING = (_('Cleaning files'), gtk.STOCK_DELETE)

    # actions: buttons within the notify bubble
    ACTION_SHOW = ('show', _('Show'))
    ACTION_QUIT = ('quit', _('Quit gPodder'))
    ACTION_IGNORE = ('ignore', _('Ignore'))
    ACTION_FORCE_EXIT = ('force_quit', _('Quit anyway'))
    ACTION_KEEP_DOWLOADING = ('keep_dowloading', _('Keep dowloading'))
    ACTION_START_DOWNLOAD = ('download', _('Download'))
    
    def __init__(self, gpodder, icon_filename):
        gtk.StatusIcon.__init__(self)
        log('Creating tray icon', sender=self)
        
        self.__gpodder = gpodder
        self.__finished_downloads = []
        self.__icon_cache = {}
        self.__icon_filename = icon_filename
        self.__current_icon = -1
        self.__is_downloading = False

        self.__previous_notification = []

        self.__is_downloading = False
        # this list store url successfully downloaded for notification
        self.__url_successfully_downloaded = []

        # try getting the icon
        try:
            self.__icon = gtk.gdk.pixbuf_new_from_file(self.__icon_filename)
        except Exception, exc:
            log('Warning: Cannot load gPodder icon, will use the default icon (%s)', exc, sender=self)
            self.__icon = gtk.icon_theme_get_default().load_icon(gtk.STOCK_DIALOG_QUESTION, 30, 30)

        # Reset trayicon (default icon, default tooltip)
        self.set_status()

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
        menuItem = gtk.ImageMenuItem(_("Synchronize to ipod/player"))
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
        menuItem = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        menuItem.connect('activate',  self.__on_exit_callback)
        menu.append(menuItem)

        self.connect('activate', self.__on_left_click)
        self.connect('popup-menu', self.__on_right_click, menu)
        self.set_visible(True)

        # initialise pynotify
        if have_pynotify:
            if not pynotify.init('gPodder'):
                log('Error: unable to initialise pynotify', sender=self)

        # Register with the download status manager
        services.download_status_manager.register('progress-changed', self.__download_progress_changed)
        services.download_status_manager.register('download-complete', self.__download_complete)

    def __on_exit_callback(self, widget, *args):
        gl = gPodderLib()
        if  self.__is_downloading and self.__is_notification_on():
            self.send_notification(_("gPodder is downloading episodes\ndo you want to exit anyway?"""), "gPodder",[self.ACTION_FORCE_EXIT, self.ACTION_KEEP_DOWLOADING])
        else:
            self.__gpodder.close_gpodder()

    def __on_show_previous_message_callback(self, widget, *args):
        p = self.__previous_notification
        if p != []:
            self.send_notification(p[0], p[1], p[2], p[3])

    def __on_right_click(self, widget, button, time, data=None):
        """Open popup menu on right-click
        """
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


    def __download_complete(self, episode):
        """Remember finished downloads
        """
        self.__finished_downloads.append(episode)

    def __download_progress_changed( self, count, percentage):
        """ callback by download manager during dowloading.
        It updates the tooltip with information on how many
        files are dowloaded and the percentage of dowload
        """

        tooltip = []
        if count > 0:
            self.__is_downloading = True
            if count == 1:
                tooltip.append(_('downloading one episode'))
            else:
                tooltip.append(_('downloading %d episodes')%count)

            tooltip.append(' (%d%%)'%percentage)

            if len(self.__finished_downloads) > 0:
                tooltip.append(self.format_episode_list(self.__finished_downloads, _('Finished downloads:')))

            self.set_status(self.STATUS_DOWNLOAD_IN_PROGRESS, ''.join(tooltip))
        else:
            self.__is_downloading = False
            self.set_status()
            num = len(self.__finished_downloads)
            if num == 1:
                title = _('one episodes downloaded:')
            elif num > 1:
                title = _('%d episodes downloaded:')%num
            else:
                # No episodes have finished downloading, ignore
                return

            message = self.format_episode_list(self.__finished_downloads, title)
            self.send_notification(message, _('gPodder downloads finished'), [self.ACTION_SHOW, self.ACTION_QUIT, self.ACTION_IGNORE])
 
            self.__finished_downloads = []
 
    def __get_status_icon(self, icon):
        if icon in self.__icon_cache:
            return self.__icon_cache[icon]

        try:
            new_icon = self.__icon.copy()
            emblem = gtk.icon_theme_get_default().load_icon(icon, int(new_icon.get_width()/1.5), 0)
            size = emblem.get_width()
            pos = new_icon.get_width()-size
            emblem.composite(new_icon, pos, pos, size, size, pos, pos, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)
            self.__icon_cache[icon] = new_icon
            return new_icon
        except Exception, exc:
            pass

        log('Warning: Cannot create status icon: %s', icon, sender=self)
        return self.__icon

    def __action_callback(self, n, action):
        """ call back when a button is clicked in a notify bubble """
        log("action triggered %s", action, sender = self)
        n.close()
        if action=='show': 
            self.__gpodder.uniconify_main_window()
        elif action=='quit':
            util.idle_add(self.__gpodder.close_gpodder)
        elif action=='ignore':
            pass
        elif action=='keep_dowloading':
            pass
        elif action=='force_quit':
            self.__gpodder.close_gpodder()
        elif action=='download':
            self.__gpodder.on_itemDownloadAllNew_activate(self.__gpodder)
        else:
            log("don't know what to do with action %s" % action, sender = self)
            
    def __is_notification_on(self):
        gl = gPodderLib()
        # tray icon not visible or notifications disabled
        if not self.get_visible() or gl.config.disable_notifications:
            return False
        return True
    
    def destroy(self, n=None, action=None):
        gtk.main_quit()
        
    def send_notification( self, message, title = "gPodder", actions = [], is_error=False):
        if not self.__is_notification_on(): return

        message = message.strip()
        log('Notification: %s', message, sender=self)
        if have_pynotify:
            notification = pynotify.Notification(title, message, self.__icon_filename)
            if is_error: notification.set_urgency(pynotify.URGENCY_CRITICAL)
            try:
                notification.attach_to_status_icon(self)
            except:
                log('Warning: Cannot attach notification to status icon.', sender=self)
            notification.connect('closed', self.destroy)
            for action in actions:
                notification.add_action(action[0], action[1], self.__action_callback)
            if not notification.show():
                log("Error: enable to send notification %s", message)
            self.__previous_notification=[message, title, actions, is_error]
            self.menuItem_previous_msg.set_sensitive(True)
            gtk.main()
        
    def set_status(self, status=None, tooltip=None):
        #TODO: add a stack for icons (an update can occure while dowloading and ending before)
        if status is None:
            if tooltip is None:
                tooltip = self.DEFAULT_TOOLTIP
            else:
                tooltip = 'gPodder - %s' % tooltip
            if self.__current_icon is not None:
                self.set_from_pixbuf(self.__icon)
                self.__current_icon = None
        else:
            (status_tooltip, icon) = status
            if tooltip is None:
                tooltip = 'gPodder - %s' % status_tooltip
            else:
                tooltip = 'gPodder - %s' % tooltip
            if self.__current_icon != icon:
                self.set_from_pixbuf(self.__get_status_icon(icon))
                self.__current_icon = icon
        self.set_tooltip(tooltip)

    def format_episode_list(self, episode_list, caption=''):
        """ format a list of episodes for displaying
            in tooltip or notification.
            return the formated string
        """
        MAX_EPISODES = 10
        MAX_TITLE_LENGTH = 100

        result = []
        result.append('\n%s'%caption)
        for episode in episode_list[:min(len(episode_list),MAX_EPISODES)]:
            if len(episode) < MAX_TITLE_LENGTH:
                title = episode
            else:
                middle = (MAX_TITLE_LENGTH/2)-2
                title = '%s...%s'%( episode[0:middle], episode[-middle:])
            result.append('\n%s'%title)
 
        more_episodes = len(episode_list) - MAX_EPISODES
        if more_episodes > 0:
            result.append('\n(...')
            if more_episodes == 1:
                result.append(_('one more episode'))
            else:
                result.append(_('%d more episodes') % more_episodes)
            result.append('...)')

        return ''.join(result)
    
