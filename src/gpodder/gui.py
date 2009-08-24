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

import os
import gtk
import gtk.gdk
import gobject
import pango
import sys
import shutil
import subprocess
import glob
import time
import urllib
import urllib2
import datetime
import fnmatch
import tempfile
import collections

from xml.sax import saxutils

from threading import Thread
from string import strip

import gpodder

try:
    import dbus
    import dbus.service
    import dbus.mainloop
    import dbus.glib
except ImportError:
    # Mock the required D-Bus interfaces with no-ops (ugly? maybe.)
    class dbus:
        class SessionBus:
            def __init__(self, *args, **kwargs):
                pass
        class glib:
            class DBusGMainLoop:
                pass
        class service:
            @staticmethod
            def method(interface):
                return lambda x: x
            class BusName:
                def __init__(self, *args, **kwargs):
                    pass
            class Object:
                def __init__(self, *args, **kwargs):
                    pass


from gpodder import feedcore
from gpodder import util
from gpodder import opml
from gpodder import services
from gpodder import sync
from gpodder import download
from gpodder import my
from gpodder.liblogger import log
from gpodder import youtube

_ = gpodder.gettext

try:
    from gpodder import trayicon
    have_trayicon = True
except Exception, exc:
    log('Warning: Could not import gpodder.trayicon.', traceback=True)
    log('Warning: This probably means your PyGTK installation is too old!')
    have_trayicon = False

from gpodder.model import PodcastChannel
from gpodder.dbsqlite import Database

from gpodder.gtkui.base import GtkBuilderWidget
from gpodder.gtkui.model import PodcastListModel
from gpodder.gtkui.model import EpisodeListModel
from gpodder.gtkui.opml import OpmlListModel
from gpodder.gtkui.config import UIConfig
from gpodder.gtkui.download import DownloadStatusModel
from gpodder.gtkui.services import DependencyModel
from gpodder.gtkui.services import CoverDownloader
from gpodder.gtkui.widgets import SimpleMessageArea
from gpodder.gtkui.desktopfile import UserAppsReader

from gpodder.gtkui.interface.common import BuilderWidget
from gpodder.gtkui.interface.channel import gPodderChannel
from gpodder.gtkui.interface.addpodcast import gPodderAddPodcast

if gpodder.interface == gpodder.GUI:
    from gpodder.gtkui.interface.preferences import gPodderPreferences
else:
    from gpodder.gtkui.maemo.preferences import gPodderDiabloPreferences as gPodderPreferences

from gpodder.gtkui.interface.shownotes import gPodderShownotes
from gpodder.gtkui.interface.syncprogress import gPodderSyncProgress

if gpodder.interface == gpodder.GUI:
    WEB_BROWSER_ICON = 'web-browser'
elif gpodder.interface == gpodder.MAEMO:
    import hildon
    WEB_BROWSER_ICON = 'qgn_toolb_browser_web'

app_authors = [
    _('Current maintainer:'), 'Thomas Perl <thpinfo.com>',
    '',
    _('Patches, bug reports and donations by:'), 'Adrien Beaucreux',
    'Alain Tauch', 'Alex Ghitza', 'Alistair Sutton', 'Anders Kvist', 'Andrei Dolganov', 'Andrew Bennett', 'Andy Busch',
    'Antonio Roversi', 'Aravind Seshadri', 'Atte André Jensen', 'audioworld', 
    'Bastian Staeck', 'Bernd Schlapsi', 'Bill Barnard', 'Bill Peters', 'Bjørn Rasmussen', 'Camille Moncelier', 'Casey Watson',
    'Carlos Moffat', 'Chris Arnold', 'Chris Moffitt', 'Clark Burbidge', 'Corey Goldberg', 'corq', 'Cory Albrecht', 'daggpod', 'Daniel Ramos',
    'David Spreen', 'Doug Hellmann', 'Edouard Pellerin', 'Fabio Fiorentini', 'FFranci72', 'Florian Richter', 'Frank Harper',
    'Franz Seidl', 'FriedBunny', 'Gerrit Sangel', 'Gilles Lehoux', 'Götz Waschk',
    'Haim Roitgrund', 'Heinz Erhard', 'Hex', 'Holger Bauer', 'Holger Leskien', 'Iwan van der Kleijn', 'Jens Thiele',
    'Jérôme Chabod', 'Jerry Moss',
    'Jessica Henline', 'Jim Nygård', 'João Trindade', 'Joel Calado', 'John Ferguson', 
    'José Luis Fustel', 'Joseph Bleau', 'Julio Acuña', 'Junio C Hamano',
    'Jürgen Schinker', 'Justin Forest',
    'Konstantin Ryabitsev', 'Leonid Ponomarev', 'Marco Antonio Villegas Vega', 'Marcos Hernández', 'Mark Alford', 'Markus Golser', 'Mehmet Nur Olcay', 'Michael Salim',
    'Mika Leppinen', 'Mike Coulson', 'Mikolaj Laczynski', 'Morten Juhl-Johansen Zölde-Fejér', 'Mykola Nikishov', 'narf',
    'Nick L.', 'Nicolas Quienot', 'Ondrej Vesely', 
    'Ortwin Forster', 'Paul Elliot', 'Paul Rudkin',
    'Pavel Mlčoch', 'Peter Hoffmann', 'PhilF', 'Philippe Gouaillier', 'Pieter de Decker',
    'Preben Randhol', 'Rafael Proença', 'R.Bell', 'red26wings', 'Richard Voigt',
    'Robert Young', 'Roel Groeneveld', 'Romain Janvier',
    'Scott Wegner', 'Sebastian Krause', 'Seth Remington', 'Shane Donohoe', 'Silvio Sisto', 'SPGoetze',
    'S. Rust',
    'Stefan Lohmaier', 'Stephan Buys', 'Steve McCarthy', 'Stylianos Papanastasiou', 'Teo Ramirez',
    'Thomas Matthijs', 'Thomas Mills Hinkle', 'Thomas Nilsson', 
    'Tim Michelsen', 'Tim Preetz', 'Todd Zullinger', 'Tomas Matheson', 'Ville-Pekka Vainio', 'Vitaliy Bondar', 'VladDrac',
    'Vladimir Zemlyakov', 'Wilfred van Rooijen',
    '',
    'List may be incomplete - please contact me.'
]


class gPodder(BuilderWidget, dbus.service.Object):
    finger_friendly_widgets = ['btnCancelFeedUpdate', 'label2', 'labelDownloads', 'btnCleanUpDownloads']
    ENTER_URL_TEXT = _('Enter podcast URL...')
    APPMENU_ACTIONS = ('itemUpdate', 'itemDownloadAllNew', 'itemPreferences')
    TREEVIEW_WIDGETS = ('treeAvailable', 'treeChannels', 'treeDownloads')

    def __init__(self, bus_name, config):
        dbus.service.Object.__init__(self, object_path=gpodder.dbus_gui_object_path, bus_name=bus_name)
        self.db = Database(gpodder.database_file)
        self.config = config
        BuilderWidget.__init__(self, None)
    
    def new(self):
        if gpodder.interface == gpodder.MAEMO:
            # Maemo-specific changes to the UI
            gpodder.icon_file = gpodder.icon_file.replace('.svg', '.png')
            
            self.app = hildon.Program()
            gtk.set_application_name('gPodder')
            self.window = hildon.Window()
            self.window.connect('delete-event', self.on_gPodder_delete_event)
            self.window.connect('window-state-event', self.window_state_event)
    
            self.itemUpdateChannel.set_visible(True)
            
            # Remove old toolbar from its parent widget
            self.toolbar.get_parent().remove(self.toolbar)

            toolbar = gtk.Toolbar()
            toolbar.set_style(gtk.TOOLBAR_BOTH_HORIZ)

            self.btnUpdateFeeds.get_parent().remove(self.btnUpdateFeeds)

            self.btnUpdateFeeds = gtk.ToolButton(gtk.image_new_from_stock(gtk.STOCK_REFRESH, gtk.ICON_SIZE_SMALL_TOOLBAR), _('Update all'))
            self.btnUpdateFeeds.set_is_important(True)
            self.btnUpdateFeeds.connect('clicked', self.on_itemUpdate_activate)
            toolbar.insert(self.btnUpdateFeeds, -1)
            self.btnUpdateFeeds.show_all()

            self.btnUpdateSelectedFeed = gtk.ToolButton(gtk.image_new_from_stock(gtk.STOCK_REFRESH, gtk.ICON_SIZE_SMALL_TOOLBAR), _('Update selected'))
            self.btnUpdateSelectedFeed.set_is_important(True)
            self.btnUpdateSelectedFeed.connect('clicked', self.on_itemUpdateChannel_activate)
            toolbar.insert(self.btnUpdateSelectedFeed, -1)
            self.btnUpdateSelectedFeed.show_all()

            self.toolFeedUpdateProgress = gtk.ToolItem()
            self.pbFeedUpdate.reparent(self.toolFeedUpdateProgress)
            self.toolFeedUpdateProgress.set_expand(True)
            toolbar.insert(self.toolFeedUpdateProgress, -1)
            self.toolFeedUpdateProgress.hide()

            self.btnCancelFeedUpdate = gtk.ToolButton(gtk.STOCK_CLOSE)
            self.btnCancelFeedUpdate.connect('clicked', self.on_btnCancelFeedUpdate_clicked)
            toolbar.insert(self.btnCancelFeedUpdate, -1)
            self.btnCancelFeedUpdate.hide()

            self.toolbarSpacer = gtk.SeparatorToolItem()
            self.toolbarSpacer.set_draw(False)
            self.toolbarSpacer.set_expand(True)
            toolbar.insert(self.toolbarSpacer, -1)
            self.toolbarSpacer.show()

            self.wNotebook.set_show_tabs(False)
            self.tool_downloads = gtk.ToggleToolButton(gtk.STOCK_GO_DOWN)
            self.tool_downloads.connect('toggled', self.on_tool_downloads_toggled)
            self.tool_downloads.set_label(_('Downloads'))
            self.tool_downloads.set_is_important(True)
            toolbar.insert(self.tool_downloads, -1)
            self.tool_downloads.show_all()

            self.toolPreferences = gtk.ToolButton(gtk.STOCK_PREFERENCES)
            self.toolPreferences.connect('clicked', self.on_itemPreferences_activate)
            toolbar.insert(self.toolPreferences, -1)
            self.toolPreferences.show()

            self.toolQuit = gtk.ToolButton(gtk.STOCK_QUIT)
            self.toolQuit.connect('clicked', self.on_gPodder_delete_event)
            toolbar.insert(self.toolQuit, -1)
            self.toolQuit.show()

            # Add and replace toolbar with our new one
            toolbar.show()
            self.window.add_toolbar(toolbar)
            self.toolbar = toolbar
         
            self.app.add_window(self.window)
            self.vMain.reparent(self.window)
            self.gPodder = self.window
            
            # Reparent the main menu
            menu = gtk.Menu()
            for child in self.mainMenu.get_children():
                child.get_parent().remove(child)
                menu.append(self.set_finger_friendly(child))
            menu.append(self.set_finger_friendly(self.itemQuit.create_menu_item()))

            if hasattr(hildon, 'AppMenu'):
                # Maemo 5 - use the new AppMenu with Buttons
                self.appmenu = hildon.AppMenu()
                for action_name in self.APPMENU_ACTIONS:
                    action = getattr(self, action_name)
                    b = gtk.Button('')
                    action.connect_proxy(b)
                    self.appmenu.append(b)
                b = gtk.Button(_('Classic menu'))
                b.connect('clicked', lambda b: menu.popup(None, None, None, 1, 0))
                self.appmenu.append(b)
                self.window.set_app_menu(self.appmenu)
            else:
                # Maemo 4 - just "reparent" the menu to the hildon window
                self.window.set_menu(menu)
         
            self.mainMenu.destroy()
            self.window.show()
            
            # do some widget hiding
            self.itemTransferSelected.set_visible(False)
            self.item_email_subscriptions.set_visible(False)
            self.menuView.set_visible(False)
            
            # get screen real estate
            self.hboxContainer.set_border_width(0)

            # Offer importing of videocenter podcasts
            if os.path.exists(os.path.expanduser('~/videocenter')):
                self.item_upgrade_from_videocenter.set_visible(True)

        self.gPodder.connect('key-press-event', self.on_key_press)
        self.bluetooth_available = util.bluetooth_available()

        if gpodder.win32:
            # FIXME: Implement e-mail sending of list in win32
            self.item_email_subscriptions.set_sensitive(False)

        if self.config.show_url_entry_in_podcast_list:
            self.hboxAddChannel.show()

        if not gpodder.interface == gpodder.MAEMO and not self.config.show_toolbar:
            self.toolbar.hide()

        self.config.add_observer(self.on_config_changed)
        self.default_entry_text_color = self.entryAddChannel.get_style().text[gtk.STATE_NORMAL]
        self.entryAddChannel.connect('focus-in-event', self.entry_add_channel_focus)
        self.entryAddChannel.connect('focus-out-event', self.entry_add_channel_unfocus)
        self.entry_add_channel_unfocus(self.entryAddChannel, None)
        
        self.uar = None
        self.tray_icon = None
        self.episode_shownotes_window = None

        self.download_status_model = DownloadStatusModel()
        self.download_queue_manager = download.DownloadQueueManager(self.config)

        self.fullscreen = False
        self.minimized = False
        self.gPodder.connect('window-state-event', self.window_state_event)
        
        self.show_hide_tray_icon()

        self.itemShowToolbar.set_active(self.config.show_toolbar)
        self.itemShowDescription.set_active(self.config.episode_list_descriptions)
                   
        self.config.connect_gtk_window(self.gPodder, 'main_window')
        self.config.connect_gtk_paned( 'paned_position', self.channelPaned)

        self.config.connect_gtk_spinbutton('max_downloads', self.spinMaxDownloads)
        self.config.connect_gtk_togglebutton('max_downloads_enabled', self.cbMaxDownloads)
        self.config.connect_gtk_spinbutton('limit_rate_value', self.spinLimitDownloads)
        self.config.connect_gtk_togglebutton('limit_rate', self.cbLimitDownloads)

        # Then the amount of maximum downloads changes, notify the queue manager
        changed_cb = lambda spinbutton: self.download_queue_manager.spawn_and_retire_threads()
        self.spinMaxDownloads.connect('value-changed', changed_cb)

        self.default_title = None
        if gpodder.__version__.rfind('git') != -1:
            self.set_title('gPodder %s' % gpodder.__version__)
        else:
            title = self.gPodder.get_title()
            if title is not None:
                self.set_title(title)
            else:
                self.set_title(_('gPodder'))

        gtk.about_dialog_set_url_hook(lambda dlg, link, data: util.open_website(link), None)

        # Set up podcast channel tree view widget
        self.treeChannels.set_enable_search(True)
        self.treeChannels.set_search_column(PodcastListModel.C_TITLE)
        self.treeChannels.set_headers_visible(False)

        iconcolumn = gtk.TreeViewColumn('')
        iconcell = gtk.CellRendererPixbuf()
        iconcolumn.pack_start(iconcell, False)
        iconcolumn.add_attribute(iconcell, 'pixbuf', PodcastListModel.C_COVER)
        self.treeChannels.append_column(iconcolumn)

        namecolumn = gtk.TreeViewColumn('')
        namecell = gtk.CellRendererText()
        namecell.set_property('ellipsize', pango.ELLIPSIZE_END)
        namecolumn.pack_start(namecell, True)
        namecolumn.add_attribute(namecell, 'markup', PodcastListModel.C_DESCRIPTION)

        iconcell = gtk.CellRendererPixbuf()
        iconcell.set_property('xalign', 1.0)
        namecolumn.pack_start(iconcell, False)
        namecolumn.add_attribute(iconcell, 'pixbuf', PodcastListModel.C_PILL)
        namecolumn.add_attribute(iconcell, 'visible', PodcastListModel.C_PILL_VISIBLE)
        self.treeChannels.append_column(namecolumn)

        self.cover_downloader = CoverDownloader()

        # Generate list models for podcasts and their episodes
        self.podcast_list_model = PodcastListModel(self.config.podcast_list_icon_size, self.cover_downloader)
        self.treeChannels.set_model(self.podcast_list_model)

        self.episode_list_model = EpisodeListModel()
        self.treeAvailable.set_model(self.episode_list_model)

        # enable alternating colors hint
        self.treeAvailable.set_rules_hint( True)
        self.treeChannels.set_rules_hint( True)

        # connect to tooltip signals
        try:
            self.treeChannels.set_property('has-tooltip', True)
            self.treeChannels.connect('query-tooltip', self.treeview_channels_query_tooltip)
            self.treeAvailable.set_property('has-tooltip', True)
            self.treeAvailable.connect('query-tooltip', self.treeview_episodes_query_tooltip)
        except:
            log('I cannot set has-tooltip/query-tooltip (need at least PyGTK 2.12)', sender = self)
        self.last_tooltip_channel = None
        self.last_tooltip_episode = None
        self.podcast_list_can_tooltip = True
        self.episode_list_can_tooltip = True

        self.currently_updating = False

        # Add our context menu to treeAvailable
        if gpodder.interface == gpodder.MAEMO:
            self.treeview_available_buttonpress = (0, 0)
            self.treeAvailable.connect('button-press-event', self.treeview_button_savepos)
            self.treeAvailable.connect('button-release-event', self.treeview_button_pressed)

            self.treeview_channels_buttonpress = (0, 0)
            self.treeChannels.connect('button-press-event', self.treeview_channels_button_pressed)
            self.treeChannels.connect('button-release-event', self.treeview_channels_button_released)
        else:
            self.treeAvailable.connect('button-press-event', self.treeview_button_pressed)
            self.treeChannels.connect('button-press-event', self.treeview_channels_button_pressed)

        self.treeDownloads.connect('button-press-event', self.treeview_downloads_button_pressed)

        iconcell = gtk.CellRendererPixbuf()
        if gpodder.interface == gpodder.MAEMO:
            iconcell.set_fixed_size(-1, 52)
            status_column_label = ''
        else:
            status_column_label = _('Status')
        iconcolumn = gtk.TreeViewColumn(status_column_label, iconcell, pixbuf=EpisodeListModel.C_STATUS_ICON)

        namecell = gtk.CellRendererText()
        namecell.set_property('ellipsize', pango.ELLIPSIZE_END)
        namecolumn = gtk.TreeViewColumn(_('Episode'), namecell, markup=EpisodeListModel.C_DESCRIPTION)
        namecolumn.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        namecolumn.set_resizable(True)
        namecolumn.set_expand(True)

        sizecell = gtk.CellRendererText()
        sizecolumn = gtk.TreeViewColumn(_('Size'), sizecell, text=EpisodeListModel.C_FILESIZE_TEXT)

        releasecell = gtk.CellRendererText()
        releasecolumn = gtk.TreeViewColumn(_('Released'), releasecell, text=EpisodeListModel.C_PUBLISHED_TEXT)
        
        for itemcolumn in (iconcolumn, namecolumn, sizecolumn, releasecolumn):
            itemcolumn.set_reorderable(gpodder.interface != gpodder.MAEMO)
            self.treeAvailable.append_column(itemcolumn)

        if gpodder.interface == gpodder.MAEMO:
            # Due to screen space contraints, we
            # hide these columns here by default
            self.column_size = sizecolumn
            self.column_released = releasecolumn
            self.column_released.set_visible(False)
            self.column_size.set_visible(False)

        # enable search in treeavailable
        self.treeAvailable.set_search_equal_func( self.treeAvailable_search_equal)

        # on Maemo 5, we need to set hildon-ui-mode of TreeView widgets to 1
        if gpodder.interface == gpodder.MAEMO:
            HUIM = 'hildon-ui-mode'
            if HUIM in [p.name for p in gobject.list_properties(gtk.TreeView)]:
                for treeview_name in self.TREEVIEW_WIDGETS:
                    treeview = getattr(self, treeview_name)
                    treeview.set_property(HUIM, 1)

        # enable multiple selection support
        if gpodder.interface == gpodder.MAEMO:
            self.treeAvailable.get_selection().set_mode(gtk.SELECTION_SINGLE)
        else:
            self.treeAvailable.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.treeDownloads.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

        if hasattr(self.treeDownloads, 'set_rubber_banding'):
            # Available in PyGTK 2.10 and above
            self.treeDownloads.set_rubber_banding(True)
        
        # columns and renderers for "download progress" tab
        # First column: [ICON] Episodename
        column = gtk.TreeViewColumn(_('Episode'))

        cell = gtk.CellRendererPixbuf()
        if gpodder.interface == gpodder.MAEMO:
            cell.set_property('stock-size', gtk.ICON_SIZE_DIALOG)
        else:
            cell.set_property('stock-size', gtk.ICON_SIZE_MENU)
        column.pack_start(cell, expand=False)
        column.add_attribute(cell, 'stock-id', \
                DownloadStatusModel.C_ICON_NAME)

        cell = gtk.CellRendererText()
        cell.set_property('ellipsize', pango.ELLIPSIZE_END)
        column.pack_start(cell, expand=True)
        column.add_attribute(cell, 'text', DownloadStatusModel.C_NAME)

        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        column.set_resizable(True)
        column.set_expand(True)
        self.treeDownloads.append_column(column)

        # Second column: Progress
        column = gtk.TreeViewColumn(_('Progress'), gtk.CellRendererProgress(),
                value=DownloadStatusModel.C_PROGRESS, \
                text=DownloadStatusModel.C_PROGRESS_TEXT)
        self.treeDownloads.append_column(column)

        # Third column: Size
        if gpodder.interface != gpodder.MAEMO:
            column = gtk.TreeViewColumn(_('Size'), gtk.CellRendererText(),
                    text=DownloadStatusModel.C_SIZE_TEXT)
            self.treeDownloads.append_column(column)

        # Fourth column: Speed
        column = gtk.TreeViewColumn(_('Speed'), gtk.CellRendererText(),
                text=DownloadStatusModel.C_SPEED_TEXT)
        self.treeDownloads.append_column(column)

        # Fifth column: Status
        column = gtk.TreeViewColumn(_('Status'), gtk.CellRendererText(),
                text=DownloadStatusModel.C_STATUS_TEXT)
        self.treeDownloads.append_column(column)

        # After we've set up most of the window, show it :)
        if not gpodder.interface == gpodder.MAEMO:
            self.gPodder.show()

        if self.config.start_iconified:
            self.iconify_main_window()
            if self.tray_icon and self.config.minimize_to_tray:
                self.tray_icon.set_visible(False)

        self.cover_downloader.register('cover-available', self.cover_download_finished)
        self.cover_downloader.register('cover-removed', self.cover_file_removed)

        self.treeDownloads.set_model(self.download_status_model)
        self.download_tasks_seen = set()
        self.download_list_update_enabled = False
        self.last_download_count = 0
        
        #Add Drag and Drop Support
        flags = gtk.DEST_DEFAULT_ALL
        targets = [ ('text/plain', 0, 2), ('STRING', 0, 3), ('TEXT', 0, 4) ]
        actions = gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_COPY
        self.treeChannels.drag_dest_set( flags, targets, actions)
        self.treeChannels.connect( 'drag_data_received', self.drag_data_received)

        # Subscribed channels
        self.active_channel = None
        self.channels = PodcastChannel.load_from_db(self.db, self.config.download_dir)
        self.channel_list_changed = True
        self.update_podcasts_tab()

        # load list of user applications for audio playback
        self.user_apps_reader = UserAppsReader(['audio', 'video'])
        Thread(target=self.read_apps).start()

        # Set the "Device" menu item for the first time
        self.update_item_device()

        # Last folder used for saving episodes
        self.folder_for_saving_episodes = None

        # Now, update the feed cache, when everything's in place
        self.btnUpdateFeeds.show()
        self.updating_feed_cache = False
        self.feed_cache_update_cancelled = False
        self.update_feed_cache(force_update=self.config.update_on_startup)

        # Look for partial file downloads
        partial_files = glob.glob(os.path.join(self.config.download_dir, '*', '*.partial'))

        # Message area
        self.message_area = None

        resumable_episodes = []
        if len(partial_files) > 0:
            for f in partial_files:
                correct_name = f[:-len('.partial')] # strip ".partial"
                log('Searching episode for file: %s', correct_name, sender=self)
                found_episode = False
                for c in self.channels:
                    for e in c.get_all_episodes():
                        if e.local_filename(create=False, check_only=True) == correct_name:
                            log('Found episode: %s', e.title, sender=self)
                            resumable_episodes.append(e)
                            found_episode = True
                        if found_episode:
                            break
                    if found_episode:
                        break
                if not found_episode:
                    log('Partial file without episode: %s', f, sender=self)
                    util.delete_file(f)

            if len(resumable_episodes):
                self.download_episode_list_paused(resumable_episodes)
                self.message_area = SimpleMessageArea(_('There are unfinished downloads from your last session.\nPick the ones you want to continue downloading.'))
                self.vboxDownloadStatusWidgets.pack_start(self.message_area, expand=False)
                self.vboxDownloadStatusWidgets.reorder_child(self.message_area, 0)
                self.message_area.show_all()
                self.wNotebook.set_current_page(1)

            self.clean_up_downloads(delete_partial=False)
        else:
            self.clean_up_downloads(delete_partial=True)

        # Start the auto-update procedure
        self.auto_update_procedure(first_run=True)

        # Delete old episodes if the user wishes to
        if self.config.auto_remove_old_episodes:
            old_episodes = self.get_old_episodes()
            if len(old_episodes) > 0:
                self.delete_episode_list(old_episodes, confirm=False)
                self.updateComboBox()

        # First-time users should be asked if they want to see the OPML
        if len(self.channels) == 0:
            util.idle_add(self.on_itemUpdate_activate)

    def enable_download_list_update(self):
        if not self.download_list_update_enabled:
            gobject.timeout_add(1500, self.update_downloads_list)
            self.download_list_update_enabled = True

    def on_btnCleanUpDownloads_clicked(self, button):
        model = self.download_status_model

        all_tasks = [(gtk.TreeRowReference(model, row.path), row[0]) for row in model]
        changed_episode_urls = []
        for row_reference, task in all_tasks:
            if task.status in (task.DONE, task.CANCELLED, task.FAILED):
                model.remove(model.get_iter(row_reference.get_path()))
                try:
                    # We don't "see" this task anymore - remove it;
                    # this is needed, so update_episode_list_icons()
                    # below gets the correct list of "seen" tasks
                    self.download_tasks_seen.remove(task)
                except KeyError, key_error:
                    log('Cannot remove task from "seen" list: %s', task, sender=self)
                changed_episode_urls.append(task.url)
                # Tell the task that it has been removed (so it can clean up)
                task.removed_from_list()

        # Tell the podcasts tab to update icons for our removed podcasts
        self.update_episode_list_icons(changed_episode_urls)

        # Update the tab title and downloads list
        self.update_downloads_list()

    def on_tool_downloads_toggled(self, toolbutton):
        if toolbutton.get_active():
            self.wNotebook.set_current_page(1)
        else:
            self.wNotebook.set_current_page(0)

    def update_downloads_list(self):
        try:
            model = self.download_status_model

            downloading, failed, finished, queued, others = 0, 0, 0, 0, 0
            total_speed, total_size, done_size = 0, 0, 0

            # Keep a list of all download tasks that we've seen
            download_tasks_seen = set()

            # Remember the progress and speed for the episode that
            # has been opened in the episode shownotes dialog (if any)
            if self.episode_shownotes_window is not None:
                episode_window_episode = self.episode_shownotes_window.episode
                episode_window_progress = 0.0
                episode_window_speed = 0.0
            else:
                episode_window_episode = None

            # Do not go through the list of the model is not (yet) available
            if model is None:
                model = ()

            for row in model:
                self.download_status_model.request_update(row.iter)

                task = row[self.download_status_model.C_TASK]
                speed, size, status, progress = task.speed, task.total_size, task.status, task.progress

                total_size += size
                done_size += size*progress

                if episode_window_episode is not None and \
                        episode_window_episode.url == task.url:
                    episode_window_progress = progress
                    episode_window_speed = speed

                download_tasks_seen.add(task)

                if status == download.DownloadTask.DOWNLOADING:
                    downloading += 1
                    total_speed += speed
                elif status == download.DownloadTask.FAILED:
                    failed += 1
                elif status == download.DownloadTask.DONE:
                    finished += 1
                elif status == download.DownloadTask.QUEUED:
                    queued += 1
                else:
                    others += 1

            # Remember which tasks we have seen after this run
            self.download_tasks_seen = download_tasks_seen

            text = [_('Downloads')]
            if downloading + failed + finished + queued > 0:
                s = []
                if downloading > 0:
                    s.append(_('%d downloading') % downloading)
                if failed > 0:
                    s.append(_('%d failed') % failed)
                if finished > 0:
                    s.append(_('%d done') % finished)
                if queued > 0:
                    s.append(_('%d queued') % queued)
                text.append(' (' + ', '.join(s)+')')
            self.labelDownloads.set_text(''.join(text))

            if gpodder.interface == gpodder.MAEMO:
                sum = downloading + failed + finished + queued + others
                if sum:
                    self.tool_downloads.set_label(_('Downloads (%d)') % sum)
                else:
                    self.tool_downloads.set_label(_('Downloads'))

            title = [self.default_title]

            # We have to update all episodes/channels for which the status has
            # changed. Accessing task.status_changed has the side effect of
            # re-setting the changed flag, so we need to get the "changed" list
            # of tuples first and split it into two lists afterwards
            changed = [(task.url, task.podcast_url) for task in \
                    self.download_tasks_seen if task.status_changed]
            episode_urls = [episode_url for episode_url, channel_url in changed]
            channel_urls = [channel_url for episode_url, channel_url in changed]

            count = downloading + queued
            if count > 0:
                if count == 1:
                    title.append( _('downloading one file'))
                elif count > 1:
                    title.append( _('downloading %d files') % count)

                if total_size > 0:
                    percentage = 100.0*done_size/total_size
                else:
                    percentage = 0.0
                total_speed = util.format_filesize(total_speed)
                title[1] += ' (%d%%, %s/s)' % (percentage, total_speed)
                if self.tray_icon is not None:
                    # Update the tray icon status and progress bar
                    self.tray_icon.set_status(self.tray_icon.STATUS_DOWNLOAD_IN_PROGRESS, title[1])
                    self.tray_icon.draw_progress_bar(percentage/100.)
            elif self.last_download_count > 0:
                if self.tray_icon is not None:
                    # Update the tray icon status
                    self.tray_icon.set_status()
                    self.tray_icon.downloads_finished(self.download_tasks_seen)
                if gpodder.interface == gpodder.MAEMO:
                    hildon.hildon_banner_show_information(self.gPodder, None, 'gPodder: %s' % _('All downloads finished'))
                log('All downloads have finished.', sender=self)
                if self.config.cmd_all_downloads_complete:
                    util.run_external_command(self.config.cmd_all_downloads_complete)
            self.last_download_count = count

            self.gPodder.set_title(' - '.join(title))

            self.update_episode_list_icons(episode_urls)
            if self.episode_shownotes_window is not None and \
                    self.episode_shownotes_window.gPodderShownotes.get_property('visible'):
                self.episode_shownotes_window.download_status_changed(episode_urls)
                self.episode_shownotes_window.download_status_progress(episode_window_progress, episode_window_speed)
            self.play_or_download()
            if channel_urls:
                self.updateComboBox(only_these_urls=channel_urls)

            if not self.download_queue_manager.are_queued_or_active_tasks():
                self.download_list_update_enabled = False

            return self.download_list_update_enabled
        except Exception, e:
            log('Exception happened while updating download list.', sender=self, traceback=True)
            self.show_message('%s\n\n%s' % (_('Please report this problem and restart gPodder:'), str(e)), _('Unhandled exception'))
            # We return False here, so the update loop won't be called again,
            # that's why we require the restart of gPodder in the message.
            return False

    def entry_add_channel_focus(self, widget, event):
        widget.modify_text(gtk.STATE_NORMAL, self.default_entry_text_color)
        if widget.get_text() == self.ENTER_URL_TEXT:
            widget.set_text('')

    def entry_add_channel_unfocus(self, widget, event):
        if widget.get_text() == '':
            widget.set_text(self.ENTER_URL_TEXT)
            widget.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('#aaaaaa'))

    def on_config_changed(self, name, old_value, new_value):
        if name == 'show_toolbar' and gpodder.interface != gpodder.MAEMO:
            if new_value:
                self.toolbar.show()
            else:
                self.toolbar.hide()
        elif name == 'episode_list_descriptions' and gpodder.interface != gpodder.MAEMO:
            self.updateTreeView()
        elif name == 'show_url_entry_in_podcast_list':
            if new_value:
                self.hboxAddChannel.show()
            else:
                self.hboxAddChannel.hide()

    def read_apps(self):
        time.sleep(3) # give other parts of gpodder a chance to start up
        self.user_apps_reader.read()
        util.idle_add(self.user_apps_reader.get_applications_as_model, 'audio', False)
        util.idle_add(self.user_apps_reader.get_applications_as_model, 'video', False)

    def treeview_episodes_query_tooltip(self, treeview, x, y, keyboard_tooltip, tooltip):
        # With get_bin_window, we get the window that contains the rows without
        # the header. The Y coordinate of this window will be the height of the
        # treeview header. This is the amount we have to subtract from the
        # event's Y coordinate to get the coordinate to pass to get_path_at_pos
        (x_bin, y_bin) = treeview.get_bin_window().get_position()
        y -= x_bin
        y -= y_bin
        (path, column, rx, ry) = treeview.get_path_at_pos( x, y) or (None,)*4

        if not self.episode_list_can_tooltip or (column is not None and column != treeview.get_columns()[0]):
            self.last_tooltip_episode = None
            return False

        if path is not None:
            model = treeview.get_model()
            iter = model.get_iter(path)
            url = model.get_value(iter, EpisodeListModel.C_URL)
            description = model.get_value(iter, EpisodeListModel.C_DESCRIPTION_STRIPPED)
            if self.last_tooltip_episode is not None and self.last_tooltip_episode != url:
                self.last_tooltip_episode = None
                return False
            self.last_tooltip_episode = url

            if len(description) > 400:
                description = description[:398]+'[...]'

            tooltip.set_text(description)
            return True

        self.last_tooltip_episode = None
        return False

    def podcast_list_allow_tooltips(self):
        self.podcast_list_can_tooltip = True

    def episode_list_allow_tooltips(self):
        self.episode_list_can_tooltip = True

    def treeview_channels_query_tooltip(self, treeview, x, y, keyboard_tooltip, tooltip):
        (path, column, rx, ry) = treeview.get_path_at_pos( x, y) or (None,)*4

        if not self.podcast_list_can_tooltip or (column is not None and column != treeview.get_columns()[0]):
            self.last_tooltip_channel = None
            return False

        if path is not None:
            model = treeview.get_model()
            iter = model.get_iter(path)
            url = model.get_value(iter, PodcastListModel.C_URL)
            channel = model.get_value(iter, PodcastListModel.C_CHANNEL)

            if self.last_tooltip_channel is not None and self.last_tooltip_channel != channel:
                self.last_tooltip_channel = None
                return False
            self.last_tooltip_channel = channel
            channel.request_save_dir_size()
            diskspace_str = util.format_filesize(channel.save_dir_size, 0)
            error_str = model.get_value(iter, PodcastListModel.C_ERROR)
            if error_str:
                error_str = _('Feedparser error: %s') % saxutils.escape(error_str.strip())
                error_str = '<span foreground="#ff0000">%s</span>' % error_str
            table = gtk.Table(rows=3, columns=3)
            table.set_row_spacings(5)
            table.set_col_spacings(5)
            table.set_border_width(5)

            heading = gtk.Label()
            heading.set_alignment(0, 1)
            heading.set_markup('<b><big>%s</big></b>\n<small>%s</small>' % (saxutils.escape(channel.title), saxutils.escape(channel.url)))
            table.attach(heading, 0, 1, 0, 1)
            size_info = gtk.Label()
            size_info.set_alignment(1, 1)
            size_info.set_justify(gtk.JUSTIFY_RIGHT)
            size_info.set_markup('<b>%s</b>\n<small>%s</small>' % (diskspace_str, _('disk usage')))
            table.attach(size_info, 2, 3, 0, 1)

            table.attach(gtk.HSeparator(), 0, 3, 1, 2)

            if len(channel.description) < 500:
                description = channel.description
            else:
                pos = channel.description.find('\n\n')
                if pos == -1 or pos > 500:
                    description = channel.description[:498]+'[...]'
                else:
                    description = channel.description[:pos]

            description = gtk.Label(description)
            if error_str:
                description.set_markup(error_str)
            description.set_alignment(0, 0)
            description.set_line_wrap(True)
            table.attach(description, 0, 3, 2, 3)

            table.show_all()
            tooltip.set_custom(table)

            return True

        self.last_tooltip_channel = None
        return False

    def update_m3u_playlist_clicked(self, widget):
        self.active_channel.update_m3u_playlist()
        self.show_message(_('Updated M3U playlist in download folder.'), _('Updated playlist'))

    def treeview_downloads_button_pressed(self, treeview, event):
        if event.button == 1:
            # Catch left mouse button presses, and if we there is no
            # path at the given position, deselect all items
            (x, y) = (int(event.x), int(event.y))
            (path, column, rx, ry) = treeview.get_path_at_pos(x, y) or (None,)*4
            if path is None:
                treeview.get_selection().unselect_all()

        # Use right-click for the Desktop version and left-click for Maemo
        if (event.button == 1 and gpodder.interface == gpodder.MAEMO) or \
           (event.button == 3 and gpodder.interface == gpodder.GUI):
            (x, y) = (int(event.x), int(event.y))
            (path, column, rx, ry) = treeview.get_path_at_pos(x, y) or (None,)*4

            paths = []
            # Did the user right-click into a selection?
            selection = treeview.get_selection()
            if selection.count_selected_rows() and path:
                (model, paths) = selection.get_selected_rows()
                if path not in paths:
                    # We have right-clicked, but not into the 
                    # selection, assume we don't want to operate
                    # on the selection
                    paths = []

            # No selection or right click not in selection:
            # Select the single item where we clicked
            if not paths and path:
                treeview.grab_focus()
                treeview.set_cursor( path, column, 0)
                (model, paths) = (treeview.get_model(), [path])

            # We did not find a selection, and the user didn't
            # click on an item to select -- don't show the menu
            if not paths:
                return True
            
            selected_tasks = [(gtk.TreeRowReference(model, path), model.get_value(model.get_iter(path), 0)) for path in paths]

            def make_menu_item(label, stock_id, tasks, status):
                # This creates a menu item for selection-wide actions
                def for_each_task_set_status(tasks, status):
                    changed_episode_urls = []
                    for row_reference, task in tasks:
                        if status is not None:
                            if status == download.DownloadTask.QUEUED:
                                # Only queue task when its paused/failed/cancelled
                                if task.status in (task.PAUSED, task.FAILED, task.CANCELLED):
                                    self.download_queue_manager.add_task(task)
                                    self.enable_download_list_update()
                            elif status == download.DownloadTask.CANCELLED:
                                # Cancelling a download only allows when paused/downloading/queued
                                if task.status in (task.QUEUED, task.DOWNLOADING, task.PAUSED):
                                    task.status = status
                            elif status == download.DownloadTask.PAUSED:
                                # Pausing a download only when queued/downloading
                                if task.status in (task.DOWNLOADING, task.QUEUED):
                                    task.status = status
                            else:
                                # We (hopefully) can simply set the task status here
                                task.status = status
                        else:
                            # Remove the selected task - cancel downloading/queued tasks
                            if task.status in (task.QUEUED, task.DOWNLOADING):
                                task.status = task.CANCELLED
                            model.remove(model.get_iter(row_reference.get_path()))
                            # Remember the URL, so we can tell the UI to update
                            try:
                                # We don't "see" this task anymore - remove it;
                                # this is needed, so update_episode_list_icons()
                                # below gets the correct list of "seen" tasks
                                self.download_tasks_seen.remove(task)
                            except KeyError, key_error:
                                log('Cannot remove task from "seen" list: %s', task, sender=self)
                            changed_episode_urls.append(task.url)
                            # Tell the task that it has been removed (so it can clean up)
                            task.removed_from_list()
                    # Tell the podcasts tab to update icons for our removed podcasts
                    self.update_episode_list_icons(changed_episode_urls)
                    # Update the tab title and downloads list
                    self.update_downloads_list()
                    return True
                item = gtk.ImageMenuItem(label)
                item.set_image(gtk.image_new_from_stock(stock_id, gtk.ICON_SIZE_MENU))
                item.connect('activate', lambda item: for_each_task_set_status(tasks, status))

                # Determine if we should disable this menu item
                for row_reference, task in tasks:
                    if status == download.DownloadTask.QUEUED:
                        if task.status not in (download.DownloadTask.PAUSED, \
                                download.DownloadTask.FAILED, \
                                download.DownloadTask.CANCELLED):
                            item.set_sensitive(False)
                            break
                    elif status == download.DownloadTask.CANCELLED:
                        if task.status not in (download.DownloadTask.PAUSED, \
                                download.DownloadTask.QUEUED, \
                                download.DownloadTask.DOWNLOADING):
                            item.set_sensitive(False)
                            break
                    elif status == download.DownloadTask.PAUSED:
                        if task.status not in (download.DownloadTask.QUEUED, \
                                download.DownloadTask.DOWNLOADING):
                            item.set_sensitive(False)
                            break
                    elif status is None:
                        if task.status not in (download.DownloadTask.CANCELLED, \
                                download.DownloadTask.FAILED, \
                                download.DownloadTask.DONE):
                            item.set_sensitive(False)
                            break

                return self.set_finger_friendly(item)

            menu = gtk.Menu()

            item = gtk.ImageMenuItem(_('Episode details'))
            item.set_image(gtk.image_new_from_stock(gtk.STOCK_INFO, gtk.ICON_SIZE_MENU))
            if len(selected_tasks) == 1:
                row_reference, task = selected_tasks[0]
                episode = task.episode
                item.connect('activate', lambda item: self.show_episode_shownotes(episode))
            else:
                item.set_sensitive(False)
            menu.append(item)
            menu.append(gtk.SeparatorMenuItem())
            menu.append(make_menu_item(_('Download'), gtk.STOCK_GO_DOWN, selected_tasks, download.DownloadTask.QUEUED))
            menu.append(make_menu_item(_('Cancel'), gtk.STOCK_CANCEL, selected_tasks, download.DownloadTask.CANCELLED))
            menu.append(make_menu_item(_('Pause'), gtk.STOCK_MEDIA_PAUSE, selected_tasks, download.DownloadTask.PAUSED))
            menu.append(gtk.SeparatorMenuItem())
            menu.append(make_menu_item(_('Remove from list'), gtk.STOCK_REMOVE, selected_tasks, None))

            if gpodder.interface == gpodder.MAEMO:
                # Because we open the popup on left-click for Maemo,
                # we also include a non-action to close the menu
                menu.append(gtk.SeparatorMenuItem())
                item = gtk.ImageMenuItem(_('Close this menu'))
                item.set_image(gtk.image_new_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU))
                menu.append(self.set_finger_friendly(item))

            menu.show_all()
            menu.popup(None, None, None, event.button, event.time)
            return True

    def treeview_channels_button_pressed( self, treeview, event):
        global WEB_BROWSER_ICON

        if gpodder.interface == gpodder.MAEMO:
            self.treeview_channels_buttonpress = (event.x, event.y)
            return True

        if event.button == 3:
            ( x, y ) = ( int(event.x), int(event.y) )
            ( path, column, rx, ry ) = treeview.get_path_at_pos( x, y) or (None,)*4

            paths = []

            # Did the user right-click into a selection?
            selection = treeview.get_selection()
            if selection.count_selected_rows() and path:
                ( model, paths ) = selection.get_selected_rows()
                if path not in paths:
                    # We have right-clicked, but not into the 
                    # selection, assume we don't want to operate
                    # on the selection
                    paths = []

            # No selection or right click not in selection:
            # Select the single item where we clicked
            if not len( paths) and path:
                treeview.grab_focus()
                treeview.set_cursor( path, column, 0)

                ( model, paths ) = ( treeview.get_model(), [ path ] )

            # We did not find a selection, and the user didn't
            # click on an item to select -- don't show the menu
            if not len( paths):
                return True

            menu = gtk.Menu()

            item = gtk.ImageMenuItem( _('Open download folder'))
            item.set_image( gtk.image_new_from_icon_name( 'folder-open', gtk.ICON_SIZE_MENU))
            item.connect('activate', lambda x: util.gui_open(self.active_channel.save_dir))
            menu.append( item)

            item = gtk.ImageMenuItem( _('Update Feed'))
            item.set_image( gtk.image_new_from_icon_name( 'gtk-refresh', gtk.ICON_SIZE_MENU))
            item.connect('activate', self.on_itemUpdateChannel_activate )
            item.set_sensitive( not self.updating_feed_cache )
            menu.append( item)

            item = gtk.ImageMenuItem(_('Update M3U playlist'))
            item.set_image(gtk.image_new_from_stock(gtk.STOCK_REFRESH, gtk.ICON_SIZE_MENU))
            item.connect('activate', self.update_m3u_playlist_clicked)
            menu.append(item)

            if self.active_channel.link:
                item = gtk.ImageMenuItem(_('Visit website'))
                item.set_image(gtk.image_new_from_icon_name(WEB_BROWSER_ICON, gtk.ICON_SIZE_MENU))
                item.connect('activate', lambda w: util.open_website(self.active_channel.link))
                menu.append(item)

            if self.active_channel.channel_is_locked:
                item = gtk.ImageMenuItem(_('Allow deletion of all episodes'))
                item.set_image(gtk.image_new_from_stock(gtk.STOCK_DIALOG_AUTHENTICATION, gtk.ICON_SIZE_MENU))
                item.connect('activate', self.on_channel_toggle_lock_activate)
                menu.append(self.set_finger_friendly(item))
            else:
                item = gtk.ImageMenuItem(_('Prohibit deletion of all episodes'))
                item.set_image(gtk.image_new_from_stock(gtk.STOCK_DIALOG_AUTHENTICATION, gtk.ICON_SIZE_MENU))
                item.connect('activate', self.on_channel_toggle_lock_activate)
                menu.append(self.set_finger_friendly(item))


            menu.append( gtk.SeparatorMenuItem())

            item = gtk.ImageMenuItem(gtk.STOCK_EDIT)
            item.connect( 'activate', self.on_itemEditChannel_activate)
            menu.append( item)

            item = gtk.ImageMenuItem(gtk.STOCK_DELETE)
            item.connect( 'activate', self.on_itemRemoveChannel_activate)
            menu.append( item)

            menu.show_all()
            # Disable tooltips while we are showing the menu, so 
            # the tooltip will not appear over the menu
            self.podcast_list_can_tooltip = False
            menu.connect('deactivate', lambda menushell: self.podcast_list_allow_tooltips())
            menu.popup( None, None, None, event.button, event.time)

            return True

    def on_itemClose_activate(self, widget):
        if self.tray_icon is not None:
            if gpodder.interface == gpodder.MAEMO:
                self.gPodder.set_property('visible', False)
            else:
                self.iconify_main_window()
        else:
            self.on_gPodder_delete_event(widget)

    def cover_file_removed(self, channel_url):
        """
        The Cover Downloader calls this when a previously-
        available cover has been removed from the disk. We
        have to update our model to reflect this change.
        """
        self.podcast_list_model.delete_cover_by_url(channel_url)
    
    def cover_download_finished(self, channel_url, pixbuf):
        """
        The Cover Downloader calls this when it has finished
        downloading (or registering, if already downloaded)
        a new channel cover, which is ready for displaying.
        """
        self.podcast_list_model.add_cover_by_url(channel_url, pixbuf)

    def save_episode_as_file(self, episode):
        if episode.was_downloaded(and_exists=True):
            folder = self.folder_for_saving_episodes
            copy_from = episode.local_filename(create=False)
            assert copy_from is not None
            copy_to = episode.sync_filename(self.config.custom_sync_name_enabled, self.config.custom_sync_name)
            (result, folder) = self.show_copy_dialog(src_filename=copy_from, dst_filename=copy_to, dst_directory=folder)
            self.folder_for_saving_episodes = folder

    def copy_episodes_bluetooth(self, episodes):
        episodes_to_copy = [e for e in episodes if e.was_downloaded(and_exists=True)]

        def convert_and_send_thread(episodes, notify):
            for episode in episodes:
                filename = episode.local_filename(create=False)
                assert filename is not None
                destfile = os.path.join(tempfile.gettempdir(), \
                        util.sanitize_filename(episode.sync_filename(self.config.custom_sync_name_enabled, self.config.custom_sync_name)))
                (base, ext) = os.path.splitext(filename)
                if not destfile.endswith(ext):
                    destfile += ext

                try:
                    shutil.copyfile(filename, destfile)
                    util.bluetooth_send_file(destfile)
                except:
                    log('Cannot copy "%s" to "%s".', filename, destfile, sender=self)
                    notify(_('Error converting file.'), _('Bluetooth file transfer'))

                util.delete_file(destfile)

        Thread(target=convert_and_send_thread, args=[episodes_to_copy, self.notification]).start()

    def treeview_button_savepos(self, treeview, event):
        if gpodder.interface == gpodder.MAEMO and event.button == 1:
            self.treeview_available_buttonpress = (event.x, event.y)
            return True

    def treeview_channels_button_released(self, treeview, event):
        if gpodder.interface == gpodder.MAEMO and event.button == 1:
            selection = self.treeChannels.get_selection()
            pathatpos = self.treeChannels.get_path_at_pos(int(event.x), int(event.y))
            if self.currently_updating:
                log('do not handle press while updating', sender=self)
                return True
            if pathatpos is None:
                return False
            else:
                ydistance = int(abs(event.y-self.treeview_channels_buttonpress[1]))
                xdistance = int(event.x-self.treeview_channels_buttonpress[0])
                if ydistance < 30:
                    (path, column, x, y) = pathatpos
                    selection.select_path(path)
                    self.treeChannels.set_cursor(path)
                    self.treeChannels.grab_focus()
                    # Emulate the cursor changed signal to force an update
                    self.on_treeChannels_cursor_changed(self.treeChannels)
                    return True

    def get_device_name(self):
        if self.config.device_type == 'ipod':
            return _('iPod')
        elif self.config.device_type in ('filesystem', 'mtp'):
            return _('MP3 player')
        else:
            return '(unknown device)'

    def treeview_button_pressed( self, treeview, event):
        global WEB_BROWSER_ICON

        if gpodder.interface == gpodder.MAEMO:
            ydistance = int(abs(event.y-self.treeview_available_buttonpress[1]))
            xdistance = int(event.x-self.treeview_available_buttonpress[0])

            selection = self.treeAvailable.get_selection()
            pathatpos = self.treeAvailable.get_path_at_pos(int(event.x), int(event.y))
            if pathatpos is None:
                # No item at the current cursor position
                return False
            elif ydistance < 30:
                # Item under the cursor, and no scrolling done
                (path, column, x, y) = pathatpos
                selection.select_path(path)
                self.treeAvailable.set_cursor(path)
                self.treeAvailable.grab_focus()
                if self.config.maemo_enable_gestures and xdistance > 70:
                    self.on_playback_selected_episodes(None)
                    return True
                elif self.config.maemo_enable_gestures and xdistance < -70:
                    self.on_shownotes_selected_episodes(None)
                    return True
            else:
                # Scrolling has been done
                return True

        # Use right-click for the Desktop version and left-click for Maemo
        if (event.button == 1 and gpodder.interface == gpodder.MAEMO) or \
           (event.button == 3 and gpodder.interface == gpodder.GUI):
            ( x, y ) = ( int(event.x), int(event.y) )
            ( path, column, rx, ry ) = treeview.get_path_at_pos( x, y) or (None,)*4

            paths = []

            # Did the user right-click into a selection?
            selection = self.treeAvailable.get_selection()
            if selection.count_selected_rows() and path:
                ( model, paths ) = selection.get_selected_rows()
                if path not in paths:
                    # We have right-clicked, but not into the 
                    # selection, assume we don't want to operate
                    # on the selection
                    paths = []

            # No selection or right click not in selection:
            # Select the single item where we clicked
            if not len( paths) and path:
                treeview.grab_focus()
                treeview.set_cursor( path, column, 0)

                ( model, paths ) = ( treeview.get_model(), [ path ] )

            # We did not find a selection, and the user didn't
            # click on an item to select -- don't show the menu
            if not len( paths):
                return True

            episodes = self.get_selected_episodes()
            any_locked = any(e.is_locked for e in episodes)
            any_played = any(e.is_played for e in episodes)
            one_is_new = any(e.state == gpodder.STATE_NORMAL and not e.is_played for e in episodes)

            menu = gtk.Menu()

            (can_play, can_download, can_transfer, can_cancel, can_delete, open_instead_of_play) = self.play_or_download()

            if open_instead_of_play:
                item = gtk.ImageMenuItem(gtk.STOCK_OPEN)
            else:
                item = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PLAY)

            item.set_sensitive(can_play)
            item.connect('activate', self.on_playback_selected_episodes)
            menu.append(self.set_finger_friendly(item))

            if not can_cancel:
                item = gtk.ImageMenuItem(_('Download'))
                item.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_DOWN, gtk.ICON_SIZE_MENU))
                item.set_sensitive(can_download)
                item.connect('activate', self.on_download_selected_episodes)
                menu.append(self.set_finger_friendly(item))
            else:
                item = gtk.ImageMenuItem(gtk.STOCK_CANCEL)
                item.connect('activate', lambda w: self.on_treeDownloads_row_activated(self.toolCancel))
                menu.append(self.set_finger_friendly(item))

            item = gtk.ImageMenuItem(gtk.STOCK_DELETE)
            item.set_sensitive(can_delete)
            item.connect('activate', self.on_btnDownloadedDelete_clicked)
            menu.append(self.set_finger_friendly(item))

            if one_is_new:
                item = gtk.ImageMenuItem(_('Do not download'))
                item.set_image(gtk.image_new_from_stock(gtk.STOCK_DELETE, gtk.ICON_SIZE_MENU))
                item.connect('activate', lambda w: self.mark_selected_episodes_old())
                menu.append(self.set_finger_friendly(item))
            elif can_download:
                item = gtk.ImageMenuItem(_('Mark as new'))
                item.set_image(gtk.image_new_from_stock(gtk.STOCK_ABOUT, gtk.ICON_SIZE_MENU))
                item.connect('activate', lambda w: self.mark_selected_episodes_new())
                menu.append(self.set_finger_friendly(item))

            # Ok, this probably makes sense to only display for downloaded files
            if can_play and not can_download:
                menu.append( gtk.SeparatorMenuItem())
                item = gtk.ImageMenuItem(_('Save to disk'))
                item.set_image(gtk.image_new_from_stock(gtk.STOCK_SAVE_AS, gtk.ICON_SIZE_MENU))
                item.connect('activate', lambda w: [self.save_episode_as_file(e) for e in episodes])
                menu.append(self.set_finger_friendly(item))
                if self.bluetooth_available:
                    item = gtk.ImageMenuItem(_('Send via bluetooth'))
                    item.set_image(gtk.image_new_from_icon_name('bluetooth', gtk.ICON_SIZE_MENU))
                    item.connect('activate', lambda w: self.copy_episodes_bluetooth(episodes))
                    menu.append(self.set_finger_friendly(item))
                if can_transfer:
                    item = gtk.ImageMenuItem(_('Transfer to %s') % self.get_device_name())
                    item.set_image(gtk.image_new_from_icon_name('multimedia-player', gtk.ICON_SIZE_MENU))
                    item.connect('activate', lambda w: self.on_sync_to_ipod_activate(w, episodes))
                    menu.append(self.set_finger_friendly(item))

            if can_play:
                menu.append( gtk.SeparatorMenuItem())
                if any_played:
                    item = gtk.ImageMenuItem(_('Mark as unplayed'))
                    item.set_image( gtk.image_new_from_stock( gtk.STOCK_CANCEL, gtk.ICON_SIZE_MENU))
                    item.connect( 'activate', lambda w: self.on_item_toggle_played_activate( w, False, False))
                    menu.append(self.set_finger_friendly(item))
                else:
                    item = gtk.ImageMenuItem(_('Mark as played'))
                    item.set_image( gtk.image_new_from_stock( gtk.STOCK_APPLY, gtk.ICON_SIZE_MENU))
                    item.connect( 'activate', lambda w: self.on_item_toggle_played_activate( w, False, True))
                    menu.append(self.set_finger_friendly(item))

                if any_locked:
                    item = gtk.ImageMenuItem(_('Allow deletion'))
                    item.set_image(gtk.image_new_from_stock(gtk.STOCK_DIALOG_AUTHENTICATION, gtk.ICON_SIZE_MENU))
                    item.connect('activate', lambda w: self.on_item_toggle_lock_activate( w, False, False))
                    menu.append(self.set_finger_friendly(item))
                else:
                    item = gtk.ImageMenuItem(_('Prohibit deletion'))
                    item.set_image(gtk.image_new_from_stock(gtk.STOCK_DIALOG_AUTHENTICATION, gtk.ICON_SIZE_MENU))
                    item.connect('activate', lambda w: self.on_item_toggle_lock_activate( w, False, True))
                    menu.append(self.set_finger_friendly(item))

            menu.append(gtk.SeparatorMenuItem())
            # Single item, add episode information menu item
            item = gtk.ImageMenuItem(_('Episode details'))
            item.set_image(gtk.image_new_from_stock( gtk.STOCK_INFO, gtk.ICON_SIZE_MENU))
            item.connect('activate', lambda w: self.show_episode_shownotes(episodes[0]))
            menu.append(self.set_finger_friendly(item))

            # If we have it, also add episode website link
            if episodes[0].link and episodes[0].link != episodes[0].url:
                item = gtk.ImageMenuItem(_('Visit website'))
                item.set_image(gtk.image_new_from_icon_name(WEB_BROWSER_ICON, gtk.ICON_SIZE_MENU))
                item.connect('activate', lambda w: util.open_website(episodes[0].link))
                menu.append(self.set_finger_friendly(item))
            
            if gpodder.interface == gpodder.MAEMO:
                # Because we open the popup on left-click for Maemo,
                # we also include a non-action to close the menu
                menu.append(gtk.SeparatorMenuItem())
                item = gtk.ImageMenuItem(_('Close this menu'))
                item.set_image(gtk.image_new_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU))
                menu.append(self.set_finger_friendly(item))

            menu.show_all()
            # Disable tooltips while we are showing the menu, so 
            # the tooltip will not appear over the menu
            self.episode_list_can_tooltip = False
            menu.connect('deactivate', lambda menushell: self.episode_list_allow_tooltips())
            menu.popup( None, None, None, event.button, event.time)

            return True

    def set_title(self, new_title):
        self.default_title = new_title
        self.gPodder.set_title(new_title)

    def update_selected_episode_list_icons(self):
        """
        Updates the status icons in the episode list
        """
        selection = self.treeAvailable.get_selection()
        (model, paths) = selection.get_selected_rows()
        for path in paths:
            iter = model.get_iter(path)
            self.episode_list_model.update_by_iter(iter, \
                    self.episode_is_downloading, \
                    self.config.episode_list_descriptions and gpodder.interface != gpodder.MAEMO)

    def update_episode_list_icons(self, urls):
        """
        Updates the status icons in the episode list
        Only update the episodes that have an URL in
        the "urls" iterable object (e.g. a list of URLs)
        """
        if self.active_channel is None or not urls:
            return

        self.episode_list_model.update_by_urls(urls, \
                self.episode_is_downloading, \
                self.config.episode_list_descriptions and gpodder.interface != gpodder.MAEMO)
 
    def clean_up_downloads(self, delete_partial=False):
        # Clean up temporary files left behind by old gPodder versions
        temporary_files = glob.glob('%s/*/.tmp-*' % self.config.download_dir)

        if delete_partial:
            temporary_files += glob.glob('%s/*/*.partial' % self.config.download_dir)

        for tempfile in temporary_files:
            util.delete_file(tempfile)

        # Clean up empty download folders and abandoned download folders
        download_dirs = glob.glob(os.path.join(self.config.download_dir, '*'))
        for ddir in download_dirs:
            if os.path.isdir(ddir) and False: # FIXME not db.channel_foldername_exists(os.path.basename(ddir)):
                globr = glob.glob(os.path.join(ddir, '*'))
                if len(globr) == 0 or (len(globr) == 1 and globr[0].endswith('/cover')):
                    log('Stale download directory found: %s', os.path.basename(ddir), sender=self)
                    shutil.rmtree(ddir, ignore_errors=True)

    def streaming_possible(self):
        return self.config.player and self.config.player != 'default'

    def playback_episodes_for_real(self, episodes):
        groups = collections.defaultdict(list)
        for episode in episodes:
            # Mark episode as played in the database
            episode.mark(is_played=True)

            file_type = episode.file_type()
            if file_type == 'video' and self.config.videoplayer and \
                    self.config.videoplayer != 'default':
                player = self.config.videoplayer
            elif file_type == 'audio' and self.config.player and \
                    self.config.player != 'default':
                player = self.config.player
            else:
                player = 'default'

            filename = episode.local_filename(create=False)
            if filename is None or not os.path.exists(filename):
                filename = episode.url
            groups[player].append(filename)

        # Open episodes with system default player
        if 'default' in groups:
            for filename in groups['default']:
                log('Opening with system default: %s', filename, sender=self)
                util.gui_open(filename)
            del groups['default']

        # For each type now, go and create play commands
        for group in groups:
            for command in util.format_desktop_command(group, groups[group]):
                log('Executing: %s', repr(command), sender=self)
                subprocess.Popen(command)

    def playback_episodes(self, episodes):
        if gpodder.interface == gpodder.MAEMO:
            if len(episodes) == 1:
                text = _('Opening %s') % saxutils.escape(episodes[0].title)
            else:
                text = _('Opening %d episodes') % len(episodes)
            banner = hildon.hildon_banner_show_animation(self.gPodder, None, text)
            def destroy_banner_later(banner):
                banner.destroy()
                return False
            gobject.timeout_add(5000, destroy_banner_later, banner)

        episodes = [e for e in episodes if \
                e.was_downloaded(and_exists=True) or self.streaming_possible()]

        try:
            self.playback_episodes_for_real(episodes)
        except Exception, e:
            log('Error in playback!', sender=self, traceback=True)
            self.show_message( _('Please check your media player settings in the preferences dialog.'), _('Error opening player'))

        self.update_selected_episode_list_icons()
        self.updateComboBox(only_selected_channel=True)

    def treeAvailable_search_equal( self, model, column, key, iter, data = None):
        if model is None:
            return True

        key = key.lower()

        for column in (EpisodeListModel.C_TITLE, EpisodeListModel.C_DESCRIPTION_STRIPPED):
            value = model.get_value( iter, column).lower()
            if value.find( key) != -1:
                return False

        return True
    
    def change_menu_item(self, menuitem, icon=None, label=None):
        if icon is not None:
            menuitem.set_property('stock-id', icon)
        if label is not None:
            menuitem.label = label

    def play_or_download(self):
        if self.wNotebook.get_current_page() > 0:
            return

        ( can_play, can_download, can_transfer, can_cancel, can_delete ) = (False,)*5
        ( is_played, is_locked ) = (False,)*2

        open_instead_of_play = False

        selection = self.treeAvailable.get_selection()
        if selection.count_selected_rows() > 0:
            (model, paths) = selection.get_selected_rows()
         
            for path in paths:
                episode = model.get_value(model.get_iter(path), EpisodeListModel.C_EPISODE)

                if episode.file_type() not in ('audio', 'video'):
                    open_instead_of_play = True

                if episode.was_downloaded():
                    can_play = episode.was_downloaded(and_exists=True)
                    can_delete = True
                    is_played = episode.is_played
                    is_locked = episode.is_locked
                    if not can_play:
                        can_download = True
                else:
                    if self.episode_is_downloading(episode):
                        can_cancel = True
                    else:
                        can_download = True

        can_download = can_download and not can_cancel
        can_play = self.streaming_possible() or (can_play and not can_cancel and not can_download)
        can_transfer = can_play and self.config.device_type != 'none' and not can_cancel and not can_download

        if open_instead_of_play:
            if gpodder.interface != gpodder.MAEMO:
                self.toolPlay.set_stock_id(gtk.STOCK_OPEN)
            can_transfer = False
        else:
            if gpodder.interface != gpodder.MAEMO:
                self.toolPlay.set_stock_id(gtk.STOCK_MEDIA_PLAY)

        self.toolPlay.set_sensitive( can_play)
        self.toolDownload.set_sensitive( can_download)
        self.toolTransfer.set_sensitive( can_transfer)
        self.toolCancel.set_sensitive( can_cancel)

        self.item_cancel_download.set_sensitive(can_cancel)
        self.itemDownloadSelected.set_sensitive(can_download)
        self.itemOpenSelected.set_sensitive(can_play)
        self.itemPlaySelected.set_sensitive(can_play)
        self.itemDeleteSelected.set_sensitive(can_play and not can_download)
        self.item_toggle_played.set_sensitive(can_play)
        self.item_toggle_lock.set_sensitive(can_play)

        self.itemOpenSelected.set_visible(open_instead_of_play)
        self.itemPlaySelected.set_visible(not open_instead_of_play)

        if can_play:
            if is_played:
                self.change_menu_item(self.item_toggle_played, gtk.STOCK_CANCEL, _('Mark as unplayed'))
            else:
                self.change_menu_item(self.item_toggle_played, gtk.STOCK_APPLY, _('Mark as played'))
            if is_locked:
                self.change_menu_item(self.item_toggle_lock, gtk.STOCK_DIALOG_AUTHENTICATION, _('Allow deletion'))
            else:
                self.change_menu_item(self.item_toggle_lock, gtk.STOCK_DIALOG_AUTHENTICATION, _('Prohibit deletion'))

        return (can_play, can_download, can_transfer, can_cancel, can_delete, open_instead_of_play)

    def on_cbMaxDownloads_toggled(self, widget, *args):
        self.spinMaxDownloads.set_sensitive(self.cbMaxDownloads.get_active())

    def on_cbLimitDownloads_toggled(self, widget, *args):
        self.spinLimitDownloads.set_sensitive(self.cbLimitDownloads.get_active())

    def episode_new_status_changed(self, urls):
        self.updateComboBox()
        self.update_episode_list_icons(urls)

    def updateComboBox(self, selected_url=None, only_selected_channel=False, only_these_urls=None):
        selection = self.treeChannels.get_selection()
        (model, iter) = selection.get_selected()

        if only_selected_channel:
            # very cheap! only update selected channel
            if iter and self.active_channel is not None:
                model.update_by_iter(iter)
        elif not self.channel_list_changed:
            # we can keep the model, but have to update some
            if only_these_urls is None:
                # still cheaper than reloading the whole list
                iter = model.get_iter_first()
                while iter is not None:
                    model.update_by_iter(iter)
                    iter = model.iter_next(iter)
            else:
                # ok, we got a bunch of urls to update
                model.update_by_urls(only_these_urls)
        else:
            if model and iter and selected_url is None:
                # Get the URL of the currently-selected podcast
                selected_url = model.get_value(iter, 0)

            # Update the podcast list model with new channels
            self.podcast_list_model.set_channels(self.channels)

            try:
                selected_path = (0,)
                # Find the previously-selected URL in the new
                # model if we have an URL (else select first)
                if selected_url is not None:
                    pos = model.get_iter_first()
                    while pos is not None:
                        url = model.get_value(pos, 0)
                        if url == selected_url:
                            selected_path = model.get_path(pos)
                            break
                        pos = model.iter_next(pos)

                self.treeChannels.get_selection().select_path(selected_path)
            except:
                log( 'Cannot set selection on treeChannels', sender = self)
            self.on_treeChannels_cursor_changed( self.treeChannels)
        self.channel_list_changed = False

    def episode_is_downloading(self, episode):
        """Returns True if the given episode is being downloaded at the moment"""
        if episode is None:
            return False

        return episode.url in (task.url for task in self.download_tasks_seen if task.status in (task.DOWNLOADING, task.QUEUED, task.PAUSED))

    def on_episode_list_model_updated(self, banner=None):
        if banner is not None:
            banner.destroy()
        self.treeAvailable.columns_autosize()
        self.play_or_download()
        self.currently_updating = False
    
    def updateTreeView(self):
        if self.channels and self.active_channel is not None:
            if gpodder.interface == gpodder.MAEMO:
                banner = hildon.hildon_banner_show_animation(self.gPodder, None, _('Loading episodes for %s') % saxutils.escape(self.active_channel.title))
            else:
                banner = None

            self.currently_updating = True
            self.episode_list_model.update_from_channel(self.active_channel, \
                    self.episode_is_downloading, \
                    self.config.episode_list_descriptions and gpodder.interface != gpodder.MAEMO, \
                    lambda: self.on_episode_list_model_updated(banner))
        else:
            self.episode_list_model.clear()
    
    def drag_data_received(self, widget, context, x, y, sel, ttype, time):
        (path, column, rx, ry) = self.treeChannels.get_path_at_pos( x, y) or (None,)*4

        dnd_channel = None
        if path is not None:
            model = self.treeChannels.get_model()
            iter = model.get_iter(path)
            url = model.get_value(iter, 0)
            for channel in self.channels:
                if channel.url == url:
                    dnd_channel = channel
                    break

        result = sel.data
        rl = result.strip().lower()
        if (rl.endswith('.jpg') or rl.endswith('.png') or rl.endswith('.gif') or rl.endswith('.svg')) and dnd_channel is not None:
            self.cover_downloader.replace_cover(dnd_channel, result)
        else:
            self.add_new_channel(result)

    def add_new_channel(self, result=None, ask_download_new=True, quiet=False, block=False, authentication_tokens=None):
        result = util.normalize_feed_url(result)
        (scheme, rest) = result.split('://', 1)

        if not result:
            cute_scheme = saxutils.escape(scheme)+'://'
            title = _('%s URLs are not supported') % cute_scheme
            message = _('gPodder does not understand the URL you supplied.')
            self.show_message( message, title)
            return

        for old_channel in self.channels:
            if old_channel.url == result:
                log( 'Channel already exists: %s', result)
                # Select the existing channel in combo box
                for i in range( len( self.channels)):
                    if self.channels[i] == old_channel:
                        self.treeChannels.get_selection().select_path( (i,))
                        self.on_treeChannels_cursor_changed(self.treeChannels)
                        break
                self.show_message( _('You have already subscribed to this podcast: %s') % ( 
                    saxutils.escape( old_channel.title), ), _('Already added'))
                return

        waitdlg = gtk.MessageDialog(self.gPodder, 0, gtk.MESSAGE_INFO, gtk.BUTTONS_NONE)
        waitdlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        waitdlg.set_title(_('Downloading episode list'))
        waitdlg.set_markup('<b><big>%s</big></b>' % waitdlg.get_title())
        waitdlg.format_secondary_text(_('Downloading episode information for %s') % result)
        waitpb = gtk.ProgressBar()
        if block:
            waitdlg.vbox.add(waitpb)
        waitdlg.show_all()
        waitdlg.set_response_sensitive(gtk.RESPONSE_CANCEL, False)

        self.entryAddChannel.set_text(_('Downloading feed...'))
        self.entryAddChannel.set_sensitive(False)
        self.btnAddChannel.set_sensitive(False)
        args = (result, self.add_new_channel_finish, authentication_tokens, ask_download_new, quiet, waitdlg)
        thread = Thread( target=self.add_new_channel_proc, args=args )
        thread.start()

        while block and thread.isAlive():
            while gtk.events_pending():
                gtk.main_iteration( False)
            waitpb.pulse()
            time.sleep(0.1)


    def add_new_channel_proc( self, url, callback, authentication_tokens, *callback_args):
        log( 'Adding new channel: %s', url)
        channel = error = None
        try:
            channel = PodcastChannel.load(self.db, url=url, create=True,
                    authentication_tokens=authentication_tokens,
                    max_episodes=self.config.max_episodes_per_feed,
                    download_dir=self.config.download_dir)
        except feedcore.AuthenticationRequired, e:
            error = e
        except feedcore.WifiLogin, e:
            error = e
        except Exception, e:
            log('Error adding channel: %s', e, traceback=True, sender=self)

        util.idle_add( callback, channel, url, error, *callback_args )

    def save_channels_opml(self):
        exporter = opml.Exporter(gpodder.subscription_file)
        return exporter.write(self.channels)

    def add_new_channel_finish( self, channel, url, error, ask_download_new, quiet, waitdlg):
        if channel is not None:
            self.channels.append( channel)
            self.channel_list_changed = True
            self.save_channels_opml()
            if not quiet:
                # download changed channels and select the new episode in the UI afterwards
                self.update_feed_cache(force_update=False, select_url_afterwards=channel.url)

            try:
                (username, password) = util.username_password_from_url(url)
            except ValueError, ve:
                self.show_message(_('The following error occured while trying to get authentication data from the URL:') + '\n\n' + ve.message, _('Error getting authentication data'))
                (username, password) = (None, None)
                log('Error getting authentication data from URL: %s', url, traceback=True)

            if username and self.show_confirmation( _('You have supplied <b>%s</b> as username and a password for this feed. Would you like to use the same authentication data for downloading episodes?') % ( saxutils.escape( username), ), _('Password authentication')):
                channel.username = username
                channel.password = password
                log('Saving authentication data for episode downloads..', sender = self)
                channel.save()
                # We need to update the channel list otherwise the authentication
                # data won't show up in the channel editor.
                # TODO: Only updated the newly added feed to save some cpu cycles
                self.channels = PodcastChannel.load_from_db(self.db, self.config.download_dir)
                self.channel_list_changed = True

            if ask_download_new:
                new_episodes = channel.get_new_episodes(downloading=self.episode_is_downloading)
                if len(new_episodes):
                    self.new_episodes_show(new_episodes)

        elif isinstance(error, feedcore.AuthenticationRequired):
            response, auth_tokens = self.UsernamePasswordDialog(
                _('Feed requires authentication'), _('Please enter your username and password.'))

            if response:
                self.add_new_channel( url, authentication_tokens=auth_tokens )

        elif isinstance(error, feedcore.WifiLogin):
            if self.show_confirmation(_('The URL you are trying to add redirects to the website %s. Do you want to visit the website to login now?') % saxutils.escape(error.data), _('Website redirection detected')):
                util.open_website(error.data)
                if self.show_confirmation(_('Please login to the website now. Should I retry subscribing to the podcast at %s?') % saxutils.escape(url), _('Retry adding channel')):
                    self.add_new_channel(url)

        else:
            # Ok, the URL is not a channel, or there is some other
            # error - let's see if it's a web page or OPML file...
            handled = False
            try:
                data = urllib2.urlopen(url).read().lower()
                if '</opml>' in data:
                    # This looks like an OPML feed
                    self.on_item_import_from_file_activate(None, url)
                    handled = True

                elif '</html>' in data:
                    # This looks like a web page
                    title = _('The URL is a website')
                    message = _('The URL you specified points to a web page. You need to find the "feed" URL of the podcast to add to gPodder. Do you want to visit this website now and look for the podcast feed URL?\n\n(Hint: Look for "XML feed", "RSS feed" or "Podcast feed" if you are unsure for what to look. If there is only an iTunes URL, try adding this one.)')
                    if self.show_confirmation(message, title):
                        util.open_website(url)
                        handled = True

            except Exception, e:
                log('Error trying to handle the URL as OPML or web page: %s', e, sender=self)

            if not handled:
                title = _('Error adding podcast')
                message = _('The podcast could not be added. Please check the spelling of the URL or try again later.')
                self.show_message( message, title)

        self.entryAddChannel.set_text(self.ENTER_URL_TEXT)
        self.entryAddChannel.set_sensitive(True)
        self.btnAddChannel.set_sensitive(True)
        self.update_podcasts_tab()
        self._update_cover(channel)
        waitdlg.destroy()


    def update_feed_cache_finish_callback(self, updated_urls=None, select_url_afterwards=None):
        self.db.commit()
        self.updating_feed_cache = False

        self.channels = PodcastChannel.load_from_db(self.db, self.config.download_dir)
        self.channel_list_changed = True
        self.updateComboBox(selected_url=select_url_afterwards)

        # Only search for new episodes in podcasts that have been
        # updated, not in other podcasts (for single-feed updates)
        episodes = self.get_new_episodes([c for c in self.channels if c.url in updated_urls])

        if self.tray_icon:
            self.tray_icon.set_status()

        if self.feed_cache_update_cancelled:
            # The user decided to abort the feed update
            self.show_update_feeds_buttons()
        elif not episodes:
            # Nothing new here - but inform the user
            self.pbFeedUpdate.set_fraction(1.0)
            self.pbFeedUpdate.set_text(_('No new episodes'))
            self.feed_cache_update_cancelled = True
            self.btnCancelFeedUpdate.show()
            self.btnCancelFeedUpdate.set_sensitive(True)
            if gpodder.interface == gpodder.MAEMO:
                # btnCancelFeedUpdate is a ToolButton on Maemo
                self.btnCancelFeedUpdate.set_stock_id(gtk.STOCK_APPLY)
            else:
                # btnCancelFeedUpdate is a normal gtk.Button
                self.btnCancelFeedUpdate.set_image(gtk.image_new_from_stock(gtk.STOCK_APPLY, gtk.ICON_SIZE_BUTTON))
        else:
            # New episodes are available
            self.pbFeedUpdate.set_fraction(1.0)
            # Are we minimized and should we auto download?
            if (self.minimized and (self.config.auto_download == 'minimized')) or (self.config.auto_download == 'always'):
                self.download_episode_list(episodes)
                if len(episodes) == 1:
                    title = _('Downloading one new episode')
                else:
                    title = _('Downloading %d new episodes') % len(episodes)

                if self.tray_icon:
                    message = self.tray_icon.format_episode_list([e.title for e in episodes])
                    self.tray_icon.send_notification(message, title)
                self.show_update_feeds_buttons()
            else:
                self.show_update_feeds_buttons()
                # New episodes are available and we are not minimized
                if not self.config.do_not_show_new_episodes_dialog:
                    self.new_episodes_show(episodes)
                else:
                    if len(episodes) == 1:
                        message = _('One new episode is available for download') 
                    else:
                        message = _('%i new episodes are available for download' % len(episodes))
                    
                    self.pbFeedUpdate.set_text(message)

    def _update_cover(self, channel):
        if not os.path.exists(channel.cover_file) and channel.image:
            self.cover_downloader.request_cover(channel)

    def update_feed_cache_proc(self, channels, select_url_afterwards):
        total = len(channels)

        for updated, channel in enumerate(channels):
            if not self.feed_cache_update_cancelled:
                try:
                    channel.update(max_episodes=self.config.max_episodes_per_feed)
                    self._update_cover(channel)
#                except feedcore.Offline:
#                    self.feed_cache_update_cancelled = True
#                    if not self.minimized:
#                        util.idle_add(self.show_message, _('The feed update has been cancelled because you appear to be offline.'), _('Cannot connect to server'))
#                    break
                except Exception, e:
                    util.idle_add(self.show_message, _('There has been an error updating %s: %s') % (saxutils.escape(channel.url), saxutils.escape(str(e))), _('Error while updating feed'))
                    log('Error: %s', str(e), sender=self, traceback=True)

            # By the time we get here the update may have already been cancelled
            if not self.feed_cache_update_cancelled:
                def update_progress():
                    progression = _('Updated %s (%d/%d)') % (channel.title, updated, total)
                    self.pbFeedUpdate.set_text(progression)
                    if self.tray_icon:
                        self.tray_icon.set_status(self.tray_icon.STATUS_UPDATING_FEED_CACHE, progression)
                    self.pbFeedUpdate.set_fraction(float(updated)/float(total))
                util.idle_add(update_progress)

            if self.feed_cache_update_cancelled:
                break

        updated_urls = [c.url for c in channels]
        util.idle_add(self.update_feed_cache_finish_callback, updated_urls, select_url_afterwards)

    def show_update_feeds_buttons(self):
        # Make sure that the buttons for updating feeds
        # appear - this should happen after a feed update
        if gpodder.interface == gpodder.MAEMO:
            self.btnUpdateSelectedFeed.show()
            self.toolFeedUpdateProgress.hide()
            self.btnCancelFeedUpdate.hide()
            self.btnCancelFeedUpdate.set_is_important(False)
            self.btnCancelFeedUpdate.set_stock_id(gtk.STOCK_CLOSE)
            self.toolbarSpacer.set_expand(True)
            self.toolbarSpacer.set_draw(False)
        else:
            self.hboxUpdateFeeds.hide()
        self.btnUpdateFeeds.show()
        self.itemUpdate.set_sensitive(True)
        self.itemUpdateChannel.set_sensitive(True)

    def on_btnCancelFeedUpdate_clicked(self, widget):
        if not self.feed_cache_update_cancelled:
            self.pbFeedUpdate.set_text(_('Cancelling...'))
            self.feed_cache_update_cancelled = True
            self.btnCancelFeedUpdate.set_sensitive(False)
        else:
            self.show_update_feeds_buttons()

    def update_feed_cache(self, channels=None, force_update=True, select_url_afterwards=None):
        if self.updating_feed_cache: 
            return

        if not force_update:
            self.channels = PodcastChannel.load_from_db(self.db, self.config.download_dir)
            self.channel_list_changed = True
            self.updateComboBox(selected_url=select_url_afterwards)
            return
        
        self.updating_feed_cache = True
        self.itemUpdate.set_sensitive(False)
        self.itemUpdateChannel.set_sensitive(False)

        if self.tray_icon:
            self.tray_icon.set_status(self.tray_icon.STATUS_UPDATING_FEED_CACHE)
        
        if channels is None:
            channels = self.channels

        if len(channels) == 1:
            text = _('Updating "%s"...') % channels[0].title
        else:
            text = _('Updating %d feeds...') % len(channels)
        self.pbFeedUpdate.set_text(text)
        self.pbFeedUpdate.set_fraction(0)

        self.feed_cache_update_cancelled = False
        self.btnCancelFeedUpdate.show()
        self.btnCancelFeedUpdate.set_sensitive(True)
        if gpodder.interface == gpodder.MAEMO:
            self.toolbarSpacer.set_expand(False)
            self.toolbarSpacer.set_draw(True)
            self.btnUpdateSelectedFeed.hide()
            self.toolFeedUpdateProgress.show_all()
        else:
            self.btnCancelFeedUpdate.set_image(gtk.image_new_from_stock(gtk.STOCK_STOP, gtk.ICON_SIZE_BUTTON))
            self.hboxUpdateFeeds.show_all()
        self.btnUpdateFeeds.hide()

        args = (channels, select_url_afterwards)
        Thread(target=self.update_feed_cache_proc, args=args).start()

    def on_gPodder_delete_event(self, widget, *args):
        """Called when the GUI wants to close the window
        Displays a confirmation dialog (and closes/hides gPodder)
        """

        downloading = self.download_status_model.are_downloads_in_progress()

        # Only iconify if we are using the window's "X" button,
        # but not when we are using "Quit" in the menu or toolbar
        if not self.config.on_quit_ask and self.config.on_quit_systray and self.tray_icon and widget.get_name() not in ('toolQuit', 'itemQuit'):
            self.iconify_main_window()
        elif self.config.on_quit_ask or downloading:
            if gpodder.interface == gpodder.MAEMO:
                result = self.show_confirmation(_('Do you really want to quit gPodder now?'))
                if result:
                    self.close_gpodder()
                else:
                    return True
            dialog = gtk.MessageDialog(self.gPodder, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_NONE)
            dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
            dialog.add_button(gtk.STOCK_QUIT, gtk.RESPONSE_CLOSE)

            title = _('Quit gPodder')
            if downloading:
                message = _('You are downloading episodes. You can resume downloads the next time you start gPodder. Do you want to quit now?')
            else:
                message = _('Do you really want to quit gPodder now?')

            dialog.set_title(title)
            dialog.set_markup('<span weight="bold" size="larger">%s</span>\n\n%s'%(title, message))
            if not downloading:
                cb_ask = gtk.CheckButton(_("Don't ask me again"))
                dialog.vbox.pack_start(cb_ask)
                cb_ask.show_all()

            result = dialog.run()
            dialog.destroy()

            if result == gtk.RESPONSE_CLOSE:
                if not downloading and cb_ask.get_active() == True:
                    self.config.on_quit_ask = False
                self.close_gpodder()
        else:
            self.close_gpodder()

        return True

    def close_gpodder(self):
        """ clean everything and exit properly
        """
        if self.channels:
            if self.save_channels_opml():
                if self.config.my_gpodder_autoupload:
                    log('Uploading to my.gpodder.org on close', sender=self)
                    util.idle_add(self.on_upload_to_mygpo, None)
            else:
                self.show_message(_('Please check your permissions and free disk space.'), _('Error saving podcast list'))

        self.gPodder.hide()

        if self.tray_icon is not None:
            self.tray_icon.set_visible(False)

        # Notify all tasks to to carry out any clean-up actions
        self.download_status_model.tell_all_tasks_to_quit()

        while gtk.events_pending():
            gtk.main_iteration(False)

        self.db.close()

        self.quit()
        sys.exit(0)

    def get_old_episodes(self):
        episodes = []
        for channel in self.channels:
            for episode in channel.get_downloaded_episodes():
                if episode.age_in_days() > self.config.episode_old_age and \
                        not episode.is_locked and episode.is_played:
                    episodes.append(episode)
        return episodes

    def delete_episode_list( self, episodes, confirm = True):
        if len(episodes) == 0:
            return

        if len(episodes) == 1:
            message = _('Do you really want to delete this episode?')
        else:
            message = _('Do you really want to delete %d episodes?') % len(episodes)

        if confirm and self.show_confirmation( message, _('Delete episodes')) == False:
            return

        episode_urls = set()
        channel_urls = set()
        for episode in episodes:
            log('Deleting episode: %s', episode.title, sender = self)
            episode.delete_from_disk()
            episode_urls.add(episode.url)
            channel_urls.add(episode.channel.url)

        # Episodes have been deleted - persist the database
        self.db.commit()

        self.update_episode_list_icons(episode_urls)
        self.updateComboBox(only_these_urls=channel_urls)

    def on_itemRemoveOldEpisodes_activate( self, widget):
        columns = (
                ('title_markup', None, None, _('Episode')),
                ('channel_prop', None, None, _('Podcast')),
                ('filesize_prop', 'length', gobject.TYPE_INT, _('Size')),
                ('pubdate_prop', 'pubDate', gobject.TYPE_INT, _('Released')),
                ('played_prop', None, None, _('Status')),
                ('age_prop', None, None, _('Downloaded')),
        )

        selection_buttons = {
                _('Select played'): lambda episode: episode.is_played,
                _('Select older than %d days') % self.config.episode_old_age: lambda episode: episode.age_in_days() > self.config.episode_old_age,
        }

        instructions = _('Select the episodes you want to delete from your hard disk.')

        episodes = []
        selected = []
        for channel in self.channels:
            for episode in channel.get_downloaded_episodes():
                if not episode.is_locked:
                    episodes.append(episode)
                    selected.append(episode.is_played)

        gPodderEpisodeSelector(self.gPodder, title = _('Remove old episodes'), instructions = instructions, \
                                episodes = episodes, selected = selected, columns = columns, \
                                stock_ok_button = gtk.STOCK_DELETE, callback = self.delete_episode_list, \
                                selection_buttons = selection_buttons, _config=self.config)

    def on_selected_episodes_status_changed(self):
        self.update_selected_episode_list_icons()
        self.updateComboBox(only_selected_channel=True)
        self.db.commit()

    def mark_selected_episodes_new(self):
        for episode in self.get_selected_episodes():
            episode.mark_new()
        self.on_selected_episodes_status_changed()

    def mark_selected_episodes_old(self):
        for episode in self.get_selected_episodes():
            episode.mark_old()
        self.on_selected_episodes_status_changed()

    def on_item_toggle_played_activate( self, widget, toggle = True, new_value = False):
        for episode in self.get_selected_episodes():
            if toggle:
                episode.mark(is_played=not episode.is_played)
            else:
                episode.mark(is_played=new_value)
        self.on_selected_episodes_status_changed()

    def on_item_toggle_lock_activate(self, widget, toggle=True, new_value=False):
        for episode in self.get_selected_episodes():
            if toggle:
                episode.mark(is_locked=not episode.is_locked)
            else:
                episode.mark(is_locked=new_value)
        self.on_selected_episodes_status_changed()

    def on_channel_toggle_lock_activate(self, widget, toggle=True, new_value=False):
        self.active_channel.channel_is_locked = not self.active_channel.channel_is_locked
        self.active_channel.update_channel_lock()

        if self.active_channel.channel_is_locked:
            self.change_menu_item(self.channel_toggle_lock, gtk.STOCK_DIALOG_AUTHENTICATION, _('Allow deletion of all episodes'))
        else:
            self.change_menu_item(self.channel_toggle_lock, gtk.STOCK_DIALOG_AUTHENTICATION, _('Prohibit deletion of all episodes'))

        for episode in self.active_channel.get_all_episodes():
            episode.mark(is_locked=self.active_channel.channel_is_locked)

        self.updateComboBox(only_selected_channel=True)
        self.update_episode_list_icons([e.url for e in self.active_channel.get_all_episodes()])

    def send_subscriptions(self):
        try:
            subprocess.Popen(['xdg-email', '--subject', _('My podcast subscriptions'),
                                           '--attach', gpodder.subscription_file])
        except:
            return False

        return True

    def on_item_email_subscriptions_activate(self, widget):
        if not self.channels:
            self.show_message(_('Your subscription list is empty.'), _('Could not send list'))
        elif not self.send_subscriptions():
            self.show_message(_('There was an error sending your subscription list via e-mail.'), _('Could not send list'))

    def on_itemUpdateChannel_activate(self, widget=None):
        self.update_feed_cache(channels=[self.active_channel,])

    def on_itemUpdate_activate(self, widget=None):
        if self.channels:
            self.update_feed_cache()
        else:
            gPodderWelcome(self.gPodder, center_on_widget=self.gPodder, show_example_podcasts_callback=self.on_itemImportChannels_activate, setup_my_gpodder_callback=self.on_download_from_mygpo)

    def download_episode_list_paused(self, episodes):
        self.download_episode_list(episodes, True)

    def download_episode_list(self, episodes, add_paused=False):
        for episode in episodes:
            log('Downloading episode: %s', episode.title, sender = self)
            if not episode.was_downloaded(and_exists=True):
                task_exists = False
                for task in self.download_tasks_seen:
                    if episode.url == task.url and task.status not in (task.DOWNLOADING, task.QUEUED):
                        self.download_queue_manager.add_task(task)
                        self.enable_download_list_update()
                        task_exists = True
                        continue

                if task_exists:
                    continue

                try:
                    task = download.DownloadTask(episode, self.config)
                except Exception, e:
                    self.show_message(_('Download error while downloading %s:\n\n%s') % (episode.title, str(e)), _('Download error'))
                    log('Download error while downloading %s', episode.title, sender=self, traceback=True)
                    continue

                if add_paused:
                    task.status = task.PAUSED
                else:
                    self.download_queue_manager.add_task(task)

                self.download_status_model.register_task(task)
                self.enable_download_list_update()

    def new_episodes_show(self, episodes):
        columns = (
                ('title_markup', None, None, _('Episode')),
                ('channel_prop', None, None, _('Podcast')),
                ('filesize_prop', 'length', gobject.TYPE_INT, _('Size')),
                ('pubdate_prop', 'pubDate', gobject.TYPE_INT, _('Released')),
        )

        instructions = _('Select the episodes you want to download now.')

        gPodderEpisodeSelector(self.gPodder, title=_('New episodes available'), instructions=instructions, \
                               episodes=episodes, columns=columns, selected_default=True, \
                               stock_ok_button = 'gpodder-download', \
                               callback=self.download_episode_list, \
                               remove_callback=lambda e: e.mark_old(), \
                               remove_action=_('Never download'), \
                               remove_finished=self.episode_new_status_changed, \
                               _config=self.config)

    def on_itemDownloadAllNew_activate(self, widget, *args):
        new_episodes = self.get_new_episodes()
        if len(new_episodes):
            self.new_episodes_show(new_episodes)
        else:
            msg = _('No new episodes available for download')
            if self.tray_icon is not None and self.minimized:
                self.tray_icon.send_notification(msg)
            else:
                self.show_message(msg, _('No new episodes'))

    def get_new_episodes(self, channels=None):
        if channels is None:
            channels = self.channels
        episodes = []
        for channel in channels:
            for episode in channel.get_new_episodes(downloading=self.episode_is_downloading):
                episodes.append(episode)

        return episodes

    def get_all_episodes(self, exclude_nonsignificant=True ):
        """'exclude_nonsignificant' will exclude non-downloaded episodes
            and all episodes from channels that are set to skip when syncing"""
        episode_list = []
        for channel in self.channels:
            if not channel.sync_to_devices and exclude_nonsignificant:
                log('Skipping channel: %s', channel.title, sender=self)
                continue
            for episode in channel.get_all_episodes():
                if episode.was_downloaded(and_exists=True) or not exclude_nonsignificant:
                    episode_list.append(episode)
        return episode_list

    def ipod_delete_played(self, device):
        all_episodes = self.get_all_episodes( exclude_nonsignificant=False )
        episodes_on_device = device.get_all_tracks()
        for local_episode in all_episodes:
            device_episode = device.episode_on_device(local_episode)
            if device_episode and ( local_episode.is_played and not local_episode.is_locked
                or local_episode.state == gpodder.STATE_DELETED ):
                log("mp3_player_delete_played: removing %s" % device_episode.title)
                device.remove_track(device_episode)

    def on_sync_to_ipod_activate(self, widget, episodes=None):
        # make sure gpod is available before even trying to sync
        if self.config.device_type == 'ipod' and not sync.gpod_available:
            title = _('Cannot Sync To iPod')
            message = _('Please install the libgpod python bindings (python-gpod) and restart gPodder to continue.')
            self.notification( message, title )
            return
        elif self.config.device_type == 'mtp' and not sync.pymtp_available:
            title = _('Cannot sync to MTP device')
            message = _('Please install the libmtp python bindings (python-pymtp) and restart gPodder to continue.')
            self.notification( message, title )
            return

        device = sync.open_device(self.config)
        device.register( 'post-done', self.sync_to_ipod_completed )

        if device is None:
            title = _('No device configured')
            message = _('To use the synchronization feature, please configure your device in the preferences dialog first.')
            self.notification(message, title)
            return

        if not device.open():
            title = _('Cannot open device')
            message = _('There has been an error opening your device.')
            self.notification(message, title)
            return

        if self.config.device_type == 'ipod':
            #update played episodes and delete if requested
            for channel in self.channels:
                if channel.sync_to_devices:
                    allepisodes = [ episode for episode in channel.get_all_episodes() if  episode.was_downloaded(and_exists=True) ]
                    device.update_played_or_delete(channel, allepisodes, self.config.ipod_delete_played_from_db)

            if self.config.ipod_purge_old_episodes:
                device.purge()

        sync_all_episodes = not bool(episodes)

        if episodes is None:
            episodes = self.get_all_episodes()

        # make sure we have enough space on the device
        can_sync = True
        total_size = 0
        free_space = max(device.get_free_space(), 0)
        for episode in episodes:
            if not device.episode_on_device(episode) and not (sync_all_episodes and self.config.only_sync_not_played and episode.is_played):
                filename = episode.local_filename(create=False)
                if filename is not None:
                    total_size += util.calculate_size(str(filename))

        if total_size > free_space:
            title = _('Not enough space left on device')
            message = _('You need to free up %s.\nDo you want to continue?') % (util.format_filesize(total_size-free_space),)
            can_sync = self.show_confirmation(message, title)

        if self.tray_icon:
            self.tray_icon.set_synchronisation_device(device)

        if can_sync:
            gPodderSyncProgress(self.gPodder, device=device, gPodder=self)
            Thread(target=self.sync_to_ipod_thread, args=(widget, device, sync_all_episodes, episodes)).start()
        else:
            device.close()

        # The sync process might have updated the status of episodes,
        # therefore persist the database here to avoid losing data
        self.db.commit()

    def sync_to_ipod_completed(self, device, successful_sync):
        device.unregister( 'post-done', self.sync_to_ipod_completed )

        if self.tray_icon:
            self.tray_icon.release_synchronisation_device()
 
        if not successful_sync:
            title = _('Error closing device')
            message = _('There has been an error closing your device.')
            self.notification(message, title)

        # update model for played state updates after sync
        util.idle_add(self.updateComboBox)

    def sync_to_ipod_thread(self, widget, device, sync_all_episodes, episodes=None):
        if sync_all_episodes:
            device.add_tracks(episodes)
            # 'only_sync_not_played' must be used or else all the played
            #  tracks will be copied then immediately deleted
            if self.config.mp3_player_delete_played and self.config.only_sync_not_played:
                self.ipod_delete_played(device)
        else:
            device.add_tracks(episodes, force_played=True)
        device.close()
        self.update_selected_episode_list_icons()

    def ipod_cleanup_callback(self, device, tracks):
        title = _('Delete podcasts from device?')
        message = _('The selected episodes will be removed from your device. This cannot be undone. Files in your gPodder library will be unaffected. Do you really want to delete these episodes from your device?')
        if len(tracks) > 0 and self.show_confirmation(message, title):
            gPodderSyncProgress(self.gPodder, device=device, gPodder=self)
            Thread(target=self.ipod_cleanup_thread, args=[device, tracks]).start()

    def ipod_cleanup_thread(self, device, tracks):
        device.remove_tracks(tracks)
 
        if not device.close():
            title = _('Error closing device')
            message = _('There has been an error closing your device.')
            gobject.idle_add(self.show_message, message, title)

    def on_cleanup_ipod_activate(self, widget, *args):
        columns = (
                ('title', None, None, _('Episode')),
                ('podcast', None, None, _('Podcast')),
                ('filesize', None, None, _('Size')),
                ('modified', 'modified_sort', gobject.TYPE_INT, _('Copied')),
                ('playcount', None, None, _('Play count')),
                ('released', None, None, _('Released')),
        )

        device = sync.open_device(self.config)

        if device is None:
            title = _('No device configured')
            message = _('To use the synchronization feature, please configure your device in the preferences dialog first.')
            self.show_message(message, title)
            return

        if not device.open():
            title = _('Cannot open device')
            message = _('There has been an error opening your device.')
            self.show_message(message, title)
            return

        tracks = device.get_all_tracks()
        if len(tracks) > 0:
            remove_tracks_callback = lambda tracks: self.ipod_cleanup_callback(device, tracks)
            wanted_columns = []
            for key, sort_name, sort_type, caption in columns:
                want_this_column = False
                for track in tracks:
                    if getattr(track, key) is not None:
                        want_this_column = True
                        break

                if want_this_column:
                    wanted_columns.append((key, sort_name, sort_type, caption))
            title = _('Remove podcasts from device')
            instructions = _('Select the podcast episodes you want to remove from your device.')
            gPodderEpisodeSelector(self.gPodder, title=title, instructions=instructions, episodes=tracks, columns=wanted_columns, \
                                   stock_ok_button=gtk.STOCK_DELETE, callback=remove_tracks_callback, tooltip_attribute=None, \
                                   _config=self.config)
        else:
            title = _('No files on device')
            message = _('The devices contains no files to be removed.')
            self.show_message(message, title)
            device.close()

    def on_manage_device_playlist(self, widget):
        # make sure gpod is available before even trying to sync
        if self.config.device_type == 'ipod' and not sync.gpod_available:
            title = _('Cannot manage iPod playlist')
            message = _('This feature is not available for iPods.')
            self.notification( message, title )
            return
        elif self.config.device_type == 'mtp' and not sync.pymtp_available:
            title = _('Cannot manage MTP device playlist')
            message = _('This feature is not available for MTP devices.')
            self.notification( message, title )
            return

        device = sync.open_device(self.config)

        if device is None:
            title = _('No device configured')
            message = _('To use the playlist feature, please configure your Filesystem based MP3-Player in the preferences dialog first.')
            self.notification(message, title)
            return

        if not device.open():
            title = _('Cannot open device')
            message = _('There has been an error opening your device.')
            self.notification(message, title)
            return

        gPodderPlaylist(self.gPodder, device=device, gPodder=self, _config=self.config)
        device.close()

    def show_hide_tray_icon(self):
        if self.config.display_tray_icon and have_trayicon and self.tray_icon is None:
            self.tray_icon = trayicon.GPodderStatusIcon(self, gpodder.icon_file, self.config)
        elif not self.config.display_tray_icon and self.tray_icon is not None:
            self.tray_icon.set_visible(False)
            del self.tray_icon
            self.tray_icon = None

        if self.config.minimize_to_tray and self.tray_icon:
            self.tray_icon.set_visible(self.minimized)
        elif self.tray_icon:
            self.tray_icon.set_visible(True)

    def on_itemShowToolbar_activate(self, widget):
        self.config.show_toolbar = self.itemShowToolbar.get_active()

    def on_itemShowDescription_activate(self, widget):
        self.config.episode_list_descriptions = self.itemShowDescription.get_active()

    def update_item_device( self):
        if self.config.device_type != 'none':
            self.itemDevice.set_visible(True)
            self.itemDevice.label = self.get_device_name()
        else:
            self.itemDevice.set_visible(False)

    def properties_closed( self):
        self.show_hide_tray_icon()
        self.update_item_device()
        self.updateComboBox()

    def on_itemPreferences_activate(self, widget, *args):
        gPodderPreferences(self.gPodder, _config=self.config, \
                callback_finished=self.properties_closed, \
                user_apps_reader=self.user_apps_reader)

    def on_itemDependencies_activate(self, widget):
        gPodderDependencyManager(self.gPodder)

    def on_add_new_google_search(self, widget, *args):
        def add_google_video_search(query):
            self.add_new_channel('http://video.google.com/videofeed?type=search&q='+urllib.quote(query)+'&so=1&num=250&output=rss')

        gPodderAddPodcast(self.gPodder, url_callback=add_google_video_search, custom_title=_('Add Google Video search'), custom_label=_('Search for:'))

    def on_upgrade_from_videocenter(self, widget):
        from gpodder import nokiavideocenter
        vc = nokiavideocenter.UpgradeFromVideocenter()
        if vc.db2opml():
            gPodderOpmlLister(self.gPodder, _config=self.config, custom_title=_('Import podcasts from Video Center'), hide_url_entry=True).get_channels_from_url(vc.opmlfile, lambda url: self.add_new_channel(url,False,block=True), lambda: self.on_itemDownloadAllNew_activate(self.gPodder))
        else:
            self.show_message(_('Have you installed Video Center on your tablet?'), _('Cannot find Video Center subscriptions'))

    def require_my_gpodder_authentication(self):
        if not self.config.my_gpodder_username or not self.config.my_gpodder_password:
            success, authentication = self.UsernamePasswordDialog(_('Login to my.gpodder.org'), _('Please enter your e-mail address and your password.'), username=self.config.my_gpodder_username, password=self.config.my_gpodder_password, username_prompt=_('E-Mail Address'), register_callback=lambda: util.open_website('http://my.gpodder.org/register'))
            if success and authentication[0] and authentication[1]:
                self.config.my_gpodder_username, self.config.my_gpodder_password = authentication
                return True
            else:
                return False

        return True
    
    def my_gpodder_offer_autoupload(self):
        if not self.config.my_gpodder_autoupload:
            if self.show_confirmation(_('gPodder can automatically upload your subscription list to my.gpodder.org when you close it. Do you want to enable this feature?'), _('Upload subscriptions on quit')):
                self.config.my_gpodder_autoupload = True
    
    def on_download_from_mygpo(self, widget):
        if self.require_my_gpodder_authentication():
            client = my.MygPodderClient(self.config.my_gpodder_username, self.config.my_gpodder_password)
            opml_data = client.download_subscriptions()
            if len(opml_data) > 0:
                fp = open(gpodder.subscription_file, 'w')
                fp.write(opml_data)
                fp.close()
                (added, skipped) = (0, 0)
                i = opml.Importer(gpodder.subscription_file)
                for item in i.items:
                    url = item['url']
                    if url not in (c.url for c in self.channels):
                        self.add_new_channel(url, ask_download_new=False, block=True)
                        added += 1
                    else:
                        log('Already added: %s', url, sender=self)
                        skipped += 1
                self.updateComboBox()
                if added > 0:
                    self.show_message(_('Added %d new subscriptions and skipped %d existing ones.') % (added, skipped), _('Result of subscription download'))
                elif widget is not None:
                    self.show_message(_('Your local subscription list is up to date.'), _('Result of subscription download'))
                self.my_gpodder_offer_autoupload()
            else:
                self.config.my_gpodder_password = ''
                self.on_download_from_mygpo(widget)
        else:
            self.show_message(_('Please set up your username and password first.'), _('Username and password needed'))

    def on_upload_to_mygpo(self, widget):
        if self.require_my_gpodder_authentication():
            client = my.MygPodderClient(self.config.my_gpodder_username, self.config.my_gpodder_password)
            self.save_channels_opml()
            success, messages = client.upload_subscriptions(gpodder.subscription_file)
            if widget is not None:
                self.show_message('\n'.join(messages), _('Results of upload'))
                if not success:
                    self.config.my_gpodder_password = ''
                    self.on_upload_to_mygpo(widget)
                else:
                    self.my_gpodder_offer_autoupload()
            elif not success:
                log('Upload to my.gpodder.org failed, but widget is None!', sender=self)
        elif widget is not None:
            self.show_message(_('Please set up your username and password first.'), _('Username and password needed'))

    def on_itemAddChannel_activate(self, widget, *args):
        gPodderAddPodcast(self.gPodder, url_callback=self.add_new_channel)

    def on_itemEditChannel_activate(self, widget, *args):
        if self.active_channel is None:
            title = _('No podcast selected')
            message = _('Please select a podcast in the podcasts list to edit.')
            self.show_message( message, title)
            return

        gPodderChannel(self.main_window, channel=self.active_channel, callback_closed=lambda: self.updateComboBox(only_selected_channel=True), cover_downloader=self.cover_downloader)

    def on_itemRemoveChannel_activate(self, widget, *args):
        try:
            if gpodder.interface == gpodder.GUI:
                dialog = gtk.MessageDialog(self.gPodder, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_NONE)
                dialog.add_button(gtk.STOCK_NO, gtk.RESPONSE_NO)
                dialog.add_button(gtk.STOCK_YES, gtk.RESPONSE_YES)

                title = _('Remove podcast and episodes?')
                message = _('Do you really want to remove <b>%s</b> and all downloaded episodes?') % saxutils.escape(self.active_channel.title)
             
                dialog.set_title(title)
                dialog.set_markup('<span weight="bold" size="larger">%s</span>\n\n%s'%(title, message))
            
                cb_ask = gtk.CheckButton(_('Do not delete my downloaded episodes'))
                dialog.vbox.pack_start(cb_ask)
                cb_ask.show_all()
                affirmative = gtk.RESPONSE_YES
            elif gpodder.interface == gpodder.MAEMO:
                cb_ask = gtk.CheckButton('') # dummy check button
                dialog = hildon.Note('confirmation', (self.gPodder, _('Do you really want to remove this podcast and all downloaded episodes?')))
                affirmative = gtk.RESPONSE_OK

            result = dialog.run()
            dialog.destroy()

            if result == affirmative:
                # delete downloaded episodes only if checkbox is unchecked
                if cb_ask.get_active() == False:
                    self.active_channel.remove_downloaded()
                else:
                    log('Not removing downloaded episodes', sender=self)

                # Clean up downloads and download directories
                self.clean_up_downloads()

                # cancel any active downloads from this channel
                for episode in self.active_channel.get_all_episodes():
                    self.download_status_model.cancel_by_url(episode.url)

                # get the URL of the podcast we want to select next
                position = self.channels.index(self.active_channel)
                if position == len(self.channels)-1:
                    # this is the last podcast, so select the URL
                    # of the item before this one (i.e. the "new last")
                    select_url = self.channels[position-1].url
                else:
                    # there is a podcast after the deleted one, so
                    # we simply select the one that comes after it
                    select_url = self.channels[position+1].url
                
                # Remove the channel
                self.active_channel.delete()
                self.channels.remove(self.active_channel)
                self.channel_list_changed = True
                self.save_channels_opml()

                # Re-load the channels and select the desired new channel
                self.update_feed_cache(force_update=False, select_url_afterwards=select_url)
        except:
            log('There has been an error removing the channel.', traceback=True, sender=self)
        self.update_podcasts_tab()

    def get_opml_filter(self):
        filter = gtk.FileFilter()
        filter.add_pattern('*.opml')
        filter.add_pattern('*.xml')
        filter.set_name(_('OPML files')+' (*.opml, *.xml)')
        return filter

    def on_item_import_from_file_activate(self, widget, filename=None):
        if filename is None:
            if gpodder.interface == gpodder.GUI:
                dlg = gtk.FileChooserDialog(title=_('Import from OPML'), parent=None, action=gtk.FILE_CHOOSER_ACTION_OPEN)
                dlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
                dlg.add_button(gtk.STOCK_OPEN, gtk.RESPONSE_OK)
            elif gpodder.interface == gpodder.MAEMO:
                dlg = hildon.FileChooserDialog(self.gPodder, gtk.FILE_CHOOSER_ACTION_OPEN)
            dlg.set_filter(self.get_opml_filter())
            response = dlg.run()
            filename = None
            if response == gtk.RESPONSE_OK:
                filename = dlg.get_filename()
            dlg.destroy()

        if filename is not None:
            gPodderOpmlLister(self.gPodder, _config=self.config, custom_title=_('Import podcasts from OPML file'), hide_url_entry=True).get_channels_from_url(filename, lambda url: self.add_new_channel(url,False,block=True), lambda: self.on_itemDownloadAllNew_activate(self.gPodder))

    def on_itemExportChannels_activate(self, widget, *args):
        if not self.channels:
            title = _('Nothing to export')
            message = _('Your list of podcast subscriptions is empty. Please subscribe to some podcasts first before trying to export your subscription list.')
            self.show_message( message, title)
            return

        if gpodder.interface == gpodder.GUI:
            dlg = gtk.FileChooserDialog(title=_('Export to OPML'), parent=self.gPodder, action=gtk.FILE_CHOOSER_ACTION_SAVE)
            dlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
            dlg.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_OK)
        elif gpodder.interface == gpodder.MAEMO:
            dlg = hildon.FileChooserDialog(self.gPodder, gtk.FILE_CHOOSER_ACTION_SAVE)
        dlg.set_filter(self.get_opml_filter())
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            filename = dlg.get_filename()
            dlg.destroy()
            exporter = opml.Exporter( filename)
            if exporter.write(self.channels):
                if len(self.channels) == 1:
                    title = _('One subscription exported')
                else:
                    title = _('%d subscriptions exported') % len(self.channels)
                self.show_message(_('Your podcast list has been successfully exported.'), title)
            else:
                self.show_message( _('Could not export OPML to file. Please check your permissions.'), _('OPML export failed'))
        else:
            dlg.destroy()

    def on_itemImportChannels_activate(self, widget, *args):
        gPodderOpmlLister(self.gPodder, _config=self.config).get_channels_from_url(self.config.opml_url, lambda url: self.add_new_channel(url,False,block=True), lambda: self.on_itemDownloadAllNew_activate(self.gPodder))

    def on_homepage_activate(self, widget, *args):
        util.open_website(gpodder.__url__)

    def on_wiki_activate(self, widget, *args):
        util.open_website('http://wiki.gpodder.org/')

    def on_bug_tracker_activate(self, widget, *args):
        if gpodder.interface == gpodder.MAEMO:
            util.open_website('http://bugs.maemo.org/enter_bug.cgi?product=gPodder')
        else:
            util.open_website('http://bugs.gpodder.org/')

    def on_shop_activate(self, widget, *args):
        util.open_website('http://gpodder.org/shop')

    def on_wishlist_activate(self, widget, *args):
        util.open_website('http://www.amazon.de/gp/registry/2PD2MYGHE6857')

    def on_itemAbout_activate(self, widget, *args):
        dlg = gtk.AboutDialog()
        dlg.set_name('gPodder')
        dlg.set_version(gpodder.__version__)
        dlg.set_copyright(gpodder.__copyright__)
        dlg.set_website(gpodder.__url__)
        dlg.set_translator_credits( _('translator-credits'))
        dlg.connect( 'response', lambda dlg, response: dlg.destroy())

        if gpodder.interface == gpodder.GUI:
            # For the "GUI" version, we add some more
            # items to the about dialog (credits and logo)
            dlg.set_authors(app_authors)
            try:
                dlg.set_logo(gtk.gdk.pixbuf_new_from_file(gpodder.icon_file))
            except:
                dlg.set_logo_icon_name('gpodder')
        
        dlg.run()

    def on_wNotebook_switch_page(self, widget, *args):
        page_num = args[1]
        if gpodder.interface == gpodder.MAEMO:
            self.tool_downloads.set_active(page_num == 1)
            page = self.wNotebook.get_nth_page(page_num)
            tab_label = self.wNotebook.get_tab_label(page).get_text()
            if page_num == 0 and self.active_channel is not None:
                self.set_title(self.active_channel.title)
            else:
                self.set_title(tab_label)
        if page_num == 0:
            self.play_or_download()
            self.menuChannels.set_sensitive(True)
            self.menuSubscriptions.set_sensitive(True)
            # The message area in the downloads tab should be hidden
            # when the user switches away from the downloads tab
            if self.message_area is not None:
                self.message_area.hide()
                self.message_area = None
        else:
            self.menuChannels.set_sensitive(False)
            self.menuSubscriptions.set_sensitive(False)
            self.toolDownload.set_sensitive( False)
            self.toolPlay.set_sensitive( False)
            self.toolTransfer.set_sensitive( False)
            self.toolCancel.set_sensitive( False)#services.download_status_model.has_items())

    def on_treeChannels_row_activated(self, widget, path, *args):
        # double-click action of the podcast list or enter
        self.treeChannels.set_cursor(path)

    def on_treeChannels_cursor_changed(self, widget, *args):
        ( model, iter ) = self.treeChannels.get_selection().get_selected()

        if model is not None and iter is not None:
            old_active_channel = self.active_channel
            self.active_channel = model.get_value(iter, PodcastListModel.C_CHANNEL)

            if self.active_channel == old_active_channel:
                return

            if gpodder.interface == gpodder.MAEMO:
                self.set_title(self.active_channel.title)
            self.itemEditChannel.set_visible(True)
            self.itemRemoveChannel.set_visible(True)
            self.channel_toggle_lock.set_visible(True)
            if self.active_channel.channel_is_locked:
                self.change_menu_item(self.channel_toggle_lock, gtk.STOCK_DIALOG_AUTHENTICATION, _('Allow deletion of all episodes'))
            else:
                self.change_menu_item(self.channel_toggle_lock, gtk.STOCK_DIALOG_AUTHENTICATION, _('Prohibit deletion of all episodes'))

        else:
            self.active_channel = None
            self.itemEditChannel.set_visible(False)
            self.itemRemoveChannel.set_visible(False)
            self.channel_toggle_lock.set_visible(False)

        self.updateTreeView()

    def on_entryAddChannel_changed(self, widget, *args):
        active = self.entryAddChannel.get_text() not in ('', self.ENTER_URL_TEXT)
        self.btnAddChannel.set_sensitive( active)

    def on_btnAddChannel_clicked(self, widget, *args):
        url = self.entryAddChannel.get_text()
        self.entryAddChannel.set_text('')
        self.add_new_channel( url)

    def on_btnEditChannel_clicked(self, widget, *args):
        self.on_itemEditChannel_activate( widget, args)

    def get_selected_episodes(self):
        """Get a list of selected episodes from treeAvailable"""
        selection = self.treeAvailable.get_selection()
        model, paths = selection.get_selected_rows()

        episodes = [model.get_value(model.get_iter(path), EpisodeListModel.C_EPISODE) for path in paths]
        return episodes

    def on_transfer_selected_episodes(self, widget):
        self.on_sync_to_ipod_activate(widget, self.get_selected_episodes())

    def on_playback_selected_episodes(self, widget):
        self.playback_episodes(self.get_selected_episodes())

    def on_shownotes_selected_episodes(self, widget):
        episodes = self.get_selected_episodes()
        if episodes:
            episode = episodes.pop(0)
            self.show_episode_shownotes(episode)
        else:
            self.show_message(_('No episode selected'), _('Please select an episode'))

    def on_download_selected_episodes(self, widget):
        episodes = self.get_selected_episodes()
        self.download_episode_list(episodes)
        self.update_episode_list_icons([episode.url for episode in episodes])
        self.play_or_download()

    def on_treeAvailable_row_activated(self, widget, path, view_column):
        """Double-click/enter action handler for treeAvailable"""
        # We should only have one one selected as it was double clicked!
        e = self.get_selected_episodes()[0]
        
        if (self.config.double_click_episode_action == 'download'):
            # If the episode has already been downloaded and exists then play it
            if e.was_downloaded(and_exists=True):
                self.playback_episodes(self.get_selected_episodes())
            # else download it if it is not already downloading
            elif not self.episode_is_downloading(e): 
                self.download_episode_list([e])
                self.update_episode_list_icons([e.url])
                self.play_or_download()
        elif (self.config.double_click_episode_action == 'stream'):
            # If we happen to have downloaded this episode simple play it
            if e.was_downloaded(and_exists=True):
                self.playback_episodes(self.get_selected_episodes())
            # else if streaming is possible stream it    
            elif self.streaming_possible():
                self.playback_episodes(self.get_selected_episodes())
            else:
                log('Unable to stream episode - default media player selected!', sender=self, traceback=True)
                self.show_message( _('Please check your media player settings in the preferences dialog.'), _('Unable to stream episode'))
        else:
            # default action is to display show notes
            self.on_shownotes_selected_episodes(widget)

    def show_episode_shownotes(self, episode):
        play_callback = lambda: self.playback_episodes([episode])
        def download_callback():
            self.download_episode_list([episode])
            self.play_or_download()
        if self.episode_shownotes_window is None:
            log('First-time use of episode window --- creating', sender=self)
            self.episode_shownotes_window = gPodderShownotes(self.gPodder, _config=self.config, \
                    download_status_model=self.download_status_model, \
                    episode_is_downloading=self.episode_is_downloading)
        self.episode_shownotes_window.show(episode=episode, download_callback=download_callback, play_callback=play_callback)

    def on_treeAvailable_button_release_event(self, widget, *args):
        self.play_or_download()

    def auto_update_procedure(self, first_run=False):
        log('auto_update_procedure() got called', sender=self)
        if not first_run and self.config.auto_update_feeds and self.minimized:
            self.update_feed_cache(force_update=True)

        next_update = 60*1000*self.config.auto_update_frequency
        gobject.timeout_add(next_update, self.auto_update_procedure)

    def on_treeDownloads_row_activated(self, widget, *args):
        if self.wNotebook.get_current_page() == 0:
            # Use the available podcasts treeview + model
            selection = self.treeAvailable.get_selection()
            (model, paths) = selection.get_selected_rows()
            urls = [model.get_value(model.get_iter(path), 0) for path in paths]
            selected_tasks = [task for task in self.download_tasks_seen if task.url in urls]
            for task in selected_tasks:
                task.status = task.CANCELLED
            self.update_selected_episode_list_icons()
            self.play_or_download()
            return

        # Use the standard way of working on the treeview
        selection = self.treeDownloads.get_selection()
        (model, paths) = selection.get_selected_rows()
        selected_tasks = [(gtk.TreeRowReference(model, path), model.get_value(model.get_iter(path), 0)) for path in paths]

        for tree_row_reference, task in selected_tasks:
            if task.status in (task.DOWNLOADING, task.QUEUED):
                task.status = task.PAUSED
            elif task.status in (task.CANCELLED, task.PAUSED, task.FAILED):
                self.download_queue_manager.add_task(task)
                self.enable_download_list_update()
            elif task.status == task.DONE:
                model.remove(model.get_iter(tree_row_reference.get_path()))
                
        self.play_or_download()

        # Update the tab title and downloads list
        self.update_downloads_list()

    def on_btnCancelDownloadStatus_clicked(self, widget, *args):
        self.on_treeDownloads_row_activated( widget, None)

    def on_btnCancelAll_clicked(self, widget, *args):
        self.treeDownloads.get_selection().select_all()
        self.on_treeDownloads_row_activated( self.toolCancel, None)
        self.treeDownloads.get_selection().unselect_all()

        # Update the tab title and downloads list
        self.update_downloads_list()

    def on_btnDownloadedDelete_clicked(self, widget, *args):
        if self.active_channel is None:
            return

        if self.wNotebook.get_current_page() == 1:
            # Downloads tab visible - no action!
            return

        episodes = self.get_selected_episodes()

        if not episodes:
            log('Nothing selected - will not remove any downloaded episode.')
            return

        if len(episodes) == 1:
            episode = episodes[0]
            if episode.is_locked:
                title = _('%s is locked') % saxutils.escape(episode.title)
                message = _('You cannot delete this locked episode. You must unlock it before you can delete it.')
                self.notification(message, title)
                return

            title = _('Remove %s?') % saxutils.escape(episode.title)
            message = _("If you remove this episode, it will be deleted from your computer. If you want to listen to this episode again, you will have to re-download it.")
        else:
            title = _('Remove %d episodes?') % len(episodes)
            message = _('If you remove these episodes, they will be deleted from your computer. If you want to listen to any of these episodes again, you will have to re-download the episodes in question.')

        locked_count = sum(int(e.is_locked) for e in episodes if e.is_locked is not None)

        if len(episodes) == locked_count:
            title = _('Episodes are locked')
            message = _('The selected episodes are locked. Please unlock the episodes that you want to delete before trying to delete them.')
            self.notification(message, title)
            return
        elif locked_count > 0:
            title = _('Remove %d out of %d episodes?') % (len(episodes)-locked_count, len(episodes))
            message = _('The selection contains locked episodes that will not be deleted. If you want to listen to the deleted episodes, you will have to re-download them.')

        # if user confirms deletion, let's remove some stuff ;)
        if self.show_confirmation(message, title):
            for episode in episodes:
                if not episode.is_locked:
                    episode.delete_from_disk()
            self.updateComboBox(only_selected_channel=True)

        # only delete partial files if we do not have any downloads in progress
        self.clean_up_downloads(False)
        self.update_selected_episode_list_icons()
        self.play_or_download()

    def on_key_press(self, widget, event):
        # Allow tab switching with Ctrl + PgUp/PgDown
        if event.state & gtk.gdk.CONTROL_MASK:
            if event.keyval == gtk.keysyms.Page_Up:
                self.wNotebook.prev_page()
                return True
            elif event.keyval == gtk.keysyms.Page_Down:
                self.wNotebook.next_page()
                return True

        # After this code we only handle Maemo hardware keys,
        # so if we are not a Maemo app, we don't do anything
        if gpodder.interface != gpodder.MAEMO:
            return False
        
        if event.keyval == gtk.keysyms.F6:
            if self.fullscreen:
                self.window.unfullscreen()
            else:
                self.window.fullscreen()
        if event.keyval == gtk.keysyms.Escape:
            new_visibility = not self.vboxChannelNavigator.get_property('visible')
            self.vboxChannelNavigator.set_property('visible', new_visibility)
            self.column_size.set_visible(not new_visibility)
            self.column_released.set_visible(not new_visibility)
        
        diff = 0
        if event.keyval == gtk.keysyms.F7: #plus
            diff = 1
        elif event.keyval == gtk.keysyms.F8: #minus
            diff = -1

        if diff != 0 and not self.currently_updating:
            selection = self.treeChannels.get_selection()
            (model, iter) = selection.get_selected()
            new_path = ((model.get_path(iter)[0]+diff)%len(model),)
            selection.select_path(new_path)
            self.treeChannels.set_cursor(new_path)
            return True

        return False
        
    def window_state_event(self, widget, event):
        if event.new_window_state & gtk.gdk.WINDOW_STATE_FULLSCREEN:
            self.fullscreen = True
        else:
            self.fullscreen = False
            
        old_minimized = self.minimized

        self.minimized = bool(event.new_window_state & gtk.gdk.WINDOW_STATE_ICONIFIED)
        if gpodder.interface == gpodder.MAEMO:
            self.minimized = bool(event.new_window_state & gtk.gdk.WINDOW_STATE_WITHDRAWN)

        if old_minimized != self.minimized and self.tray_icon:
            self.gPodder.set_skip_taskbar_hint(self.minimized)
        elif not self.tray_icon:
            self.gPodder.set_skip_taskbar_hint(False)

        if self.config.minimize_to_tray and self.tray_icon:
            self.tray_icon.set_visible(self.minimized)
    
    def uniconify_main_window(self):
        if self.minimized:
            self.gPodder.present()
 
    def iconify_main_window(self):
        if not self.minimized:
            self.gPodder.iconify()          

    def update_podcasts_tab(self):
        if len(self.channels):
            self.label2.set_text(_('Podcasts (%d)') % len(self.channels))
        else:
            self.label2.set_text(_('Podcasts'))

    @dbus.service.method(gpodder.dbus_interface)
    def show_gui_window(self):
        self.gPodder.present()


class gPodderOpmlLister(BuilderWidget):
    finger_friendly_widgets = ['btnDownloadOpml', 'btnCancel', 'btnOK', 'treeviewChannelChooser']
    (MODE_DOWNLOAD, MODE_SEARCH) = range(2)
    
    def new(self):
        # initiate channels list
        self.channels = []
        self.callback_for_channel = None
        self.callback_finished = None

        if hasattr(self, 'custom_title'):
            self.gPodderOpmlLister.set_title(self.custom_title)
        if hasattr(self, 'hide_url_entry'):
            self.hboxOpmlUrlEntry.hide_all()
            new_parent = self.notebookChannelAdder.get_parent()
            new_parent.remove(self.notebookChannelAdder)
            self.vboxOpmlImport.reparent(new_parent)

        self.setup_treeview(self.treeviewChannelChooser)
        self.setup_treeview(self.treeviewTopPodcastsChooser)
        self.setup_treeview(self.treeviewYouTubeChooser)

        self.current_mode = self.MODE_DOWNLOAD

        self.notebookChannelAdder.connect('switch-page', lambda a, b, c: self.on_change_tab(c))

    def setup_treeview(self, tv):
        togglecell = gtk.CellRendererToggle()
        togglecell.set_property( 'activatable', True)
        togglecell.connect( 'toggled', self.callback_edited)
        togglecolumn = gtk.TreeViewColumn( '', togglecell, active=OpmlListModel.C_SELECTED)
        
        titlecell = gtk.CellRendererText()
        titlecell.set_property('ellipsize', pango.ELLIPSIZE_END)
        titlecolumn = gtk.TreeViewColumn(_('Podcast'), titlecell, markup=OpmlListModel.C_DESCRIPTION_MARKUP)

        for itemcolumn in (togglecolumn, titlecolumn):
            tv.append_column(itemcolumn)

    def callback_edited( self, cell, path):
        model = self.get_treeview().get_model()

        url = model[path][OpmlListModel.C_URL]

        model[path][OpmlListModel.C_SELECTED] = not model[path][OpmlListModel.C_SELECTED]
        if model[path][OpmlListModel.C_SELECTED]:
            self.channels.append( url)
        else:
            self.channels.remove( url)

        self.btnOK.set_sensitive( bool(len(self.get_selected_channels())))

    def on_entryURL_changed(self, editable):
        old_mode = self.current_mode
        self.current_mode = not editable.get_text().lower().startswith('http://')
        if self.current_mode == old_mode:
            return

        if self.current_mode == self.MODE_SEARCH:
            self.btnDownloadOpml.set_property('image', None)
            self.btnDownloadOpml.set_label(gtk.STOCK_FIND)
            self.btnDownloadOpml.set_use_stock(True)
            self.labelOpmlUrl.set_text(_('Search podcast.de:'))
        else:
            self.btnDownloadOpml.set_label(_('Download'))
            self.btnDownloadOpml.set_image(gtk.image_new_from_stock(gtk.STOCK_GOTO_BOTTOM, gtk.ICON_SIZE_BUTTON))
            self.btnDownloadOpml.set_use_stock(False)
            self.labelOpmlUrl.set_text(_('OPML:'))

    def get_selected_channels(self, tab=None):
        channels = []

        model = self.get_treeview(tab).get_model()
        if model is not None:
            for row in model:
                if row[OpmlListModel.C_SELECTED]:
                    channels.append(row[OpmlListModel.C_URL])

        return channels

    def on_change_tab(self, tab):
        self.btnOK.set_sensitive( bool(len(self.get_selected_channels(tab))))

    def thread_finished(self, model, tab=0):
        if tab == 1:
            tv = self.treeviewTopPodcastsChooser
        elif tab == 2:
            tv = self.treeviewYouTubeChooser
            self.entryYoutubeSearch.set_sensitive(True)
            self.btnSearchYouTube.set_sensitive(True)
            self.btnOK.set_sensitive(False)
        else:
            tv = self.treeviewChannelChooser
            self.btnDownloadOpml.set_sensitive(True)
            self.entryURL.set_sensitive(True)
            self.channels = []

        tv.set_model(model)
        tv.set_sensitive(True)

    def thread_func(self, tab=0):
        if tab == 1:
            model = OpmlListModel(opml.Importer(self._config.toplist_url))
            if len(model) == 0:
                self.notification(_('The specified URL does not provide any valid OPML podcast items.'), _('No feeds found'))
        elif tab == 2:
            model = OpmlListModel(youtube.find_youtube_channels(self.entryYoutubeSearch.get_text()))
            if len(model) == 0:
                self.notification(_('There are no YouTube channels that would match this query.'), _('No channels found'))
        else:
            url = self.entryURL.get_text()
            if not os.path.isfile(url) and not url.lower().startswith('http://'):
                log('Using podcast.de search')
                url = 'http://api.podcast.de/opml/podcasts/suche/%s' % (urllib.quote(url),)
            model = OpmlListModel(opml.Importer(url))
            if len(model) == 0:
                self.notification(_('The specified URL does not provide any valid OPML podcast items.'), _('No feeds found'))

        util.idle_add(self.thread_finished, model, tab)
    
    def get_channels_from_url( self, url, callback_for_channel = None, callback_finished = None):
        if callback_for_channel:
            self.callback_for_channel = callback_for_channel
        if callback_finished:
            self.callback_finished = callback_finished
        self.entryURL.set_text( url)
        self.btnDownloadOpml.set_sensitive( False)
        self.entryURL.set_sensitive( False)
        self.btnOK.set_sensitive( False)
        self.treeviewChannelChooser.set_sensitive( False)
        Thread( target = self.thread_func).start()
        Thread( target = lambda: self.thread_func(1)).start()

    def select_all( self, value ):
        enabled = False
        model = self.get_treeview().get_model()
        if model is not None:
            for row in model:
                row[OpmlListModel.C_SELECTED] = value
                if value:
                    enabled = True
        self.btnOK.set_sensitive(enabled)

    def on_gPodderOpmlLister_destroy(self, widget, *args):
        pass

    def on_btnDownloadOpml_clicked(self, widget, *args):
        self.get_channels_from_url( self.entryURL.get_text())

    def on_btnSearchYouTube_clicked(self, widget, *args):
        self.entryYoutubeSearch.set_sensitive(False)
        self.treeviewYouTubeChooser.set_sensitive(False)
        self.btnSearchYouTube.set_sensitive(False)
        Thread(target = lambda: self.thread_func(2)).start()

    def on_btnSelectAll_clicked(self, widget, *args):
        self.select_all(True)
    
    def on_btnSelectNone_clicked(self, widget, *args):
        self.select_all(False)

    def on_btnOK_clicked(self, widget, *args):
        self.channels = self.get_selected_channels()
        self.gPodderOpmlLister.destroy()

        # add channels that have been selected
        for url in self.channels:
            if self.callback_for_channel:
                self.callback_for_channel( url)

        if self.callback_finished:
            util.idle_add(self.callback_finished)

    def on_btnCancel_clicked(self, widget, *args):
        self.gPodderOpmlLister.destroy()

    def on_entryYoutubeSearch_key_press_event(self, widget, event):
        if event.keyval == gtk.keysyms.Return:
            self.on_btnSearchYouTube_clicked(widget)

    def get_treeview(self, tab=None):
        if tab is None:
            tab = self.notebookChannelAdder.get_current_page()

        if tab == 0:
            return self.treeviewChannelChooser
        elif tab == 1:
            return self.treeviewTopPodcastsChooser
        else:
            return self.treeviewYouTubeChooser

class gPodderEpisodeSelector(BuilderWidget):
    """Episode selection dialog

    Optional keyword arguments that modify the behaviour of this dialog:

      - callback: Function that takes 1 parameter which is a list of
                  the selected episodes (or empty list when none selected)
      - remove_callback: Function that takes 1 parameter which is a list
                         of episodes that should be "removed" (see below)
                         (default is None, which means remove not possible)
      - remove_action: Label for the "remove" action (default is "Remove")
      - remove_finished: Callback after all remove callbacks have finished
                         (default is None, also depends on remove_callback)
                         It will get a list of episode URLs that have been
                         removed, so the main UI can update those
      - episodes: List of episodes that are presented for selection
      - selected: (optional) List of boolean variables that define the
                  default checked state for the given episodes
      - selected_default: (optional) The default boolean value for the
                          checked state if no other value is set
                          (default is False)
      - columns: List of (name, sort_name, sort_type, caption) pairs for the
                 columns, the name is the attribute name of the episode to be 
                 read from each episode object.  The sort name is the 
                 attribute name of the episode to be used to sort this column.
                 If the sort_name is None it will use the attribute name for
                 sorting.  The sort type is the type of the sort column.
                 The caption attribute is the text that appear as column caption
                 (default is [('title_markup', None, None, 'Episode'),])
      - title: (optional) The title of the window + heading
      - instructions: (optional) A one-line text describing what the 
                      user should select / what the selection is for
      - stock_ok_button: (optional) Will replace the "OK" button with
                         another GTK+ stock item to be used for the
                         affirmative button of the dialog (e.g. can 
                         be gtk.STOCK_DELETE when the episodes to be
                         selected will be deleted after closing the 
                         dialog)
      - selection_buttons: (optional) A dictionary with labels as 
                           keys and callbacks as values; for each
                           key a button will be generated, and when
                           the button is clicked, the callback will
                           be called for each episode and the return
                           value of the callback (True or False) will
                           be the new selected state of the episode
      - size_attribute: (optional) The name of an attribute of the 
                        supplied episode objects that can be used to
                        calculate the size of an episode; set this to
                        None if no total size calculation should be
                        done (in cases where total size is useless)
                        (default is 'length')
      - tooltip_attribute: (optional) The name of an attribute of
                           the supplied episode objects that holds
                           the text for the tooltips when hovering
                           over an episode (default is 'description')
                           
    """
    finger_friendly_widgets = ['btnCancel', 'btnOK', 'btnCheckAll', 'btnCheckNone', 'treeviewEpisodes']
    
    COLUMN_INDEX = 0
    COLUMN_TOOLTIP = 1
    COLUMN_TOGGLE = 2
    COLUMN_ADDITIONAL = 3

    def new( self):
        self._config.connect_gtk_window(self.gPodderEpisodeSelector, 'episode_selector', True)
        if not hasattr( self, 'callback'):
            self.callback = None

        if not hasattr(self, 'remove_callback'):
            self.remove_callback = None

        if not hasattr(self, 'remove_action'):
            self.remove_action = _('Remove')

        if not hasattr(self, 'remove_finished'):
            self.remove_finished = None

        if not hasattr( self, 'episodes'):
            self.episodes = []

        if not hasattr( self, 'size_attribute'):
            self.size_attribute = 'length'

        if not hasattr(self, 'tooltip_attribute'):
            self.tooltip_attribute = 'description'

        if not hasattr( self, 'selection_buttons'):
            self.selection_buttons = {}

        if not hasattr( self, 'selected_default'):
            self.selected_default = False

        if not hasattr( self, 'selected'):
            self.selected = [self.selected_default]*len(self.episodes)

        if len(self.selected) < len(self.episodes):
            self.selected += [self.selected_default]*(len(self.episodes)-len(self.selected))

        if not hasattr( self, 'columns'):
            self.columns = (('title_markup', None, None, _('Episode')),)

        if hasattr( self, 'title'):
            self.gPodderEpisodeSelector.set_title( self.title)
            self.labelHeading.set_markup( '<b><big>%s</big></b>' % saxutils.escape( self.title))

        if gpodder.interface == gpodder.MAEMO:
            self.labelHeading.hide()

        if hasattr( self, 'instructions'):
            self.labelInstructions.set_text( self.instructions)
            self.labelInstructions.show_all()

        if hasattr(self, 'stock_ok_button'):
            if self.stock_ok_button == 'gpodder-download':
                self.btnOK.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_DOWN, gtk.ICON_SIZE_BUTTON))
                self.btnOK.set_label(_('Download'))
            else:
                self.btnOK.set_label(self.stock_ok_button)
                self.btnOK.set_use_stock(True)

        # check/uncheck column
        toggle_cell = gtk.CellRendererToggle()
        toggle_cell.connect( 'toggled', self.toggle_cell_handler)
        self.treeviewEpisodes.append_column( gtk.TreeViewColumn( '', toggle_cell, active=self.COLUMN_TOGGLE))
        
        next_column = self.COLUMN_ADDITIONAL
        for name, sort_name, sort_type, caption in self.columns:
            renderer = gtk.CellRendererText()
            if next_column < self.COLUMN_ADDITIONAL + 2:
                renderer.set_property('ellipsize', pango.ELLIPSIZE_END)
            column = gtk.TreeViewColumn(caption, renderer, markup=next_column)
            column.set_resizable( True)
            # Only set "expand" on the first two columns
            if next_column < self.COLUMN_ADDITIONAL + 2:
                column.set_expand(True)
            if sort_name is not None:
                column.set_sort_column_id(next_column+1)
            else:
                column.set_sort_column_id(next_column)
            self.treeviewEpisodes.append_column( column)
            next_column += 1
            
            if sort_name is not None:
                # add the sort column
                column = gtk.TreeViewColumn()
                column.set_visible(False)
                self.treeviewEpisodes.append_column( column)
                next_column += 1

        column_types = [ gobject.TYPE_INT, gobject.TYPE_STRING, gobject.TYPE_BOOLEAN ]
        # add string column type plus sort column type if it exists
        for name, sort_name, sort_type, caption in self.columns:
            column_types.append(gobject.TYPE_STRING)
            if sort_name is not None:
                column_types.append(sort_type)
        self.model = gtk.ListStore( *column_types)

        tooltip = None
        for index, episode in enumerate( self.episodes):
            if self.tooltip_attribute is not None:
                try:
                    tooltip = getattr(episode, self.tooltip_attribute)
                except:
                    log('Episode object %s does not have tooltip attribute: "%s"', episode, self.tooltip_attribute, sender=self)
                    tooltip = None
            row = [ index, tooltip, self.selected[index] ]
            for name, sort_name, sort_type, caption in self.columns:
                if not hasattr(episode, name):
                    log('Warning: Missing attribute "%s"', name, sender=self)
                    row.append(None)
                else:
                    row.append(getattr( episode, name))
                    
                if sort_name is not None:
                    if not hasattr(episode, sort_name):
                        log('Warning: Missing attribute "%s"', sort_name, sender=self)
                        row.append(None)
                    else:
                        row.append(getattr( episode, sort_name))
            self.model.append( row)

        if self.remove_callback is not None:
            self.btnRemoveAction.show()
            self.btnRemoveAction.set_label(self.remove_action)

        # connect to tooltip signals
        if self.tooltip_attribute is not None:
            try:
                self.treeviewEpisodes.set_property('has-tooltip', True)
                self.treeviewEpisodes.connect('query-tooltip', self.treeview_episodes_query_tooltip)
            except:
                log('I cannot set has-tooltip/query-tooltip (need at least PyGTK 2.12)', sender=self)
        self.last_tooltip_episode = None
        self.episode_list_can_tooltip = True

        self.treeviewEpisodes.connect('button-press-event', self.treeview_episodes_button_pressed)
        self.treeviewEpisodes.set_rules_hint( True)
        self.treeviewEpisodes.set_model( self.model)
        self.treeviewEpisodes.columns_autosize()
        self.calculate_total_size()

    def treeview_episodes_query_tooltip(self, treeview, x, y, keyboard_tooltip, tooltip):
        # With get_bin_window, we get the window that contains the rows without
        # the header. The Y coordinate of this window will be the height of the
        # treeview header. This is the amount we have to subtract from the
        # event's Y coordinate to get the coordinate to pass to get_path_at_pos
        (x_bin, y_bin) = treeview.get_bin_window().get_position()
        y -= x_bin
        y -= y_bin
        (path, column, rx, ry) = treeview.get_path_at_pos(x, y) or (None,)*4

        if not self.episode_list_can_tooltip:
            self.last_tooltip_episode = None
            return False

        if path is not None:
            model = treeview.get_model()
            iter = model.get_iter(path)
            index = model.get_value(iter, self.COLUMN_INDEX)
            description = model.get_value(iter, self.COLUMN_TOOLTIP)
            if self.last_tooltip_episode is not None and self.last_tooltip_episode != index:
                self.last_tooltip_episode = None
                return False
            self.last_tooltip_episode = index

            if description is not None:
                tooltip.set_text(description)
                return True
            else:
                return False

        self.last_tooltip_episode = None
        return False

    def treeview_episodes_button_pressed(self, treeview, event):
        if event.button == 3:
            menu = gtk.Menu()

            if len(self.selection_buttons):
                for label in self.selection_buttons:
                    item = gtk.MenuItem(label)
                    item.connect('activate', self.custom_selection_button_clicked, label)
                    menu.append(item)
                menu.append(gtk.SeparatorMenuItem())

            item = gtk.MenuItem(_('Select all'))
            item.connect('activate', self.on_btnCheckAll_clicked)
            menu.append(item)

            item = gtk.MenuItem(_('Select none'))
            item.connect('activate', self.on_btnCheckNone_clicked)
            menu.append(item)

            menu.show_all()
            # Disable tooltips while we are showing the menu, so 
            # the tooltip will not appear over the menu
            self.episode_list_can_tooltip = False
            menu.connect('deactivate', lambda menushell: self.episode_list_allow_tooltips())
            menu.popup(None, None, None, event.button, event.time)

            return True

    def episode_list_allow_tooltips(self):
        self.episode_list_can_tooltip = True

    def calculate_total_size( self):
        if self.size_attribute is not None:
            (total_size, count) = (0, 0)
            for episode in self.get_selected_episodes():
                try:
                    total_size += int(getattr( episode, self.size_attribute))
                    count += 1
                except:
                    log( 'Cannot get size for %s', episode.title, sender = self)

            text = []
            if count == 0: 
                text.append(_('Nothing selected'))
            elif count == 1:
                text.append(_('One episode selected'))
            else:
                text.append(_('%d episodes selected') % count)
            if total_size > 0: 
                text.append(_('total size: %s') % util.format_filesize(total_size))
            self.labelTotalSize.set_text(', '.join(text))
            self.btnOK.set_sensitive(count>0)
            self.btnRemoveAction.set_sensitive(count>0)
            if count > 0:
                self.btnCancel.set_label(gtk.STOCK_CANCEL)
            else:
                self.btnCancel.set_label(gtk.STOCK_CLOSE)
        else:
            self.btnOK.set_sensitive(False)
            self.btnRemoveAction.set_sensitive(False)
            for index, row in enumerate(self.model):
                if self.model.get_value(row.iter, self.COLUMN_TOGGLE) == True:
                    self.btnOK.set_sensitive(True)
                    self.btnRemoveAction.set_sensitive(True)
                    break
            self.labelTotalSize.set_text('')

    def toggle_cell_handler( self, cell, path):
        model = self.treeviewEpisodes.get_model()
        model[path][self.COLUMN_TOGGLE] = not model[path][self.COLUMN_TOGGLE]

        self.calculate_total_size()

    def custom_selection_button_clicked(self, button, label):
        callback = self.selection_buttons[label]

        for index, row in enumerate( self.model):
            new_value = callback( self.episodes[index])
            self.model.set_value( row.iter, self.COLUMN_TOGGLE, new_value)

        self.calculate_total_size()

    def on_btnCheckAll_clicked( self, widget):
        for row in self.model:
            self.model.set_value( row.iter, self.COLUMN_TOGGLE, True)

        self.calculate_total_size()

    def on_btnCheckNone_clicked( self, widget):
        for row in self.model:
            self.model.set_value( row.iter, self.COLUMN_TOGGLE, False)

        self.calculate_total_size()

    def on_remove_action_activate(self, widget):
        episodes = self.get_selected_episodes(remove_episodes=True)

        urls = []
        for episode in episodes:
            urls.append(episode.url)
            self.remove_callback(episode)

        if self.remove_finished is not None:
            self.remove_finished(urls)
        self.calculate_total_size()

    def get_selected_episodes( self, remove_episodes=False):
        selected_episodes = []

        for index, row in enumerate( self.model):
            if self.model.get_value( row.iter, self.COLUMN_TOGGLE) == True:
                selected_episodes.append( self.episodes[self.model.get_value( row.iter, self.COLUMN_INDEX)])

        if remove_episodes:
            for episode in selected_episodes:
                index = self.episodes.index(episode)
                iter = self.model.get_iter_first()
                while iter is not None:
                    if self.model.get_value(iter, self.COLUMN_INDEX) == index:
                        self.model.remove(iter)
                        break
                    iter = self.model.iter_next(iter)

        return selected_episodes

    def on_btnOK_clicked( self, widget):
        self.gPodderEpisodeSelector.destroy()
        if self.callback is not None:
            self.callback( self.get_selected_episodes())

    def on_btnCancel_clicked( self, widget):
        self.gPodderEpisodeSelector.destroy()
        if self.callback is not None:
            self.callback([])

class gPodderPlaylist(BuilderWidget):
    finger_friendly_widgets = ['btnCancelPlaylist', 'btnSavePlaylist', 'treeviewPlaylist']

    def new(self):
        self.linebreak = '\n'
        if self._config.mp3_player_playlist_win_path:
            self.linebreak = '\r\n'
        self.mountpoint = util.find_mount_point(self._config.mp3_player_folder)
        if self.mountpoint == '/':
            self.mountpoint = self._config.mp3_player_folder
            log('Warning: MP3 player resides on / - using %s as MP3 player root', self.mountpoint, sender=self)
        self.playlist_file = os.path.join(self.mountpoint,
                                          self._config.mp3_player_playlist_file)
        icon_theme = gtk.icon_theme_get_default()
        self.icon_new = icon_theme.load_icon(gtk.STOCK_NEW, 16, 0)

        # add column two
        check_cell = gtk.CellRendererToggle()
        check_cell.set_property('activatable', True)
        check_cell.connect('toggled', self.cell_toggled)
        check_column = gtk.TreeViewColumn(_('Use'), check_cell, active=1)
        self.treeviewPlaylist.append_column(check_column)

        # add column three
        column = gtk.TreeViewColumn(_('Filename'))
        icon_cell = gtk.CellRendererPixbuf()
        column.pack_start(icon_cell, False)
        column.add_attribute(icon_cell, 'pixbuf', 0)
        filename_cell = gtk.CellRendererText()
        column.pack_start(filename_cell, True)
        column.add_attribute(filename_cell, 'text', 2)

        column.set_resizable(True)
        self.treeviewPlaylist.append_column(column)

        # Make treeview reorderable
        self.treeviewPlaylist.set_reorderable(True)

        # init liststore
        self.playlist = gtk.ListStore(gtk.gdk.Pixbuf, bool, str)
        self.treeviewPlaylist.set_model(self.playlist)

        # read device and playlist and fill the TreeView
        title = _('Reading files from %s') % self._config.mp3_player_folder
        message = _('Please wait your media file list is being read from device.')
        dlg = gtk.MessageDialog(self.main_window, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_NONE)
        dlg.set_title(title)
        dlg.set_markup('<span weight="bold" size="larger">%s</span>\n\n%s'%(title, message))
        dlg.show_all()
        Thread(target=self.process_device, args=[dlg]).start()

    def process_device(self, dlg):
        self.m3u = self.read_m3u()
        self.device = self.read_device()
        util.idle_add(self.write2gui, dlg)

    def cell_toggled(self, cellrenderertoggle, path):
        (treeview, liststore) = (self.treeviewPlaylist, self.playlist)
        it = liststore.get_iter(path)
        liststore.set_value(it, 1, not liststore.get_value(it, 1))

    def on_btnCancelPlaylist_clicked(self, widget):
        self.gPodderPlaylist.destroy()

    def on_btnSavePlaylist_clicked(self, widget):
        self.write_m3u()
        self.gPodderPlaylist.destroy()

    def read_m3u(self):
        """
        read all files from the existing playlist
        """
        tracks = []
        log("Read data from the playlistfile %s" % self.playlist_file)
        if os.path.exists(self.playlist_file):
            for line in open(self.playlist_file, 'r'):
                if not line.startswith('#EXT'):
                    if line.startswith('#'):
                        tracks.append([False, line[1:].strip()])
                    else:
                        tracks.append([True, line.strip()])
        return tracks

    def build_extinf(self, filename):
        if self._config.mp3_player_playlist_win_path:
            filename = filename.replace('\\', os.sep)

        # rebuild the whole filename including the mountpoint
        if self._config.mp3_player_playlist_absolute_path:
            absfile = self.mountpoint + filename
        else:
            absfile = util.rel2abs(filename, os.path.dirname(self.playlist_file))

        # fallback: use the basename of the file
        (title, extension) = os.path.splitext(os.path.basename(filename))

        return "#EXTINF:0,%s%s" % (title.strip(), self.linebreak)

    def write_m3u(self):
        """
        write the list into the playlist on the device
        """
        log('Writing playlist file: %s', self.playlist_file, sender=self)
        playlist_folder = os.path.split(self.playlist_file)[0]
        if not util.make_directory(playlist_folder):
            self.show_message(_('Folder %s could not be created.') % playlist_folder, _('Error writing playlist'))
        else:
            try:
                fp = open(self.playlist_file, 'w')
                fp.write('#EXTM3U%s' % self.linebreak)
                for icon, checked, filename in self.playlist:
                    fp.write(self.build_extinf(filename))
                    if not checked:
                        fp.write('#')
                    fp.write(filename)
                    fp.write(self.linebreak)
                fp.close()
                self.show_message(_('The playlist on your MP3 player has been updated.'), _('Update successful'))
            except IOError, ioe:
                self.show_message(str(ioe), _('Error writing playlist file'))

    def read_device(self):
        """
        read all files from the device
        """
        log('Reading files from %s', self._config.mp3_player_folder, sender=self)
        tracks = []
        for root, dirs, files in os.walk(self._config.mp3_player_folder):
            for file in files:
                filename = os.path.join(root, file)

                if filename == self.playlist_file or fnmatch.fnmatch(filename, '*.dat') or fnmatch.fnmatch(filename, '*.DAT'):
                    # We don't want to have our playlist file as
                    # an entry in our file list, so skip it!
                    # We also don't want to include dat files
                    continue

                if self._config.mp3_player_playlist_absolute_path:
                    filename = filename[len(self.mountpoint):]
                else:
                    filename = util.relpath(os.path.dirname(self.playlist_file),
                                            os.path.dirname(filename)) + \
                               os.sep + os.path.basename(filename)

                if self._config.mp3_player_playlist_win_path:
                    filename = filename.replace(os.sep, '\\')

                tracks.append(filename)
        return tracks

    def write2gui(self, dlg):
        # add the files from the device to the list only when
        # they are not yet in the playlist
        # mark this files as NEW
        for filename in self.device[:]:
            m3ulist = [file[1] for file in self.m3u]
            if filename not in m3ulist:
                self.playlist.append([self.icon_new, False, filename])

        # add the files from the playlist to the list only when
        # they are on the device
        for checked, filename in self.m3u[:]:
            if filename in self.device:
                self.playlist.append([None, checked, filename])

        dlg.destroy()
        return False

class gPodderDependencyManager(BuilderWidget):
    def new(self):
        col_name = gtk.TreeViewColumn(_('Feature'), gtk.CellRendererText(), text=0)
        self.treeview_components.append_column(col_name)
        col_installed = gtk.TreeViewColumn(_('Status'), gtk.CellRendererText(), text=2)
        self.treeview_components.append_column(col_installed)
        self.treeview_components.set_model(DependencyModel(services.dependency_manager))
        self.btn_about.set_sensitive(False)
        self.btn_install.set_sensitive(False)

    def on_btn_about_clicked(self, widget):
        selection = self.treeview_components.get_selection()
        model, iter = selection.get_selected()
        if iter is not None:
            title = model.get_value(iter, 0)
            description = model.get_value(iter, 1)
            available = model.get_value(iter, 3)
            missing = model.get_value(iter, 4)

            if not available:
                description += '\n\n'+_('Missing components:')+'\n\n'+missing

            self.show_message(description, title)

    def on_btn_install_clicked(self, widget):
        # TODO: Implement package manager integration
        pass

    def on_treeview_components_cursor_changed(self, treeview):
        self.btn_about.set_sensitive(treeview.get_selection().count_selected_rows() > 0)
        # TODO: If installing is possible, enable btn_install

    def on_gPodderDependencyManager_response(self, dialog, response_id):
        self.gPodderDependencyManager.destroy()

class gPodderWelcome(BuilderWidget):
    finger_friendly_widgets = ['btnOPML', 'btnMygPodder', 'btnCancel']

    def new(self):
        for widget in (self.btnOPML, self.btnMygPodder):
            for child in widget.get_children():
                if isinstance(child, gtk.Alignment):
                    child.set_padding(20, 20, 20, 20)
                else:
                    child.set_padding(20, 20)
        self.gPodderWelcome.show()

    def on_show_example_podcasts(self, button):
        self.gPodderWelcome.destroy()
        self.show_example_podcasts_callback(None)

    def on_setup_my_gpodder(self, gpodder):
        self.gPodderWelcome.destroy()
        self.setup_my_gpodder_callback(None)

    def on_btnCancel_clicked(self, button):
        self.gPodderWelcome.destroy()

def main():
    gobject.threads_init()
    gtk.window_set_default_icon_name( 'gpodder')

    try:
        session_bus = dbus.SessionBus(mainloop=dbus.glib.DBusGMainLoop())
        bus_name = dbus.service.BusName(gpodder.dbus_bus_name, bus=session_bus)
    except dbus.exceptions.DBusException, dbe:
        log('Warning: Cannot get "on the bus".', traceback=True)
        dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, \
                gtk.BUTTONS_CLOSE, _('Cannot start gPodder'))
        dlg.format_secondary_markup(_('D-Bus error: %s') % (str(dbe),))
        dlg.set_title('gPodder')
        dlg.run()
        dlg.destroy()
        sys.exit(0)

    util.make_directory(gpodder.home)
    config = UIConfig(gpodder.config_file)

    if gpodder.interface == gpodder.MAEMO:
        # Detect changing of SD cards between mmc1/mmc2 if a gpodder
        # folder exists there (allow moving "gpodder" between SD cards or USB)
        # Also allow moving "gpodder" to home folder (e.g. rootfs on SD)
        if not os.path.exists(config.download_dir):
            log('Downloads might have been moved. Trying to locate them...')
            for basedir in ['/media/mmc1', '/media/mmc2']+glob.glob('/media/usb/*')+['/home/user']:
                dir = os.path.join(basedir, 'gpodder')
                if os.path.exists(dir):
                    log('Downloads found in: %s', dir)
                    config.download_dir = dir
                    break
                else:
                    log('Downloads NOT FOUND in %s', dir)

        if not config.disable_fingerscroll:
            GtkBuilderWidget.use_fingerscroll = True

    gp = gPodder(bus_name, config)
    gp.run()



