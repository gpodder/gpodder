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
import datetime

from gpodder.liblogger import log
from gpodder.libgpodder import gl
from gpodder.libpodcasts import podcastItem

try:
    import pynotify
    have_pynotify = True
except:
    log('Cannot find pynotify. Please install the python-notify package.')
    log('Notification bubbles have been disabled.')
    have_pynotify = False

from gpodder import services
from gpodder import util
from gpodder import draw

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
    STATUS_UPDATING_FEED_CACHE = (_('Looking for new episodes'), gtk.STOCK_FIND)
    STATUS_SYNCHRONIZING = (_('Synchronizing to player'), gtk.STOCK_REFRESH)
    STATUS_DELETING = (_('Cleaning files'), gtk.STOCK_DELETE)

    # actions: buttons within the notify bubble
    ACTION_SHOW = ('show', _('Show'))
    ACTION_QUIT = ('quit', _('Quit gPodder'))
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
        self.__synchronisation_device = None
        self.__download_start_time = None

        self.__previous_notification = []

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

        self.connect('activate', self.__on_left_click)
        menu = self.__create_context_menu()
        self.connect('popup-menu', self.__on_right_click, menu)
        self.set_visible(True)

        # initialise pynotify
        if have_pynotify:
            if not pynotify.init('gPodder'):
                log('Error: unable to initialise pynotify', sender=self)

        # Register with the download status manager
        dl_man = services.download_status_manager
        dl_man.register('progress-changed', self.__on_download_progress_changed)
        dl_man.register('download-complete', self.__on_download_complete)
        
    def __create_context_menu(self):
        # build and connect the popup menu
        menu = gtk.Menu()
        menuItem = gtk.ImageMenuItem(_("Check for new episodes"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_FIND, gtk.ICON_SIZE_MENU))
        # connect the "on_itemUpdate_activate" with the parameter notify_no_new_episodes set to True
        menuItem.connect('activate',  self.__gpodder.on_itemUpdate_activate, True)
        menu.append(menuItem)
        
        menuItem = gtk.ImageMenuItem(_("Download all new episodes"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_DOWN, gtk.ICON_SIZE_MENU))
        menuItem.connect('activate',  self.__gpodder.on_itemDownloadAllNew_activate)
        menu.append(menuItem)

        # menus's label will adapt to the synchronisation device name
        if gl.config.device_type != 'none':
            sync_label = _('Synchronize to %s') % (gl.get_device_name(),)
            menuItem = gtk.ImageMenuItem(sync_label)
            menuItem.set_sensitive(gl.config.device_type != 'none')
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
        
        return menu        

    def __on_exit_callback(self, widget, *args):
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

    def __on_download_complete(self, episode):
        """Remember finished downloads
        """
        self.__finished_downloads.append(episode)

    def __on_download_progress_changed( self, count, percentage):
        """ callback by download manager during dowloading.
        It updates the tooltip with information on how many
        files are dowloaded and the percentage of dowload
        """

        tooltip = []
        if count > 0:
            self.__is_downloading = True
            if not self.__download_start_time:
                self.__download_start_time = datetime.datetime.now()
            if count == 1:
                tooltip.append(_('downloading one episode'))
            else:
                tooltip.append(_('downloading %d episodes')%count)

            tooltip.append(' (%d%%)'%percentage)

            if percentage <> 0:
                date_diff = datetime.datetime.now() - self.__download_start_time
                estim = date_diff.seconds * 100 // percentage - date_diff.seconds
                tooltip.append('\n' + _('estimated remaining time: '))
                tooltip.append(util.format_seconds_to_hour_min_sec(estim))
                
            if len(self.__finished_downloads) > 0:
                tooltip.append(self.format_episode_list(self.__finished_downloads, _('Finished downloads:')))

            self.set_status(self.STATUS_DOWNLOAD_IN_PROGRESS, ''.join(tooltip))
            
            self.progress_bar(float(percentage)/100.)
        else:
            self.__is_downloading = False
            self.__download_start_time = None
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
            self.send_notification(message, _('gPodder downloads finished'))
 
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
        elif action=='keep_dowloading':
            pass
        elif action=='force_quit':
            self.__gpodder.close_gpodder()
        elif action=='download':
            self.__gpodder.on_itemDownloadAllNew_activate(self.__gpodder)
        else:
            log("don't know what to do with action %s" % action, sender = self)
            
    def __is_notification_on(self):
        # tray icon not visible or notifications disabled
        if not self.get_visible() or not gl.config.enable_notifications:
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

    def format_episode_list(self, episode_list, caption=''):
        """
        Format a list of episodes for tooltips and notifications
        Return a listing of episodes title separated by a line break.
        Long title are troncated: "xxxx...xxxx"
        If the list is too long, it is cut and the string "x others episodes" is append
        
        episode_list
            can be either a list containing podcastItem objects 
            or a list of strings of episode's title.

        return
            the formatted list of episodes as a string
        """
        
        MAX_EPISODES = 10
        MAX_TITLE_LENGTH = 100

        result = []
        result.append('\n%s' % caption)
        for episode in episode_list[:min(len(episode_list),MAX_EPISODES)]:
            if isinstance(episode, podcastItem): 
                episode_title = episode.title
            else:
                episode_title = episode
            if len(episode_title) < MAX_TITLE_LENGTH:
                title = episode_title
            else:
                middle = (MAX_TITLE_LENGTH/2)-2
                title = '%s...%s' % (episode_title[0:middle], episode_title[-middle:])
            result.append('\n%s' % title)
 
        more_episodes = len(episode_list) - MAX_EPISODES
        if more_episodes > 0:
            result.append('\n(...')
            if more_episodes == 1:
                result.append(_('one more episode'))
            else:
                result.append(_('%d more episodes') % more_episodes)
            result.append('...)')

        return ''.join(result)
    
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
        
    def __on_synchronisation_progress(self, pos, max):
        self.__sync_progress = _('%d of %d done') % (pos, max)

    def __on_synchronisation_status(self, status):
        tooltip = _('%s\n%s') % (status, self.__sync_progress)
        self.set_status(self.STATUS_SYNCHRONIZING, tooltip)
        log("tooltip: %s", tooltip, sender=self) 

    def __on_synchronisation_done(self):
        if self.__gpodder.minimized:
            # this might propably never appends so long gPodder synchronizes in a modal windows
            self.send_notification(_('Your device has been updated by gPodder.'), _('Operation finished'))
        self.set_status()
        
    def progress_bar(self, ratio):
        """
        draw a progress bar on top of the tray icon.
        Be sure to call this method the first time with ratio=0
        in order to initialise background image
            
        ratio
            value between 0 and 1 (inclusive) indicating the ratio 
            of the progress bar to be drawn
                
        """

        # Only update in 3-percent-steps to save some resources
        if abs(ratio-self.__last_ratio) < 0.03 and ratio > self.__last_ratio:
            return

        icon = self.__current_pixbuf.copy()
        progressbar = draw.progressbar_pixbuf(icon.get_width(), icon.get_height(), ratio)
        progressbar.composite(icon, 0, 0, icon.get_width(), icon.get_height(), 0, 0, 1, 1, gtk.gdk.INTERP_NEAREST, 255)
        
        self.set_from_pixbuf(icon)
        self.__last_ratio = ratio

