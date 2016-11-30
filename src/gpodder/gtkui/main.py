# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2016 Thomas Perl and the gPodder Team
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
import platform
import gtk
import gtk.gdk
import gobject
import pango
import random
import sys
import shutil
import subprocess
import glob
import time
import threading
import tempfile
import collections
import urllib
import cgi


import gpodder

import dbus
import dbus.service
import dbus.mainloop
import dbus.glib

from gpodder import core
from gpodder import feedcore
from gpodder import util
from gpodder import opml
from gpodder import download
from gpodder import my
from gpodder import youtube
from gpodder import player
from gpodder import common

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext
N_ = gpodder.ngettext

from gpodder.gtkui.model import Model
from gpodder.gtkui.model import PodcastListModel
from gpodder.gtkui.model import EpisodeListModel
from gpodder.gtkui.config import UIConfig
from gpodder.gtkui.services import CoverDownloader
from gpodder.gtkui.widgets import SimpleMessageArea
from gpodder.gtkui.desktopfile import UserAppsReader

from gpodder.gtkui.draw import draw_text_box_centered, draw_cake_pixbuf
from gpodder.gtkui.draw import EPISODE_LIST_ICON_SIZE

from gpodder.gtkui.interface.common import BuilderWidget
from gpodder.gtkui.interface.common import TreeViewHelper
from gpodder.gtkui.interface.addpodcast import gPodderAddPodcast

from gpodder.gtkui.download import DownloadStatusModel

from gpodder.gtkui.desktop.welcome import gPodderWelcome
from gpodder.gtkui.desktop.channel import gPodderChannel
from gpodder.gtkui.desktop.preferences import gPodderPreferences
from gpodder.gtkui.desktop.episodeselector import gPodderEpisodeSelector
from gpodder.gtkui.desktop.podcastdirectory import gPodderPodcastDirectory
from gpodder.gtkui.interface.progress import ProgressIndicator

from gpodder.gtkui.desktop.sync import gPodderSyncUI
from gpodder.gtkui import shownotes

from gpodder.dbusproxy import DBusPodcastsProxy
from gpodder import extensions


macapp = None
if gpodder.ui.osx and getattr(gtk.gdk, 'WINDOWING', 'x11') == 'quartz':
    try:
        from gtkosx_application import *
        macapp = Application()
    except ImportError:
        print >> sys.stderr, """
        Warning: gtk-mac-integration not found, disabling native menus
        """


class gPodder(BuilderWidget, dbus.service.Object):
    # Width (in pixels) of episode list icon
    EPISODE_LIST_ICON_WIDTH = 40

    def __init__(self, bus_name, gpodder_core, options):
        dbus.service.Object.__init__(self, object_path=gpodder.dbus_gui_object_path, bus_name=bus_name)
        self.podcasts_proxy = DBusPodcastsProxy(lambda: self.channels,
                self.on_itemUpdate_activate,
                self.playback_episodes,
                self.download_episode_list,
                self.episode_object_by_uri,
                bus_name)
        self.core = gpodder_core
        self.config = self.core.config
        self.db = self.core.db
        self.model = self.core.model
        self.options = options
        BuilderWidget.__init__(self, None)

    def new(self):
        gpodder.user_extensions.on_ui_object_available('gpodder-gtk', self)
        self.toolbar.set_property('visible', self.config.show_toolbar)

        self.bluetooth_available = util.bluetooth_available()

        self.config.connect_gtk_window(self.main_window, 'main_window')

        self.config.connect_gtk_paned('ui.gtk.state.main_window.paned_position', self.channelPaned)

        self.main_window.show()

        self.player_receiver = player.MediaPlayerDBusReceiver(self.on_played)

        self.gPodder.connect('key-press-event', self.on_key_press)

        self.episode_columns_menu = None
        self.config.add_observer(self.on_config_changed)

        self.shownotes_pane = gtk.HBox()
        self.shownotes_object = shownotes.gPodderShownotesText(self.shownotes_pane)

        # Vertical paned for the episode list and shownotes
        self.vpaned = gtk.VPaned()
        paned = self.vbox_episode_list.get_parent()
        self.vbox_episode_list.reparent(self.vpaned)
        self.vpaned.child_set_property(self.vbox_episode_list, 'resize', True)
        self.vpaned.child_set_property(self.vbox_episode_list, 'shrink', False)
        self.vpaned.pack2(self.shownotes_pane, resize=False, shrink=False)
        self.vpaned.show()

        # Minimum height for both episode list and shownotes
        self.vbox_episode_list.set_size_request(-1, 100)
        self.shownotes_pane.set_size_request(-1, 100)

        self.config.connect_gtk_paned('ui.gtk.state.main_window.episode_list_size',
                self.vpaned)
        paned.add2(self.vpaned)


        self.new_episodes_window = None

        # Mac OS X-specific UI tweaks: Native main menu integration
        # http://sourceforge.net/apps/trac/gtk-osx/wiki/Integrate
        if macapp is not None:
            # Move the menu bar from the window to the Mac menu bar
            self.mainMenu.hide()
            macapp.set_menu_bar(self.mainMenu)

            # Reparent some items to the "Application" menu
            item = self.uimanager1.get_widget('/mainMenu/menuHelp/itemAbout')
            macapp.insert_app_menu_item(item, 0)
            macapp.insert_app_menu_item(gtk.SeparatorMenuItem(), 1)
            item = self.uimanager1.get_widget('/mainMenu/menuPodcasts/itemPreferences')
            macapp.insert_app_menu_item(item, 2)

            quit_item = self.uimanager1.get_widget('/mainMenu/menuPodcasts/itemQuit')
            quit_item.hide()
        # end Mac OS X specific UI tweaks

        self.download_status_model = DownloadStatusModel()
        self.download_queue_manager = download.DownloadQueueManager(self.config)

        self.itemShowToolbar.set_active(self.config.show_toolbar)
        self.itemShowDescription.set_active(self.config.episode_list_descriptions)

        self.config.connect_gtk_spinbutton('max_downloads', self.spinMaxDownloads)
        self.config.connect_gtk_togglebutton('max_downloads_enabled', self.cbMaxDownloads)
        self.config.connect_gtk_spinbutton('limit_rate_value', self.spinLimitDownloads)
        self.config.connect_gtk_togglebutton('limit_rate', self.cbLimitDownloads)

        # When the amount of maximum downloads changes, notify the queue manager
        changed_cb = lambda spinbutton: self.download_queue_manager.spawn_threads()
        self.spinMaxDownloads.connect('value-changed', changed_cb)

        # Keep a reference to the last add podcast dialog instance
        self._add_podcast_dialog = None

        self.default_title = None
        self.set_title(_('gPodder'))

        self.cover_downloader = CoverDownloader()

        # Generate list models for podcasts and their episodes
        self.podcast_list_model = PodcastListModel(self.cover_downloader)

        self.cover_downloader.register('cover-available', self.cover_download_finished)

        # Source IDs for timeouts for search-as-you-type
        self._podcast_list_search_timeout = None
        self._episode_list_search_timeout = None

        # Init the treeviews that we use
        self.init_podcast_list_treeview()
        self.init_episode_list_treeview()
        self.init_download_list_treeview()

        if self.config.podcast_list_hide_boring:
            self.item_view_hide_boring_podcasts.set_active(True)

        self.download_tasks_seen = set()
        self.download_list_update_enabled = False
        self.download_task_monitors = set()

        # Subscribed channels
        self.active_channel = None
        self.channels = self.model.get_podcasts()

        # Set up the first instance of MygPoClient
        self.mygpo_client = my.MygPoClient(self.config)

        gpodder.user_extensions.on_ui_initialized(self.model,
                self.extensions_podcast_update_cb,
                self.extensions_episode_download_cb)

        # load list of user applications for audio playback
        self.user_apps_reader = UserAppsReader(['audio', 'video'])
        util.run_in_background(self.user_apps_reader.read)

        # Now, update the feed cache, when everything's in place
        self.btnUpdateFeeds.show()
        self.feed_cache_update_cancelled = False
        self.update_podcast_list_model()

        self.message_area = None

        self.partial_downloads_indicator = None
        util.run_in_background(self.find_partial_downloads)

        # Start the auto-update procedure
        self._auto_update_timer_source_id = None
        if self.config.auto_update_feeds:
            self.restart_auto_update_timer()

        # Find expired (old) episodes and delete them
        old_episodes = list(common.get_expired_episodes(self.channels, self.config))
        if len(old_episodes) > 0:
            self.delete_episode_list(old_episodes, confirm=False)
            updated_urls = set(e.channel.url for e in old_episodes)
            self.update_podcast_list_model(updated_urls)

        # Do the initial sync with the web service
        if self.mygpo_client.can_access_webservice():
            util.idle_add(self.mygpo_client.flush, True)

        # First-time users should be asked if they want to see the OPML
        if self.options.subscribe:
            util.idle_add(self.subscribe_to_url, self.options.subscribe)
        elif not self.channels:
            self.on_itemUpdate_activate()
        elif self.config.software_update.check_on_startup:
            # Check for software updates from gpodder.org
            diff = time.time() - self.config.software_update.last_check
            if diff > (60*60*24)*self.config.software_update.interval:
                self.config.software_update.last_check = int(time.time())
                self.check_for_updates(silent=True)

    def find_partial_downloads(self):
        def start_progress_callback(count):
            self.partial_downloads_indicator = ProgressIndicator(
                    _('Loading incomplete downloads'),
                    _('Some episodes have not finished downloading in a previous session.'),
                    False, self.get_dialog_parent())
            self.partial_downloads_indicator.on_message(N_('%(count)d partial file', '%(count)d partial files', count) % {'count':count})

            util.idle_add(self.wNotebook.set_current_page, 1)

        def progress_callback(title, progress):
            self.partial_downloads_indicator.on_message(title)
            self.partial_downloads_indicator.on_progress(progress)

        def finish_progress_callback(resumable_episodes):
            util.idle_add(self.partial_downloads_indicator.on_finished)
            self.partial_downloads_indicator = None

            if resumable_episodes:
                def offer_resuming():
                    self.download_episode_list_paused(resumable_episodes)
                    resume_all = gtk.Button(_('Resume all'))
                    def on_resume_all(button):
                        selection = self.treeDownloads.get_selection()
                        selection.select_all()
                        selected_tasks, _, _, _, _, _ = self.downloads_list_get_selection()
                        selection.unselect_all()
                        self._for_each_task_set_status(selected_tasks, download.DownloadTask.QUEUED)
                        self.message_area.hide()
                    resume_all.connect('clicked', on_resume_all)

                    self.message_area = SimpleMessageArea(_('Incomplete downloads from a previous session were found.'), (resume_all,))
                    self.vboxDownloadStatusWidgets.pack_start(self.message_area, expand=False)
                    self.vboxDownloadStatusWidgets.reorder_child(self.message_area, 0)
                    self.message_area.show_all()
                    common.clean_up_downloads(delete_partial=False)
                util.idle_add(offer_resuming)
            else:
                util.idle_add(self.wNotebook.set_current_page, 0)

        common.find_partial_downloads(self.channels,
                start_progress_callback,
                progress_callback,
                finish_progress_callback)

    def episode_object_by_uri(self, uri):
        """Get an episode object given a local or remote URI

        This can be used to quickly access an episode object
        when all we have is its download filename or episode
        URL (e.g. from external D-Bus calls / signals, etc..)
        """
        if uri.startswith('/'):
            uri = 'file://' + urllib.quote(uri)

        prefix = 'file://' + urllib.quote(gpodder.downloads)

        # By default, assume we can't pre-select any channel
        # but can match episodes simply via the download URL
        is_channel = lambda c: True
        is_episode = lambda e: e.url == uri

        if uri.startswith(prefix):
            # File is on the local filesystem in the download folder
            # Try to reduce search space by pre-selecting the channel
            # based on the folder name of the local file

            filename = urllib.unquote(uri[len(prefix):])
            file_parts = filter(None, filename.split(os.sep))

            if len(file_parts) != 2:
                return None

            foldername, filename = file_parts

            is_channel = lambda c: c.download_folder == foldername
            is_episode = lambda e: e.download_filename == filename

        # Deep search through channels and episodes for a match
        for channel in filter(is_channel, self.channels):
            for episode in filter(is_episode, channel.get_all_episodes()):
                return episode

        return None

    def on_played(self, start, end, total, file_uri):
        """Handle the "played" signal from a media player"""
        if start == 0 and end == 0 and total == 0:
            # Ignore bogus play event
            return
        elif end < start + 5:
            # Ignore "less than five seconds" segments,
            # as they can happen with seeking, etc...
            return

        logger.debug('Received play action: %s (%d, %d, %d)', file_uri, start, end, total)
        episode = self.episode_object_by_uri(file_uri)

        if episode is not None:
            file_type = episode.file_type()

            now = time.time()
            if total > 0:
                episode.total_time = total
            elif total == 0:
                # Assume the episode's total time for the action
                total = episode.total_time

            assert (episode.current_position_updated is None or
                    now >= episode.current_position_updated)

            episode.current_position = end
            episode.current_position_updated = now
            episode.mark(is_played=True)
            episode.save()
            self.episode_list_status_changed([episode])

            # Submit this action to the webservice
            self.mygpo_client.on_playback_full(episode, start, end, total)

    def on_add_remove_podcasts_mygpo(self):
        actions = self.mygpo_client.get_received_actions()
        if not actions:
            return False

        existing_urls = [c.url for c in self.channels]

        # Columns for the episode selector window - just one...
        columns = (
            ('description', None, None, _('Action')),
        )

        # A list of actions that have to be chosen from
        changes = []

        # Actions that are ignored (already carried out)
        ignored = []

        for action in actions:
            if action.is_add and action.url not in existing_urls:
                changes.append(my.Change(action))
            elif action.is_remove and action.url in existing_urls:
                podcast_object = None
                for podcast in self.channels:
                    if podcast.url == action.url:
                        podcast_object = podcast
                        break
                changes.append(my.Change(action, podcast_object))
            else:
                ignored.append(action)

        # Confirm all ignored changes
        self.mygpo_client.confirm_received_actions(ignored)

        def execute_podcast_actions(selected):
            # In the future, we might retrieve the title from gpodder.net here,
            # but for now, we just use "None" to use the feed-provided title
            title = None
            add_list = [(title, c.action.url)
                    for c in selected if c.action.is_add]
            remove_list = [c.podcast for c in selected if c.action.is_remove]

            # Apply the accepted changes locally
            self.add_podcast_list(add_list)
            self.remove_podcast_list(remove_list, confirm=False)

            # All selected items are now confirmed
            self.mygpo_client.confirm_received_actions(c.action for c in selected)

            # Revert the changes on the server
            rejected = [c.action for c in changes if c not in selected]
            self.mygpo_client.reject_received_actions(rejected)

        def ask():
            # We're abusing the Episode Selector again ;) -- thp
            gPodderEpisodeSelector(self.main_window, \
                    title=_('Confirm changes from gpodder.net'), \
                    instructions=_('Select the actions you want to carry out.'), \
                    episodes=changes, \
                    columns=columns, \
                    size_attribute=None, \
                    stock_ok_button=gtk.STOCK_APPLY, \
                    callback=execute_podcast_actions, \
                    _config=self.config)

        # There are some actions that need the user's attention
        if changes:
            util.idle_add(ask)
            return True

        # We have no remaining actions - no selection happens
        return False

    def rewrite_urls_mygpo(self):
        # Check if we have to rewrite URLs since the last add
        rewritten_urls = self.mygpo_client.get_rewritten_urls()
        changed = False

        for rewritten_url in rewritten_urls:
            if not rewritten_url.new_url:
                continue

            for channel in self.channels:
                if channel.url == rewritten_url.old_url:
                    logger.info('Updating URL of %s to %s', channel,
                            rewritten_url.new_url)
                    channel.url = rewritten_url.new_url
                    channel.save()
                    changed = True
                    break

        if changed:
            util.idle_add(self.update_episode_list_model)

    def on_send_full_subscriptions(self):
        # Send the full subscription list to the gpodder.net client
        # (this will overwrite the subscription list on the server)
        indicator = ProgressIndicator(_('Uploading subscriptions'), \
                _('Your subscriptions are being uploaded to the server.'), \
                False, self.get_dialog_parent())

        try:
            self.mygpo_client.set_subscriptions([c.url for c in self.channels])
            util.idle_add(self.show_message, _('List uploaded successfully.'))
        except Exception, e:
            def show_error(e):
                message = str(e)
                if not message:
                    message = e.__class__.__name__
                self.show_message(message, \
                        _('Error while uploading'), \
                        important=True)
            util.idle_add(show_error, e)

        util.idle_add(indicator.on_finished)

    def on_button_subscribe_clicked(self, button):
        self.on_itemImportChannels_activate(button)

    def on_button_downloads_clicked(self, widget):
        self.downloads_window.show()

    def for_each_episode_set_task_status(self, episodes, status):
        episode_urls = set(episode.url for episode in episodes)
        model = self.treeDownloads.get_model()
        selected_tasks = [(gtk.TreeRowReference(model, row.path), \
                           model.get_value(row.iter, \
                           DownloadStatusModel.C_TASK)) for row in model \
                           if model.get_value(row.iter, DownloadStatusModel.C_TASK).url \
                           in episode_urls]
        self._for_each_task_set_status(selected_tasks, status)

    def on_treeview_button_pressed(self, treeview, event):
        if event.window != treeview.get_bin_window():
            return False

        role = getattr(treeview, TreeViewHelper.ROLE)
        if role == TreeViewHelper.ROLE_EPISODES and event.button == 1:
            # Toggle episode "new" status by clicking the icon (bug 1432)
            result = treeview.get_path_at_pos(int(event.x), int(event.y))
            if result is not None:
                path, column, x, y = result
                # The user clicked the icon if she clicked in the first column
                # and the x position is in the area where the icon resides
                if (x < self.EPISODE_LIST_ICON_WIDTH and
                        column == treeview.get_columns()[0]):
                    model = treeview.get_model()
                    cursor_episode = model.get_value(model.get_iter(path),
                            EpisodeListModel.C_EPISODE)

                    new_value = cursor_episode.is_new
                    selected_episodes = self.get_selected_episodes()

                    # Avoid changing anything if the clicked episode is not
                    # selected already - otherwise update all selected
                    if cursor_episode in selected_episodes:
                        for episode in selected_episodes:
                            episode.mark(is_played=new_value)

                        self.update_episode_list_icons(selected=True)
                        self.update_podcast_list_model(selected=True)
                        return True

        return event.button == 3

    def on_treeview_podcasts_button_released(self, treeview, event):
        if event.window != treeview.get_bin_window():
            return False

        return self.treeview_channels_show_context_menu(treeview, event)

    def on_treeview_episodes_button_released(self, treeview, event):
        if event.window != treeview.get_bin_window():
            return False

        return self.treeview_available_show_context_menu(treeview, event)

    def on_treeview_downloads_button_released(self, treeview, event):
        if event.window != treeview.get_bin_window():
            return False

        return self.treeview_downloads_show_context_menu(treeview, event)

    def on_entry_search_podcasts_changed(self, editable):
        if self.hbox_search_podcasts.get_property('visible'):
            def set_search_term(self, text):
                self.podcast_list_model.set_search_term(text)
                self._podcast_list_search_timeout = None
                return False

            if self._podcast_list_search_timeout is not None:
                gobject.source_remove(self._podcast_list_search_timeout)
            self._podcast_list_search_timeout = gobject.timeout_add(
                    self.config.ui.gtk.live_search_delay,
                    set_search_term, self, editable.get_chars(0, -1))

    def on_entry_search_podcasts_key_press(self, editable, event):
        if event.keyval == gtk.keysyms.Escape:
            self.hide_podcast_search()
            return True

    def hide_podcast_search(self, *args):
        if self._podcast_list_search_timeout is not None:
            gobject.source_remove(self._podcast_list_search_timeout)
            self._podcast_list_search_timeout = None
        self.hbox_search_podcasts.hide()
        self.entry_search_podcasts.set_text('')
        self.podcast_list_model.set_search_term(None)
        self.treeChannels.grab_focus()

    def show_podcast_search(self, input_char):
        self.hbox_search_podcasts.show()
        self.entry_search_podcasts.insert_text(input_char, -1)
        self.entry_search_podcasts.grab_focus()
        self.entry_search_podcasts.set_position(-1)

    def init_podcast_list_treeview(self):
        # Set up podcast channel tree view widget
        column = gtk.TreeViewColumn('')
        iconcell = gtk.CellRendererPixbuf()
        iconcell.set_property('width', 45)
        column.pack_start(iconcell, False)
        column.add_attribute(iconcell, 'pixbuf', PodcastListModel.C_COVER)
        column.add_attribute(iconcell, 'visible', PodcastListModel.C_COVER_VISIBLE)

        namecell = gtk.CellRendererText()
        namecell.set_property('ellipsize', pango.ELLIPSIZE_END)
        column.pack_start(namecell, True)
        column.add_attribute(namecell, 'markup', PodcastListModel.C_DESCRIPTION)

        iconcell = gtk.CellRendererPixbuf()
        iconcell.set_property('xalign', 1.0)
        column.pack_start(iconcell, False)
        column.add_attribute(iconcell, 'pixbuf', PodcastListModel.C_PILL)
        column.add_attribute(iconcell, 'visible', PodcastListModel.C_PILL_VISIBLE)

        self.treeChannels.append_column(column)

        self.treeChannels.set_model(self.podcast_list_model.get_filtered_model())

        # When no podcast is selected, clear the episode list model
        selection = self.treeChannels.get_selection()
        def select_function(selection, model, path, path_currently_selected):
            url = model.get_value(model.get_iter(path), PodcastListModel.C_URL)
            return (url != '-')
        selection.set_select_function(select_function, full=True)

        # Set up type-ahead find for the podcast list
        def on_key_press(treeview, event):
            if event.keyval == gtk.keysyms.Right:
                self.treeAvailable.grab_focus()
            elif event.keyval in (gtk.keysyms.Up, gtk.keysyms.Down):
                # If section markers exist in the treeview, we want to
                # "jump over" them when moving the cursor up and down
                selection = self.treeChannels.get_selection()
                model, it = selection.get_selected()

                if event.keyval == gtk.keysyms.Up:
                    step = -1
                else:
                    step = 1

                path = model.get_path(it)
                while True:
                    path = (path[0]+step,)

                    if path[0] < 0:
                        # Valid paths must have a value >= 0
                        return True

                    try:
                        it = model.get_iter(path)
                    except ValueError:
                        # Already at the end of the list
                        return True

                    if model.get_value(it, PodcastListModel.C_URL) != '-':
                        break

                self.treeChannels.set_cursor(path)
            elif event.keyval == gtk.keysyms.Escape:
                self.hide_podcast_search()
            elif event.state & gtk.gdk.CONTROL_MASK:
                # Don't handle type-ahead when control is pressed (so shortcuts
                # with the Ctrl key still work, e.g. Ctrl+A, ...)
                return True
            else:
                unicode_char_id = gtk.gdk.keyval_to_unicode(event.keyval)
                if unicode_char_id == 0:
                    return False
                input_char = unichr(unicode_char_id)
                self.show_podcast_search(input_char)
            return True
        self.treeChannels.connect('key-press-event', on_key_press)

        self.treeChannels.connect('popup-menu', self.treeview_channels_show_context_menu)

        # Enable separators to the podcast list to separate special podcasts
        # from others (this is used for the "all episodes" view)
        self.treeChannels.set_row_separator_func(PodcastListModel.row_separator_func)

        TreeViewHelper.set(self.treeChannels, TreeViewHelper.ROLE_PODCASTS)

    def on_entry_search_episodes_changed(self, editable):
        if self.hbox_search_episodes.get_property('visible'):
            def set_search_term(self, text):
                self.episode_list_model.set_search_term(text)
                self._episode_list_search_timeout = None
                return False

            if self._episode_list_search_timeout is not None:
                gobject.source_remove(self._episode_list_search_timeout)
            self._episode_list_search_timeout = gobject.timeout_add(
                    self.config.ui.gtk.live_search_delay,
                    set_search_term, self, editable.get_chars(0, -1))

    def on_entry_search_episodes_key_press(self, editable, event):
        if event.keyval == gtk.keysyms.Escape:
            self.hide_episode_search()
            return True

    def hide_episode_search(self, *args):
        if self._episode_list_search_timeout is not None:
            gobject.source_remove(self._episode_list_search_timeout)
            self._episode_list_search_timeout = None
        self.hbox_search_episodes.hide()
        self.entry_search_episodes.set_text('')
        self.episode_list_model.set_search_term(None)
        self.treeAvailable.grab_focus()

    def show_episode_search(self, input_char):
        self.hbox_search_episodes.show()
        self.entry_search_episodes.insert_text(input_char, -1)
        self.entry_search_episodes.grab_focus()
        self.entry_search_episodes.set_position(-1)

    def set_episode_list_column(self, index, new_value):
        mask = (1 << index)
        if new_value:
            self.config.episode_list_columns |= mask
        else:
            self.config.episode_list_columns &= ~mask

    def update_episode_list_columns_visibility(self):
        columns = TreeViewHelper.get_columns(self.treeAvailable)
        for index, column in enumerate(columns):
            visible = bool(self.config.episode_list_columns & (1 << index))
            column.set_visible(visible)
        self.treeAvailable.columns_autosize()

        if self.episode_columns_menu is not None:
            children = self.episode_columns_menu.get_children()
            for index, child in enumerate(children):
                active = bool(self.config.episode_list_columns & (1 << index))
                child.set_active(active)

    def on_episode_list_header_clicked(self, button, event):
        if event.button != 3:
            return False

        if self.episode_columns_menu is not None:
            self.episode_columns_menu.popup(None, None, None, event.button, \
                    event.time, None)

        return False

    def init_episode_list_treeview(self):
        # For loading the list model
        self.episode_list_model = EpisodeListModel(self.config, self.on_episode_list_filter_changed)

        if self.config.episode_list_view_mode == EpisodeListModel.VIEW_UNDELETED:
            self.item_view_episodes_undeleted.set_active(True)
        elif self.config.episode_list_view_mode == EpisodeListModel.VIEW_DOWNLOADED:
            self.item_view_episodes_downloaded.set_active(True)
        elif self.config.episode_list_view_mode == EpisodeListModel.VIEW_UNPLAYED:
            self.item_view_episodes_unplayed.set_active(True)
        else:
            self.item_view_episodes_all.set_active(True)

        self.episode_list_model.set_view_mode(self.config.episode_list_view_mode)

        self.treeAvailable.set_model(self.episode_list_model.get_filtered_model())

        TreeViewHelper.set(self.treeAvailable, TreeViewHelper.ROLE_EPISODES)

        iconcell = gtk.CellRendererPixbuf()
        episode_list_icon_size = gtk.icon_size_register('episode-list',
            EPISODE_LIST_ICON_SIZE, EPISODE_LIST_ICON_SIZE)
        iconcell.set_property('stock-size', episode_list_icon_size)
        iconcell.set_fixed_size(self.EPISODE_LIST_ICON_WIDTH, -1)

        namecell = gtk.CellRendererText()
        namecell.set_property('ellipsize', pango.ELLIPSIZE_END)
        namecolumn = gtk.TreeViewColumn(_('Episode'))
        namecolumn.pack_start(iconcell, False)
        namecolumn.add_attribute(iconcell, 'icon-name', EpisodeListModel.C_STATUS_ICON)
        namecolumn.pack_start(namecell, True)
        namecolumn.add_attribute(namecell, 'markup', EpisodeListModel.C_DESCRIPTION)
        namecolumn.set_sort_column_id(EpisodeListModel.C_DESCRIPTION)
        namecolumn.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        namecolumn.set_resizable(True)
        namecolumn.set_expand(True)

        lockcell = gtk.CellRendererPixbuf()
        lockcell.set_fixed_size(40, -1)
        lockcell.set_property('stock-size', gtk.ICON_SIZE_MENU)
        lockcell.set_property('icon-name', 'emblem-readonly')
        namecolumn.pack_start(lockcell, False)
        namecolumn.add_attribute(lockcell, 'visible', EpisodeListModel.C_LOCKED)

        sizecell = gtk.CellRendererText()
        sizecell.set_property('xalign', 1)
        sizecolumn = gtk.TreeViewColumn(_('Size'), sizecell, text=EpisodeListModel.C_FILESIZE_TEXT)
        sizecolumn.set_sort_column_id(EpisodeListModel.C_FILESIZE)

        timecell = gtk.CellRendererText()
        timecell.set_property('xalign', 1)
        timecolumn = gtk.TreeViewColumn(_('Duration'), timecell, text=EpisodeListModel.C_TIME)
        timecolumn.set_sort_column_id(EpisodeListModel.C_TOTAL_TIME)

        releasecell = gtk.CellRendererText()
        releasecolumn = gtk.TreeViewColumn(_('Released'), releasecell, text=EpisodeListModel.C_PUBLISHED_TEXT)
        releasecolumn.set_sort_column_id(EpisodeListModel.C_PUBLISHED)

        namecolumn.set_reorderable(True)
        self.treeAvailable.append_column(namecolumn)

        for itemcolumn in (sizecolumn, timecolumn, releasecolumn):
            itemcolumn.set_reorderable(True)
            self.treeAvailable.append_column(itemcolumn)
            TreeViewHelper.register_column(self.treeAvailable, itemcolumn)

        # Add context menu to all tree view column headers
        for column in self.treeAvailable.get_columns():
            label = gtk.Label(column.get_title())
            label.show_all()
            column.set_widget(label)

            w = column.get_widget()
            while w is not None and not isinstance(w, gtk.Button):
                w = w.get_parent()

            w.connect('button-release-event', self.on_episode_list_header_clicked)

        # Create a new menu for the visible episode list columns
        for child in self.mainMenu.get_children():
            if child.get_name() == 'menuView':
                submenu = child.get_submenu()
                item = gtk.MenuItem(_('Visible columns'))
                submenu.append(gtk.SeparatorMenuItem())
                submenu.append(item)
                submenu.show_all()

                self.episode_columns_menu = gtk.Menu()
                item.set_submenu(self.episode_columns_menu)
                break

        # For each column that can be shown/hidden, add a menu item
        columns = TreeViewHelper.get_columns(self.treeAvailable)
        for index, column in enumerate(columns):
            item = gtk.CheckMenuItem(column.get_title())
            self.episode_columns_menu.append(item)
            def on_item_toggled(item, index):
                self.set_episode_list_column(index, item.get_active())
            item.connect('toggled', on_item_toggled, index)
        self.episode_columns_menu.show_all()

        # Update the visibility of the columns and the check menu items
        self.update_episode_list_columns_visibility()

        # Set up type-ahead find for the episode list
        def on_key_press(treeview, event):
            if event.keyval == gtk.keysyms.Left:
                self.treeChannels.grab_focus()
            elif event.keyval == gtk.keysyms.Escape:
                if self.hbox_search_episodes.get_property('visible'):
                    self.hide_episode_search()
                else:
                    self.shownotes_object.hide_pane()
            elif event.state & gtk.gdk.CONTROL_MASK:
                # Don't handle type-ahead when control is pressed (so shortcuts
                # with the Ctrl key still work, e.g. Ctrl+A, ...)
                return False
            else:
                unicode_char_id = gtk.gdk.keyval_to_unicode(event.keyval)
                if unicode_char_id == 0:
                    return False
                input_char = unichr(unicode_char_id)
                self.show_episode_search(input_char)
            return True
        self.treeAvailable.connect('key-press-event', on_key_press)

        self.treeAvailable.connect('popup-menu', self.treeview_available_show_context_menu)

        self.treeAvailable.enable_model_drag_source(gtk.gdk.BUTTON1_MASK, \
                (('text/uri-list', 0, 0),), gtk.gdk.ACTION_COPY)
        def drag_data_get(tree, context, selection_data, info, timestamp):
            uris = ['file://'+e.local_filename(create=False) \
                    for e in self.get_selected_episodes() \
                    if e.was_downloaded(and_exists=True)]
            uris.append('') # for the trailing '\r\n'
            selection_data.set(selection_data.target, 8, '\r\n'.join(uris))
        self.treeAvailable.connect('drag-data-get', drag_data_get)

        selection = self.treeAvailable.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        selection.connect('changed', self.on_episode_list_selection_changed)

    def on_episode_list_selection_changed(self, selection):
        # Update the toolbar buttons
        self.play_or_download()
        # and the shownotes
        self.shownotes_object.set_episodes(self.get_selected_episodes())

    def init_download_list_treeview(self):
        # enable multiple selection support
        self.treeDownloads.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.treeDownloads.set_search_equal_func(TreeViewHelper.make_search_equal_func(DownloadStatusModel))

        # columns and renderers for "download progress" tab
        # First column: [ICON] Episodename
        column = gtk.TreeViewColumn(_('Episode'))

        cell = gtk.CellRendererPixbuf()
        cell.set_property('stock-size', gtk.ICON_SIZE_BUTTON)
        column.pack_start(cell, expand=False)
        column.add_attribute(cell, 'icon-name', \
                DownloadStatusModel.C_ICON_NAME)

        cell = gtk.CellRendererText()
        cell.set_property('ellipsize', pango.ELLIPSIZE_END)
        column.pack_start(cell, expand=True)
        column.add_attribute(cell, 'markup', DownloadStatusModel.C_NAME)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        column.set_expand(True)
        self.treeDownloads.append_column(column)

        # Second column: Progress
        cell = gtk.CellRendererProgress()
        cell.set_property('yalign', .5)
        cell.set_property('ypad', 6)
        column = gtk.TreeViewColumn(_('Progress'), cell,
                value=DownloadStatusModel.C_PROGRESS, \
                text=DownloadStatusModel.C_PROGRESS_TEXT)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        column.set_expand(False)
        self.treeDownloads.append_column(column)
        column.set_property('min-width', 150)
        column.set_property('max-width', 150)

        self.treeDownloads.set_model(self.download_status_model)
        TreeViewHelper.set(self.treeDownloads, TreeViewHelper.ROLE_DOWNLOADS)

        self.treeDownloads.connect('popup-menu', self.treeview_downloads_show_context_menu)

    def on_treeview_expose_event(self, treeview, event):
        if event.window == treeview.get_bin_window():
            model = treeview.get_model()
            if (model is not None and model.get_iter_first() is not None):
                return False

            role = getattr(treeview, TreeViewHelper.ROLE, None)
            if role is None:
                return False

            ctx = event.window.cairo_create()
            ctx.rectangle(event.area.x, event.area.y,
                    event.area.width, event.area.height)
            ctx.clip()

            x, y, width, height, depth = event.window.get_geometry()
            progress = None

            if role == TreeViewHelper.ROLE_EPISODES:
                if self.config.episode_list_view_mode != EpisodeListModel.VIEW_ALL:
                    text = _('No episodes in current view')
                else:
                    text = _('No episodes available')
            elif role == TreeViewHelper.ROLE_PODCASTS:
                if self.config.episode_list_view_mode != \
                        EpisodeListModel.VIEW_ALL and \
                        self.config.podcast_list_hide_boring and \
                        len(self.channels) > 0:
                    text = _('No podcasts in this view')
                else:
                    text = _('No subscriptions')
            elif role == TreeViewHelper.ROLE_DOWNLOADS:
                text = _('No active tasks')
            else:
                raise Exception('on_treeview_expose_event: unknown role')

            font_desc = None
            draw_text_box_centered(ctx, treeview, width, height, text, font_desc, progress)

        return False

    def enable_download_list_update(self):
        if not self.download_list_update_enabled:
            self.update_downloads_list()
            gobject.timeout_add(1500, self.update_downloads_list)
            self.download_list_update_enabled = True

    def cleanup_downloads(self):
        model = self.download_status_model

        all_tasks = [(gtk.TreeRowReference(model, row.path), row[0]) for row in model]
        changed_episode_urls = set()
        for row_reference, task in all_tasks:
            if task.status in (task.DONE, task.CANCELLED):
                model.remove(model.get_iter(row_reference.get_path()))
                try:
                    # We don't "see" this task anymore - remove it;
                    # this is needed, so update_episode_list_icons()
                    # below gets the correct list of "seen" tasks
                    self.download_tasks_seen.remove(task)
                except KeyError, key_error:
                    pass
                changed_episode_urls.add(task.url)
                # Tell the task that it has been removed (so it can clean up)
                task.removed_from_list()

        # Tell the podcasts tab to update icons for our removed podcasts
        self.update_episode_list_icons(changed_episode_urls)

        # Update the downloads list one more time
        self.update_downloads_list(can_call_cleanup=False)

    def on_tool_downloads_toggled(self, toolbutton):
        if toolbutton.get_active():
            self.wNotebook.set_current_page(1)
        else:
            self.wNotebook.set_current_page(0)

    def add_download_task_monitor(self, monitor):
        self.download_task_monitors.add(monitor)
        model = self.download_status_model
        if model is None:
            model = ()
        for row in model:
            task = row[self.download_status_model.C_TASK]
            monitor.task_updated(task)

    def remove_download_task_monitor(self, monitor):
        self.download_task_monitors.remove(monitor)

    def set_download_progress(self, progress):
        gpodder.user_extensions.on_download_progress(progress)

    def update_downloads_list(self, can_call_cleanup=True):
        try:
            model = self.download_status_model

            downloading, synchronizing, failed, finished, queued, paused, others = 0, 0, 0, 0, 0, 0, 0
            total_speed, total_size, done_size = 0, 0, 0

            # Keep a list of all download tasks that we've seen
            download_tasks_seen = set()

            # Do not go through the list of the model is not (yet) available
            if model is None:
                model = ()

            for row in model:
                self.download_status_model.request_update(row.iter)

                task = row[self.download_status_model.C_TASK]
                speed, size, status, progress, activity = task.speed, task.total_size, task.status, task.progress, task.activity

                # Let the download task monitors know of changes
                for monitor in self.download_task_monitors:
                    monitor.task_updated(task)

                total_size += size
                done_size += size*progress

                download_tasks_seen.add(task)

                if (status == download.DownloadTask.DOWNLOADING and
                        activity == download.DownloadTask.ACTIVITY_DOWNLOAD):
                    downloading += 1
                    total_speed += speed
                elif (status == download.DownloadTask.DOWNLOADING and
                        activity == download.DownloadTask.ACTIVITY_SYNCHRONIZE):
                    synchronizing += 1
                elif status == download.DownloadTask.FAILED:
                    failed += 1
                elif status == download.DownloadTask.DONE:
                    finished += 1
                elif status == download.DownloadTask.QUEUED:
                    queued += 1
                elif status == download.DownloadTask.PAUSED:
                    paused += 1
                else:
                    others += 1

            # Remember which tasks we have seen after this run
            self.download_tasks_seen = download_tasks_seen

            text = [_('Progress')]
            if downloading + failed + queued + synchronizing > 0:
                s = []
                if downloading > 0:
                    s.append(N_('%(count)d active', '%(count)d active', downloading) % {'count':downloading})
                if synchronizing > 0:
                    s.append(N_('%(count)d active', '%(count)d active', synchronizing) % {'count':synchronizing})
                if failed > 0:
                    s.append(N_('%(count)d failed', '%(count)d failed', failed) % {'count':failed})
                if queued > 0:
                    s.append(N_('%(count)d queued', '%(count)d queued', queued) % {'count':queued})
                text.append(' (' + ', '.join(s)+')')
            self.labelDownloads.set_text(''.join(text))

            title = [self.default_title]

            # Accessing task.status_changed has the side effect of re-setting
            # the changed flag, but we only do it once here so that's okay
            channel_urls = [task.podcast_url for task in
                    self.download_tasks_seen if task.status_changed]
            episode_urls = [task.url for task in self.download_tasks_seen]


            if downloading > 0:
                title.append(N_('downloading %(count)d file', 'downloading %(count)d files', downloading) % {'count':downloading})

                if total_size > 0:
                    percentage = 100.0*done_size/total_size
                else:
                    percentage = 0.0
                self.set_download_progress(percentage/100.)
                total_speed = util.format_filesize(total_speed)
                title[1] += ' (%d%%, %s/s)' % (percentage, total_speed)
            if synchronizing > 0:
                title.append(N_('synchronizing %(count)d file', 'synchronizing %(count)d files', synchronizing) % {'count':synchronizing})
            if queued > 0:
                title.append(N_('%(queued)d task queued', '%(queued)d tasks queued', queued) % {'queued':queued})
            if (downloading + synchronizing + queued)==0:
                self.set_download_progress(1.)
                self.downloads_finished(self.download_tasks_seen)
                gpodder.user_extensions.on_all_episodes_downloaded()
                logger.info('All tasks have finished.')

                # Remove finished episodes
                if self.config.auto_cleanup_downloads and can_call_cleanup:
                    self.cleanup_downloads()

                # Stop updating the download list here
                self.download_list_update_enabled = False

            self.gPodder.set_title(' - '.join(title))

            self.update_episode_list_icons(episode_urls)
            self.play_or_download()
            if channel_urls:
                self.update_podcast_list_model(channel_urls)

            return self.download_list_update_enabled
        except Exception, e:
            logger.error('Exception happened while updating download list.', exc_info=True)
            self.show_message('%s\n\n%s' % (_('Please report this problem and restart gPodder:'), str(e)), _('Unhandled exception'), important=True)
            # We return False here, so the update loop won't be called again,
            # that's why we require the restart of gPodder in the message.
            return False

    def on_config_changed(self, *args):
        util.idle_add(self._on_config_changed, *args)

    def _on_config_changed(self, name, old_value, new_value):
        if name == 'ui.gtk.toolbar':
            self.toolbar.set_property('visible', new_value)
        elif name == 'ui.gtk.episode_list.descriptions':
            self.update_episode_list_model()
        elif name in ('auto.update.enabled', 'auto.update.frequency'):
            self.restart_auto_update_timer()
        elif name in ('ui.gtk.podcast_list.all_episodes',
                'ui.gtk.podcast_list.sections'):
            # Force a update of the podcast list model
            self.update_podcast_list_model()
        elif name == 'ui.gtk.episode_list.columns':
            self.update_episode_list_columns_visibility()

    def on_treeview_query_tooltip(self, treeview, x, y, keyboard_tooltip, tooltip):
        # With get_bin_window, we get the window that contains the rows without
        # the header. The Y coordinate of this window will be the height of the
        # treeview header. This is the amount we have to subtract from the
        # event's Y coordinate to get the coordinate to pass to get_path_at_pos
        (x_bin, y_bin) = treeview.get_bin_window().get_position()
        y -= x_bin
        y -= y_bin
        (path, column, rx, ry) = treeview.get_path_at_pos( x, y) or (None,)*4

        if not getattr(treeview, TreeViewHelper.CAN_TOOLTIP) or x > 50 or (column is not None and column != treeview.get_columns()[0]):
            setattr(treeview, TreeViewHelper.LAST_TOOLTIP, None)
            return False

        if path is not None:
            model = treeview.get_model()
            iter = model.get_iter(path)
            role = getattr(treeview, TreeViewHelper.ROLE)

            if role == TreeViewHelper.ROLE_EPISODES:
                id = model.get_value(iter, EpisodeListModel.C_URL)
            elif role == TreeViewHelper.ROLE_PODCASTS:
                id = model.get_value(iter, PodcastListModel.C_URL)
                if id == '-':
                    # Section header - no tooltip here (for now at least)
                    return False

            last_tooltip = getattr(treeview, TreeViewHelper.LAST_TOOLTIP)
            if last_tooltip is not None and last_tooltip != id:
                setattr(treeview, TreeViewHelper.LAST_TOOLTIP, None)
                return False
            setattr(treeview, TreeViewHelper.LAST_TOOLTIP, id)

            if role == TreeViewHelper.ROLE_EPISODES:
                description = model.get_value(iter, EpisodeListModel.C_TOOLTIP)
                if description:
                    tooltip.set_text(description)
                else:
                    return False
            elif role == TreeViewHelper.ROLE_PODCASTS:
                channel = model.get_value(iter, PodcastListModel.C_CHANNEL)
                if channel is None or not hasattr(channel, 'title'):
                    return False
                error_str = model.get_value(iter, PodcastListModel.C_ERROR)
                if error_str:
                    error_str = _('Feedparser error: %s') % cgi.escape(error_str.strip())
                    error_str = '<span foreground="#ff0000">%s</span>' % error_str
                table = gtk.Table(rows=3, columns=3)
                table.set_row_spacings(5)
                table.set_col_spacings(5)
                table.set_border_width(5)

                heading = gtk.Label()
                heading.set_alignment(0, 1)
                heading.set_markup('<b><big>%s</big></b>\n<small>%s</small>' % (cgi.escape(channel.title), cgi.escape(channel.url)))
                table.attach(heading, 0, 1, 0, 1)

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

        setattr(treeview, TreeViewHelper.LAST_TOOLTIP, None)
        return False

    def treeview_allow_tooltips(self, treeview, allow):
        setattr(treeview, TreeViewHelper.CAN_TOOLTIP, allow)

    def treeview_handle_context_menu_click(self, treeview, event):
        if event is None:
            selection = treeview.get_selection()
            return selection.get_selected_rows()

        x, y = int(event.x), int(event.y)
        path, column, rx, ry = treeview.get_path_at_pos(x, y) or (None,)*4

        selection = treeview.get_selection()
        model, paths = selection.get_selected_rows()

        if path is None or (path not in paths and \
                event.button == 3):
            # We have right-clicked, but not into the selection,
            # assume we don't want to operate on the selection
            paths = []

        if path is not None and not paths and \
                event.button == 3:
            # No selection or clicked outside selection;
            # select the single item where we clicked
            treeview.grab_focus()
            treeview.set_cursor(path, column, 0)
            paths = [path]

        if not paths:
            # Unselect any remaining items (clicked elsewhere)
            if hasattr(treeview, 'is_rubber_banding_active'):
                if not treeview.is_rubber_banding_active():
                    selection.unselect_all()
            else:
                selection.unselect_all()

        return model, paths

    def downloads_list_get_selection(self, model=None, paths=None):
        if model is None and paths is None:
            selection = self.treeDownloads.get_selection()
            model, paths = selection.get_selected_rows()

        can_queue, can_cancel, can_pause, can_remove, can_force = (True,)*5
        selected_tasks = [(gtk.TreeRowReference(model, path), \
                           model.get_value(model.get_iter(path), \
                           DownloadStatusModel.C_TASK)) for path in paths]

        for row_reference, task in selected_tasks:
            if task.status != download.DownloadTask.QUEUED:
                can_force = False
            if task.status not in (download.DownloadTask.PAUSED, \
                    download.DownloadTask.FAILED, \
                    download.DownloadTask.CANCELLED):
                can_queue = False
            if task.status not in (download.DownloadTask.PAUSED, \
                    download.DownloadTask.QUEUED, \
                    download.DownloadTask.DOWNLOADING, \
                    download.DownloadTask.FAILED):
                can_cancel = False
            if task.status not in (download.DownloadTask.QUEUED, \
                    download.DownloadTask.DOWNLOADING):
                can_pause = False
            if task.status not in (download.DownloadTask.CANCELLED, \
                    download.DownloadTask.FAILED, \
                    download.DownloadTask.DONE):
                can_remove = False

        return selected_tasks, can_queue, can_cancel, can_pause, can_remove, can_force

    def downloads_finished(self, download_tasks_seen):
        # Separate tasks into downloads & syncs
        # Since calling notify_as_finished or notify_as_failed clears the flag,
        # need to iterate through downloads & syncs separately, else all sync
        # tasks will have their flags cleared if we do downloads first

        def filter_by_activity(activity, tasks):
            return filter(lambda task: task.activity == activity, tasks)

        download_tasks = filter_by_activity(download.DownloadTask.ACTIVITY_DOWNLOAD,
                download_tasks_seen)

        finished_downloads = [str(task)
                for task in download_tasks if task.notify_as_finished()]
        failed_downloads = ['%s (%s)' % (str(task), task.error_message)
                for task in download_tasks if task.notify_as_failed()]

        sync_tasks = filter_by_activity(download.DownloadTask.ACTIVITY_SYNCHRONIZE,
                download_tasks_seen)

        finished_syncs = [task for task in sync_tasks if task.notify_as_finished()]
        failed_syncs = [task for task in sync_tasks if task.notify_as_failed()]

        # Note that 'finished_ / failed_downloads' is a list of strings
        # Whereas 'finished_ / failed_syncs' is a list of SyncTask objects

        if finished_downloads and failed_downloads:
            message = self.format_episode_list(finished_downloads, 5)
            message += '\n\n<i>%s</i>\n' % _('Could not download some episodes:')
            message += self.format_episode_list(failed_downloads, 5)
            self.show_message(message, _('Downloads finished'), widget=self.labelDownloads)
        elif finished_downloads:
            message = self.format_episode_list(finished_downloads)
            self.show_message(message, _('Downloads finished'), widget=self.labelDownloads)
        elif failed_downloads:
            message = self.format_episode_list(failed_downloads)
            self.show_message(message, _('Downloads failed'), widget=self.labelDownloads)

        if finished_syncs and failed_syncs:
            message = self.format_episode_list(map((lambda task: str(task)),finished_syncs), 5)
            message += '\n\n<i>%s</i>\n' % _('Could not sync some episodes:')
            message += self.format_episode_list(map((lambda task: str(task)),failed_syncs), 5)
            self.show_message(message, _('Device synchronization finished'), True, widget=self.labelDownloads)
        elif finished_syncs:
            message = self.format_episode_list(map((lambda task: str(task)),finished_syncs))
            self.show_message(message, _('Device synchronization finished'), widget=self.labelDownloads)
        elif failed_syncs:
            message = self.format_episode_list(map((lambda task: str(task)),failed_syncs))
            self.show_message(message, _('Device synchronization failed'), True, widget=self.labelDownloads)

        # Do post-sync processing if required
        for task in finished_syncs:
            if self.config.device_sync.after_sync.mark_episodes_played:
                logger.info('Marking as played on transfer: %s', task.episode.url)
                task.episode.mark(is_played=True)

            if self.config.device_sync.after_sync.delete_episodes:
                logger.info('Removing episode after transfer: %s', task.episode.url)
                task.episode.delete_from_disk()

            self.sync_ui.device.close()

        # Update icon list to show changes, if any
        self.update_episode_list_icons(all=True)
        self.update_podcast_list_model()


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
            # Bug 1834: make sure title is a unicode string,
            # so it may be cut correctly on UTF-8 char boundaries
            title = util.convert_bytes(title)
            if len(title) > MAX_TITLE_LENGTH:
                middle = (MAX_TITLE_LENGTH/2)-2
                title = '%s...%s' % (title[0:middle], title[-middle:])
            result.append(cgi.escape(title))
            result.append('\n')

        more_episodes = len(episode_list) - max_episodes
        if more_episodes > 0:
            result.append('(...')
            result.append(N_('%(count)d more episode', '%(count)d more episodes', more_episodes) % {'count':more_episodes})
            result.append('...)')

        return (''.join(result)).strip()

    def _for_each_task_set_status(self, tasks, status, force_start=False):
        episode_urls = set()
        model = self.treeDownloads.get_model()
        for row_reference, task in tasks:
            if status == download.DownloadTask.QUEUED:
                # Only queue task when its paused/failed/cancelled (or forced)
                if task.status in (task.PAUSED, task.FAILED, task.CANCELLED) or force_start:
                    self.download_queue_manager.add_task(task, force_start)
                    self.enable_download_list_update()
            elif status == download.DownloadTask.CANCELLED:
                # Cancelling a download allowed when downloading/queued
                if task.status in (task.QUEUED, task.DOWNLOADING):
                    task.status = status
                # Cancelling paused/failed downloads requires a call to .run()
                elif task.status in (task.PAUSED, task.FAILED):
                    task.status = status
                    # Call run, so the partial file gets deleted
                    task.run()
            elif status == download.DownloadTask.PAUSED:
                # Pausing a download only when queued/downloading
                if task.status in (task.DOWNLOADING, task.QUEUED):
                    task.status = status
            elif status is None:
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
                    pass
                episode_urls.add(task.url)
                # Tell the task that it has been removed (so it can clean up)
                task.removed_from_list()
            else:
                # We can (hopefully) simply set the task status here
                task.status = status
        # Tell the podcasts tab to update icons for our removed podcasts
        self.update_episode_list_icons(episode_urls)
        # Update the tab title and downloads list
        self.update_downloads_list()

    def treeview_downloads_show_context_menu(self, treeview, event=None):
        model, paths = self.treeview_handle_context_menu_click(treeview, event)
        if not paths:
            if not hasattr(treeview, 'is_rubber_banding_active'):
                return True
            else:
                return not treeview.is_rubber_banding_active()

        if event is None or event.button == 3:
            selected_tasks, can_queue, can_cancel, can_pause, can_remove, can_force = \
                    self.downloads_list_get_selection(model, paths)

            def make_menu_item(label, stock_id, tasks, status, sensitive, force_start=False):
                # This creates a menu item for selection-wide actions
                item = gtk.ImageMenuItem(label)
                item.set_image(gtk.image_new_from_stock(stock_id, gtk.ICON_SIZE_MENU))
                item.connect('activate', lambda item: self._for_each_task_set_status(tasks, status, force_start))
                item.set_sensitive(sensitive)
                return item

            menu = gtk.Menu()

            if can_force:
                menu.append(make_menu_item(_('Start download now'), gtk.STOCK_GO_DOWN, selected_tasks, download.DownloadTask.QUEUED, True, True))
            else:
                menu.append(make_menu_item(_('Download'), gtk.STOCK_GO_DOWN, selected_tasks, download.DownloadTask.QUEUED, can_queue, False))
            menu.append(make_menu_item(_('Cancel'), gtk.STOCK_CANCEL, selected_tasks, download.DownloadTask.CANCELLED, can_cancel))
            menu.append(make_menu_item(_('Pause'), gtk.STOCK_MEDIA_PAUSE, selected_tasks, download.DownloadTask.PAUSED, can_pause))
            menu.append(gtk.SeparatorMenuItem())
            menu.append(make_menu_item(_('Remove from list'), gtk.STOCK_REMOVE, selected_tasks, None, can_remove))

            menu.show_all()

            if event is None:
                func = TreeViewHelper.make_popup_position_func(treeview)
                menu.popup(None, None, func, 3, 0)
            else:
                menu.popup(None, None, None, event.button, event.time)
            return True

    def on_mark_episodes_as_old(self, item):
        assert self.active_channel is not None

        for episode in self.active_channel.get_all_episodes():
            if not episode.was_downloaded(and_exists=True):
                episode.mark(is_played=True)

        self.update_podcast_list_model(selected=True)
        self.update_episode_list_icons(all=True)

    def on_open_download_folder(self, item):
        assert self.active_channel is not None
        util.gui_open(self.active_channel.save_dir)

    def treeview_channels_show_context_menu(self, treeview, event=None):
        model, paths = self.treeview_handle_context_menu_click(treeview, event)
        if not paths:
            return True

        # Check for valid channel id, if there's no id then
        # assume that it is a proxy channel or equivalent
        # and cannot be operated with right click
        if self.active_channel.id is None:
            return True

        if event is None or event.button == 3:
            menu = gtk.Menu()

            item = gtk.ImageMenuItem( _('Update podcast'))
            item.set_image(gtk.image_new_from_stock(gtk.STOCK_REFRESH, gtk.ICON_SIZE_MENU))
            item.connect('activate', self.on_itemUpdateChannel_activate)
            menu.append(item)

            menu.append(gtk.SeparatorMenuItem())

            item = gtk.MenuItem(_('Open download folder'))
            item.connect('activate', self.on_open_download_folder)
            menu.append(item)

            menu.append(gtk.SeparatorMenuItem())

            item = gtk.MenuItem(_('Mark episodes as old'))
            item.connect('activate', self.on_mark_episodes_as_old)
            menu.append(item)

            item = gtk.CheckMenuItem(_('Archive'))
            item.set_active(self.active_channel.auto_archive_episodes)
            item.connect('activate', self.on_channel_toggle_lock_activate)
            menu.append(item)

            item = gtk.ImageMenuItem(_('Remove podcast'))
            item.set_image(gtk.image_new_from_stock(gtk.STOCK_DELETE, gtk.ICON_SIZE_MENU))
            item.connect( 'activate', self.on_itemRemoveChannel_activate)
            menu.append( item)

            result = gpodder.user_extensions.on_channel_context_menu(self.active_channel)
            if result:
                menu.append(gtk.SeparatorMenuItem())
                for label, callback in result:
                    item = gtk.MenuItem(label)
                    item.connect('activate', lambda item, callback: callback(self.active_channel), callback)
                    menu.append(item)

            menu.append(gtk.SeparatorMenuItem())

            item = gtk.ImageMenuItem(_('Podcast settings'))
            item.set_image(gtk.image_new_from_stock(gtk.STOCK_INFO, gtk.ICON_SIZE_MENU))
            item.connect('activate', self.on_itemEditChannel_activate)
            menu.append(item)

            menu.show_all()
            # Disable tooltips while we are showing the menu, so
            # the tooltip will not appear over the menu
            self.treeview_allow_tooltips(self.treeChannels, False)
            menu.connect('deactivate', lambda menushell: self.treeview_allow_tooltips(self.treeChannels, True))

            if event is None:
                func = TreeViewHelper.make_popup_position_func(treeview)
                menu.popup(None, None, func, 3, 0)
            else:
                menu.popup(None, None, None, event.button, event.time)

            return True

    def cover_download_finished(self, channel, pixbuf):
        """
        The Cover Downloader calls this when it has finished
        downloading (or registering, if already downloaded)
        a new channel cover, which is ready for displaying.
        """
        util.idle_add(self.podcast_list_model.add_cover_by_channel,
                channel, pixbuf)

    def save_episodes_as_file(self, episodes):
        for episode in episodes:
            self.save_episode_as_file(episode)

    def save_episode_as_file(self, episode):
        PRIVATE_FOLDER_ATTRIBUTE = '_save_episodes_as_file_folder'
        if episode.was_downloaded(and_exists=True):
            folder = getattr(self, PRIVATE_FOLDER_ATTRIBUTE, None)
            copy_from = episode.local_filename(create=False)
            assert copy_from is not None
            copy_to = util.sanitize_filename(episode.sync_filename())
            (result, folder) = self.show_copy_dialog(src_filename=copy_from, dst_filename=copy_to, dst_directory=folder)
            setattr(self, PRIVATE_FOLDER_ATTRIBUTE, folder)

    def copy_episodes_bluetooth(self, episodes):
        episodes_to_copy = [e for e in episodes if e.was_downloaded(and_exists=True)]

        def convert_and_send_thread(episode):
            for episode in episodes:
                filename = episode.local_filename(create=False)
                assert filename is not None
                destfile = os.path.join(tempfile.gettempdir(), \
                        util.sanitize_filename(episode.sync_filename()))
                (base, ext) = os.path.splitext(filename)
                if not destfile.endswith(ext):
                    destfile += ext

                try:
                    shutil.copyfile(filename, destfile)
                    util.bluetooth_send_file(destfile)
                except:
                    logger.error('Cannot copy "%s" to "%s".', filename, destfile)
                    self.notification(_('Error converting file.'), _('Bluetooth file transfer'), important=True)

                util.delete_file(destfile)

        util.run_in_background(lambda: convert_and_send_thread(episodes_to_copy))

    def _add_sub_menu(self, menu, label):
        root_item = gtk.MenuItem(label)
        menu.append(root_item)
        sub_menu = gtk.Menu()
        root_item.set_submenu(sub_menu)
        return sub_menu

    def _submenu_item_activate_hack(self, item, callback, *args):
        # See http://stackoverflow.com/questions/5221326/submenu-item-does-not-call-function-with-working-solution
        # Note that we can't just call the callback on button-press-event, as
        # it might be blocking (see http://gpodder.org/bug/1778), so we run
        # this in the GUI thread at a later point in time (util.idle_add).
        # Also, we also have to connect to the activate signal, as this is the
        # only signal that is fired when keyboard navigation is used.

        # It can happen that both (button-release-event and activate) signals
        # are fired, and we must avoid calling the callback twice. We do this
        # using a semaphore and only acquiring (but never releasing) it, making
        # sure that the util.idle_add() call below is only ever called once.
        only_once = threading.Semaphore(1)

        def handle_event(item, event=None):
            if only_once.acquire(False):
                util.idle_add(callback, *args)

        item.connect('button-press-event', handle_event)
        item.connect('activate', handle_event)

    def treeview_available_show_context_menu(self, treeview, event=None):
        model, paths = self.treeview_handle_context_menu_click(treeview, event)
        if not paths:
            if not hasattr(treeview, 'is_rubber_banding_active'):
                return True
            else:
                return not treeview.is_rubber_banding_active()

        if event is None or event.button == 3:
            episodes = self.get_selected_episodes()
            any_locked = any(e.archive for e in episodes)
            any_new = any(e.is_new for e in episodes)
            downloaded = all(e.was_downloaded(and_exists=True) for e in episodes)
            downloading = any(e.downloading for e in episodes)

            menu = gtk.Menu()

            (can_play, can_download, can_cancel, can_delete, open_instead_of_play) = self.play_or_download()

            if open_instead_of_play:
                item = gtk.ImageMenuItem(gtk.STOCK_OPEN)
            elif downloaded:
                item = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PLAY)
            else:
                if downloading:
                    item = gtk.ImageMenuItem(_('Preview'))
                else:
                    item = gtk.ImageMenuItem(_('Stream'))
                item.set_image(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_MENU))

            item.set_sensitive(can_play)
            item.connect('activate', self.on_playback_selected_episodes)
            menu.append(item)

            if not can_cancel:
                item = gtk.ImageMenuItem(_('Download'))
                item.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_DOWN, gtk.ICON_SIZE_MENU))
                item.set_sensitive(can_download)
                item.connect('activate', self.on_download_selected_episodes)
                menu.append(item)
            else:
                item = gtk.ImageMenuItem(gtk.STOCK_CANCEL)
                item.connect('activate', self.on_item_cancel_download_activate)
                menu.append(item)

            item = gtk.ImageMenuItem(gtk.STOCK_DELETE)
            item.set_sensitive(can_delete)
            item.connect('activate', self.on_btnDownloadedDelete_clicked)
            menu.append(item)

            result = gpodder.user_extensions.on_episodes_context_menu(episodes)
            if result:
                menu.append(gtk.SeparatorMenuItem())
                submenus = {}
                for label, callback in result:
                    key, sep, title = label.rpartition('/')
                    item = gtk.ImageMenuItem(title)
                    self._submenu_item_activate_hack(item, callback, episodes)
                    if key:
                        if key not in submenus:
                            sub_menu = self._add_sub_menu(menu, key)
                            submenus[key] = sub_menu
                        else:
                            sub_menu = submenus[key]
                        sub_menu.append(item)
                    else:
                        menu.append(item)

            # Ok, this probably makes sense to only display for downloaded files
            if downloaded:
                menu.append(gtk.SeparatorMenuItem())
                share_menu = self._add_sub_menu(menu, _('Send to'))

                item = gtk.ImageMenuItem(_('Local folder'))
                item.set_image(gtk.image_new_from_stock(gtk.STOCK_DIRECTORY, gtk.ICON_SIZE_MENU))
                self._submenu_item_activate_hack(item, self.save_episodes_as_file, episodes)
                share_menu.append(item)
                if self.bluetooth_available:
                    item = gtk.ImageMenuItem(_('Bluetooth device'))
                    item.set_image(gtk.image_new_from_icon_name('bluetooth', gtk.ICON_SIZE_MENU))
                    self._submenu_item_activate_hack(item, self.copy_episodes_bluetooth, episodes)
                    share_menu.append(item)

            menu.append(gtk.SeparatorMenuItem())

            item = gtk.CheckMenuItem(_('New'))
            item.set_active(any_new)
            if any_new:
                item.connect('activate', lambda w: self.mark_selected_episodes_old())
            else:
                item.connect('activate', lambda w: self.mark_selected_episodes_new())
            menu.append(item)

            if downloaded:
                item = gtk.CheckMenuItem(_('Archive'))
                item.set_active(any_locked)
                item.connect('activate', lambda w: self.on_item_toggle_lock_activate( w, False, not any_locked))
                menu.append(item)

            menu.append(gtk.SeparatorMenuItem())
            # Single item, add episode information menu item
            item = gtk.ImageMenuItem(_('Episode details'))
            item.set_image(gtk.image_new_from_stock( gtk.STOCK_INFO, gtk.ICON_SIZE_MENU))
            item.connect('activate', self.on_shownotes_selected_episodes)
            menu.append(item)

            menu.show_all()
            # Disable tooltips while we are showing the menu, so
            # the tooltip will not appear over the menu
            self.treeview_allow_tooltips(self.treeAvailable, False)
            menu.connect('deactivate', lambda menushell: self.treeview_allow_tooltips(self.treeAvailable, True))
            if event is None:
                func = TreeViewHelper.make_popup_position_func(treeview)
                menu.popup(None, None, func, 3, 0)
            else:
                menu.popup(None, None, None, event.button, event.time)

            return True

    def set_title(self, new_title):
        self.default_title = new_title
        self.gPodder.set_title(new_title)

    def update_episode_list_icons(self, urls=None, selected=False, all=False):
        """
        Updates the status icons in the episode list.

        If urls is given, it should be a list of URLs
        of episodes that should be updated.

        If urls is None, set ONE OF selected, all to
        True (the former updates just the selected
        episodes and the latter updates all episodes).
        """
        descriptions = self.config.episode_list_descriptions

        if urls is not None:
            # We have a list of URLs to walk through
            self.episode_list_model.update_by_urls(urls, descriptions)
        elif selected and not all:
            # We should update all selected episodes
            selection = self.treeAvailable.get_selection()
            model, paths = selection.get_selected_rows()
            for path in reversed(paths):
                iter = model.get_iter(path)
                self.episode_list_model.update_by_filter_iter(iter, descriptions)
        elif all and not selected:
            # We update all (even the filter-hidden) episodes
            self.episode_list_model.update_all(descriptions)
        else:
            # Wrong/invalid call - have to specify at least one parameter
            raise ValueError('Invalid call to update_episode_list_icons')

    def episode_list_status_changed(self, episodes):
        self.update_episode_list_icons(set(e.url for e in episodes))
        self.update_podcast_list_model(set(e.channel.url for e in episodes))
        self.db.commit()

    def streaming_possible(self):
        # User has to have a media player set on the Desktop, or else we
        # would probably open the browser when giving a URL to xdg-open..
        return (self.config.player and self.config.player != 'default')

    def playback_episodes_for_real(self, episodes):
        groups = collections.defaultdict(list)
        for episode in episodes:
            file_type = episode.file_type()
            if file_type == 'video' and self.config.videoplayer and \
                    self.config.videoplayer != 'default':
                player = self.config.videoplayer
            elif file_type == 'audio' and self.config.player and \
                    self.config.player != 'default':
                player = self.config.player
            else:
                player = 'default'

            # Mark episode as played in the database
            episode.playback_mark()
            self.mygpo_client.on_playback([episode])

            fmt_ids = youtube.get_fmt_ids(self.config.youtube)
            vimeo_fmt = self.config.vimeo.fileformat

            allow_partial = (player != 'default')
            filename = episode.get_playback_url(fmt_ids, vimeo_fmt, allow_partial)

            # Determine the playback resume position - if the file
            # was played 100%, we simply start from the beginning
            resume_position = episode.current_position
            if resume_position == episode.total_time:
                resume_position = 0

            # If Panucci is configured, use D-Bus to call it
            if player == 'panucci':
                try:
                    PANUCCI_NAME = 'org.panucci.panucciInterface'
                    PANUCCI_PATH = '/panucciInterface'
                    PANUCCI_INTF = 'org.panucci.panucciInterface'
                    o = gpodder.dbus_session_bus.get_object(PANUCCI_NAME, PANUCCI_PATH)
                    i = dbus.Interface(o, PANUCCI_INTF)

                    def on_reply(*args):
                        pass

                    def error_handler(filename, err):
                        logger.error('Exception in D-Bus call: %s', str(err))

                        # Fallback: use the command line client
                        for command in util.format_desktop_command('panucci', \
                                [filename]):
                            logger.info('Executing: %s', repr(command))
                            subprocess.Popen(command)

                    on_error = lambda err: error_handler(filename, err)

                    # This method only exists in Panucci > 0.9 ('new Panucci')
                    i.playback_from(filename, resume_position, \
                            reply_handler=on_reply, error_handler=on_error)

                    continue # This file was handled by the D-Bus call
                except Exception, e:
                    logger.error('Calling Panucci using D-Bus', exc_info=True)

            groups[player].append(filename)

        # Open episodes with system default player
        if 'default' in groups:
            for filename in groups['default']:
                logger.debug('Opening with system default: %s', filename)
                util.gui_open(filename)
            del groups['default']

        # For each type now, go and create play commands
        for group in groups:
            for command in util.format_desktop_command(group, groups[group], resume_position):
                logger.debug('Executing: %s', repr(command))
                subprocess.Popen(command)

        # Persist episode status changes to the database
        self.db.commit()

        # Flush updated episode status
        if self.mygpo_client.can_access_webservice():
            self.mygpo_client.flush()

    def playback_episodes(self, episodes):
        # We need to create a list, because we run through it more than once
        episodes = list(Model.sort_episodes_by_pubdate(e for e in episodes if \
               e.was_downloaded(and_exists=True) or self.streaming_possible()))

        try:
            self.playback_episodes_for_real(episodes)
        except Exception, e:
            logger.error('Error in playback!', exc_info=True)
            self.show_message(_('Please check your media player settings in the preferences dialog.'), \
                    _('Error opening player'), widget=self.toolPreferences)

        self.episode_list_status_changed(episodes)

    def play_or_download(self):
        if self.wNotebook.get_current_page() > 0:
            self.toolCancel.set_sensitive(True)
            return (False, False, False, False, False, False)

        ( can_play, can_download, can_cancel, can_delete ) = (False,)*4
        ( is_played, is_locked ) = (False,)*2

        open_instead_of_play = False

        selection = self.treeAvailable.get_selection()
        if selection.count_selected_rows() > 0:
            (model, paths) = selection.get_selected_rows()

            for path in paths:
                try:
                    episode = model.get_value(model.get_iter(path), EpisodeListModel.C_EPISODE)
                except TypeError, te:
                    logger.error('Invalid episode at path %s', str(path))
                    continue

                if episode.file_type() not in ('audio', 'video'):
                    open_instead_of_play = True

                if episode.was_downloaded():
                    can_play = episode.was_downloaded(and_exists=True)
                    is_played = not episode.is_new
                    is_locked = episode.archive
                    if not can_play:
                        can_download = True
                else:
                    if episode.downloading:
                        can_cancel = True
                    else:
                        can_download = True

            can_download = can_download and not can_cancel
            can_play = self.streaming_possible() or (can_play and not can_cancel and not can_download)
            can_delete = not can_cancel

        if open_instead_of_play:
            self.toolPlay.set_stock_id(gtk.STOCK_OPEN)
        else:
            self.toolPlay.set_stock_id(gtk.STOCK_MEDIA_PLAY)
        self.toolPlay.set_sensitive( can_play)
        self.toolDownload.set_sensitive( can_download)
        self.toolCancel.set_sensitive( can_cancel)

        self.item_cancel_download.set_sensitive(can_cancel)
        self.itemDownloadSelected.set_sensitive(can_download)
        self.itemOpenSelected.set_sensitive(can_play)
        self.itemPlaySelected.set_sensitive(can_play)
        self.itemDeleteSelected.set_sensitive(can_delete)
        self.item_toggle_played.set_sensitive(can_play)
        self.item_toggle_lock.set_sensitive(can_play)
        self.itemOpenSelected.set_visible(open_instead_of_play)
        self.itemPlaySelected.set_visible(not open_instead_of_play)

        return (can_play, can_download, can_cancel, can_delete, open_instead_of_play)

    def on_cbMaxDownloads_toggled(self, widget, *args):
        self.spinMaxDownloads.set_sensitive(self.cbMaxDownloads.get_active())

    def on_cbLimitDownloads_toggled(self, widget, *args):
        self.spinLimitDownloads.set_sensitive(self.cbLimitDownloads.get_active())

    def episode_new_status_changed(self, urls):
        self.update_podcast_list_model()
        self.update_episode_list_icons(urls)

    def update_podcast_list_model(self, urls=None, selected=False, select_url=None,
            sections_changed=False):
        """Update the podcast list treeview model

        If urls is given, it should list the URLs of each
        podcast that has to be updated in the list.

        If selected is True, only update the model contents
        for the currently-selected podcast - nothing more.

        The caller can optionally specify "select_url",
        which is the URL of the podcast that is to be
        selected in the list after the update is complete.
        This only works if the podcast list has to be
        reloaded; i.e. something has been added or removed
        since the last update of the podcast list).
        """
        selection = self.treeChannels.get_selection()
        model, iter = selection.get_selected()

        is_section = lambda r: r[PodcastListModel.C_URL] == '-'
        is_separator = lambda r: r[PodcastListModel.C_SEPARATOR]
        sections_active = any(is_section(x) for x in self.podcast_list_model)

        if self.config.podcast_list_view_all:
            # Update "all episodes" view in any case (if enabled)
            self.podcast_list_model.update_first_row()
            # List model length minus 1, because of "All"
            list_model_length = len(self.podcast_list_model) - 1
        else:
            list_model_length = len(self.podcast_list_model)

        force_update = (sections_active != self.config.podcast_list_sections or
                sections_changed)

        # Filter items in the list model that are not podcasts, so we get the
        # correct podcast list count (ignore section headers and separators)
        is_not_podcast = lambda r: is_section(r) or is_separator(r)
        list_model_length -= len(filter(is_not_podcast, self.podcast_list_model))

        if selected and not force_update:
            # very cheap! only update selected channel
            if iter is not None:
                # If we have selected the "all episodes" view, we have
                # to update all channels for selected episodes:
                if self.config.podcast_list_view_all and \
                        self.podcast_list_model.iter_is_first_row(iter):
                    urls = self.get_podcast_urls_from_selected_episodes()
                    self.podcast_list_model.update_by_urls(urls)
                else:
                    # Otherwise just update the selected row (a podcast)
                    self.podcast_list_model.update_by_filter_iter(iter)

                if self.config.podcast_list_sections:
                    self.podcast_list_model.update_sections()
        elif list_model_length == len(self.channels) and not force_update:
            # we can keep the model, but have to update some
            if urls is None:
                # still cheaper than reloading the whole list
                self.podcast_list_model.update_all()
            else:
                # ok, we got a bunch of urls to update
                self.podcast_list_model.update_by_urls(urls)
                if self.config.podcast_list_sections:
                    self.podcast_list_model.update_sections()
        else:
            if model and iter and select_url is None:
                # Get the URL of the currently-selected podcast
                select_url = model.get_value(iter, PodcastListModel.C_URL)

            # Update the podcast list model with new channels
            self.podcast_list_model.set_channels(self.db, self.config, self.channels)

            try:
                selected_iter = model.get_iter_first()
                # Find the previously-selected URL in the new
                # model if we have an URL (else select first)
                if select_url is not None:
                    pos = model.get_iter_first()
                    while pos is not None:
                        url = model.get_value(pos, PodcastListModel.C_URL)
                        if url == select_url:
                            selected_iter = pos
                            break
                        pos = model.iter_next(pos)

                if selected_iter is not None:
                    selection.select_iter(selected_iter)
                self.on_treeChannels_cursor_changed(self.treeChannels)
            except:
                logger.error('Cannot select podcast in list', exc_info=True)

    def on_episode_list_filter_changed(self, has_episodes):
        self.play_or_download()

    def update_episode_list_model(self):
        if self.channels and self.active_channel is not None:
            self.treeAvailable.get_selection().unselect_all()
            self.treeAvailable.scroll_to_point(0, 0)

            descriptions = self.config.episode_list_descriptions
            self.episode_list_model.replace_from_channel(self.active_channel, descriptions)
        else:
            self.episode_list_model.clear()

    @dbus.service.method(gpodder.dbus_interface)
    def offer_new_episodes(self, channels=None):
        new_episodes = self.get_new_episodes(channels)
        if new_episodes:
            self.new_episodes_show(new_episodes)
            return True
        return False

    def add_podcast_list(self, podcasts, auth_tokens=None):
        """Subscribe to a list of podcast given (title, url) pairs

        If auth_tokens is given, it should be a dictionary
        mapping URLs to (username, password) tuples."""

        if auth_tokens is None:
            auth_tokens = {}

        existing_urls = set(podcast.url for podcast in self.channels)

        # For a given URL, the desired title (or None)
        title_for_url = {}

        # Sort and split the URL list into five buckets
        queued, failed, existing, worked, authreq = [], [], [], [], []
        for input_title, input_url in podcasts:
            url = util.normalize_feed_url(input_url)

            # Check if it's a YouTube feed, and if we have an API key, auto-resolve the channel
            url = youtube.resolve_v3_url(url, self.config.youtube.api_key_v3)

            if url is None:
                # Fail this one because the URL is not valid
                failed.append(input_url)
            elif url in existing_urls:
                # A podcast already exists in the list for this URL
                existing.append(url)
                # XXX: Should we try to update the title of the existing
                # subscription from input_title here if it is different?
            else:
                # This URL has survived the first round - queue for add
                title_for_url[url] = input_title
                queued.append(url)
                if url != input_url and input_url in auth_tokens:
                    auth_tokens[url] = auth_tokens[input_url]

        error_messages = {}
        redirections = {}

        progress = ProgressIndicator(_('Adding podcasts'), \
                _('Please wait while episode information is downloaded.'), \
                parent=self.get_dialog_parent())

        def on_after_update():
            progress.on_finished()
            # Report already-existing subscriptions to the user
            if existing:
                title = _('Existing subscriptions skipped')
                message = _('You are already subscribed to these podcasts:') \
                     + '\n\n' + '\n'.join(cgi.escape(url) for url in existing)
                self.show_message(message, title, widget=self.treeChannels)

            # Report subscriptions that require authentication
            retry_podcasts = {}
            if authreq:
                for url in authreq:
                    title = _('Podcast requires authentication')
                    message = _('Please login to %s:') % (cgi.escape(url),)
                    success, auth_tokens = self.show_login_dialog(title, message)
                    if success:
                        retry_podcasts[url] = auth_tokens
                    else:
                        # Stop asking the user for more login data
                        retry_podcasts = {}
                        for url in authreq:
                            error_messages[url] = _('Authentication failed')
                            failed.append(url)
                        break

            # Report website redirections
            for url in redirections:
                title = _('Website redirection detected')
                message = _('The URL %(url)s redirects to %(target)s.') \
                        + '\n\n' + _('Do you want to visit the website now?')
                message = message % {'url': url, 'target': redirections[url]}
                if self.show_confirmation(message, title):
                    util.open_website(url)
                else:
                    break

            # Report failed subscriptions to the user
            if failed:
                title = _('Could not add some podcasts')
                message = _('Some podcasts could not be added to your list:') \
                     + '\n\n' + '\n'.join(cgi.escape('%s: %s' % (url, \
                        error_messages.get(url, _('Unknown')))) for url in failed)
                self.show_message(message, title, important=True)

            # Upload subscription changes to gpodder.net
            self.mygpo_client.on_subscribe(worked)

            # Fix URLs if mygpo has rewritten them
            self.rewrite_urls_mygpo()

            # If only one podcast was added, select it after the update
            if len(worked) == 1:
                url = worked[0]
            else:
                url = None

            # Update the list of subscribed podcasts
            self.update_podcast_list_model(select_url=url)

            # If we have authentication data to retry, do so here
            if retry_podcasts:
                podcasts = [(title_for_url.get(url), url)
                        for url in retry_podcasts.keys()]
                self.add_podcast_list(podcasts, retry_podcasts)
                # This will NOT show new episodes for podcasts that have
                # been added ("worked"), but it will prevent problems with
                # multiple dialogs being open at the same time ;)
                return

            # Offer to download new episodes
            episodes = []
            for podcast in self.channels:
                if podcast.url in worked:
                    episodes.extend(podcast.get_all_episodes())

            if episodes:
                episodes = list(Model.sort_episodes_by_pubdate(episodes, \
                        reverse=True))
                self.new_episodes_show(episodes, \
                        selected=[e.check_is_new() for e in episodes])


        @util.run_in_background
        def thread_proc():
            # After the initial sorting and splitting, try all queued podcasts
            length = len(queued)
            for index, url in enumerate(queued):
                title = title_for_url.get(url)
                progress.on_progress(float(index)/float(length))
                progress.on_message(title or url)
                try:
                    # The URL is valid and does not exist already - subscribe!
                    channel = self.model.load_podcast(url=url, create=True, \
                            authentication_tokens=auth_tokens.get(url, None), \
                            max_episodes=self.config.max_episodes_per_feed)

                    try:
                        username, password = util.username_password_from_url(url)
                    except ValueError, ve:
                        username, password = (None, None)

                    if title is not None:
                        # Prefer title from subscription source (bug 1711)
                        channel.title = title

                    if username is not None and channel.auth_username is None and \
                            password is not None and channel.auth_password is None:
                        channel.auth_username = username
                        channel.auth_password = password

                    channel.save()

                    self._update_cover(channel)
                except feedcore.AuthenticationRequired:
                    if url in auth_tokens:
                        # Fail for wrong authentication data
                        error_messages[url] = _('Authentication failed')
                        failed.append(url)
                    else:
                        # Queue for login dialog later
                        authreq.append(url)
                    continue
                except feedcore.WifiLogin, error:
                    redirections[url] = error.data
                    failed.append(url)
                    error_messages[url] = _('Redirection detected')
                    continue
                except Exception, e:
                    logger.error('Subscription error: %s', e, exc_info=True)
                    error_messages[url] = str(e)
                    failed.append(url)
                    continue

                assert channel is not None
                worked.append(channel.url)

            util.idle_add(on_after_update)

    def find_episode(self, podcast_url, episode_url):
        """Find an episode given its podcast and episode URL

        The function will return a PodcastEpisode object if
        the episode is found, or None if it's not found.
        """
        for podcast in self.channels:
            if podcast_url == podcast.url:
                for episode in podcast.get_all_episodes():
                    if episode_url == episode.url:
                        return episode

        return None

    def process_received_episode_actions(self):
        """Process/merge episode actions from gpodder.net

        This function will merge all changes received from
        the server to the local database and update the
        status of the affected episodes as necessary.
        """
        indicator = ProgressIndicator(_('Merging episode actions'), \
                _('Episode actions from gpodder.net are merged.'), \
                False, self.get_dialog_parent())

        while gtk.events_pending():
            gtk.main_iteration(False)

        self.mygpo_client.process_episode_actions(self.find_episode)

        indicator.on_finished()
        self.db.commit()

    def _update_cover(self, channel):
        if channel is not None:
            self.cover_downloader.request_cover(channel)

    def show_update_feeds_buttons(self):
        # Make sure that the buttons for updating feeds
        # appear - this should happen after a feed update
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

    def update_feed_cache(self, channels=None,
                          show_new_episodes_dialog=True):
        if not util.connection_available():
            self.show_message(_('Please connect to a network, then try again.'),
                    _('No network connection'), important=True)
            return

        # Fix URLs if mygpo has rewritten them
        self.rewrite_urls_mygpo()

        if channels is None:
            # Only update podcasts for which updates are enabled
            channels = [c for c in self.channels if not c.pause_subscription]

        self.itemUpdate.set_sensitive(False)
        self.itemUpdateChannel.set_sensitive(False)

        self.feed_cache_update_cancelled = False
        self.btnCancelFeedUpdate.show()
        self.btnCancelFeedUpdate.set_sensitive(True)
        self.btnCancelFeedUpdate.set_image(gtk.image_new_from_stock(gtk.STOCK_STOP, gtk.ICON_SIZE_BUTTON))
        self.hboxUpdateFeeds.show_all()
        self.btnUpdateFeeds.hide()

        count = len(channels)
        text = N_('Updating %(count)d feed...', 'Updating %(count)d feeds...', count) % {'count':count}

        self.pbFeedUpdate.set_text(text)
        self.pbFeedUpdate.set_fraction(0)

        @util.run_in_background
        def update_feed_cache_proc():
            updated_channels = []
            for updated, channel in enumerate(channels):
                if self.feed_cache_update_cancelled:
                    break

                try:
                    channel.update(max_episodes=self.config.max_episodes_per_feed)
                    self._update_cover(channel)
                except Exception, e:
                    d = {'url': cgi.escape(channel.url), 'message': cgi.escape(str(e))}
                    if d['message']:
                        message = _('Error while updating %(url)s: %(message)s')
                    else:
                        message = _('The feed at %(url)s could not be updated.')
                    self.notification(message % d, _('Error while updating feed'), widget=self.treeChannels)
                    logger.error('Error: %s', str(e), exc_info=True)

                updated_channels.append(channel)

                def update_progress(channel):
                    self.update_podcast_list_model([channel.url])

                    # If the currently-viewed podcast is updated, reload episodes
                    if self.active_channel is not None and \
                            self.active_channel == channel:
                        logger.debug('Updated channel is active, updating UI')
                        self.update_episode_list_model()

                    d = {'podcast': channel.title, 'position': updated+1, 'total': count}
                    progression = _('Updated %(podcast)s (%(position)d/%(total)d)') % d

                    self.pbFeedUpdate.set_text(progression)
                    self.pbFeedUpdate.set_fraction(float(updated+1)/float(count))

                util.idle_add(update_progress, channel)

            def update_feed_cache_finish_callback():
                # Process received episode actions for all updated URLs
                self.process_received_episode_actions()

                # If we are currently viewing "All episodes", update its episode list now
                if self.active_channel is not None and \
                        getattr(self.active_channel, 'ALL_EPISODES_PROXY', False):
                    self.update_episode_list_model()

                if self.feed_cache_update_cancelled:
                    # The user decided to abort the feed update
                    self.show_update_feeds_buttons()

                # Only search for new episodes in podcasts that have been
                # updated, not in other podcasts (for single-feed updates)
                episodes = self.get_new_episodes([c for c in updated_channels])

                if self.config.downloads.chronological_order:
                    # download older episodes first
                    episodes = list(Model.sort_episodes_by_pubdate(episodes))

                if not episodes:
                    # Nothing new here - but inform the user
                    self.pbFeedUpdate.set_fraction(1.0)
                    self.pbFeedUpdate.set_text(_('No new episodes'))
                    self.feed_cache_update_cancelled = True
                    self.btnCancelFeedUpdate.show()
                    self.btnCancelFeedUpdate.set_sensitive(True)
                    self.itemUpdate.set_sensitive(True)
                    self.btnCancelFeedUpdate.set_image(gtk.image_new_from_stock(gtk.STOCK_APPLY, gtk.ICON_SIZE_BUTTON))
                else:
                    count = len(episodes)
                    # New episodes are available
                    self.pbFeedUpdate.set_fraction(1.0)

                    if self.config.auto_download == 'download':
                        self.download_episode_list(episodes)
                        title = N_('Downloading %(count)d new episode.', 'Downloading %(count)d new episodes.', count) % {'count':count}
                        self.show_message(title, _('New episodes available'), widget=self.labelDownloads)
                    elif self.config.auto_download == 'queue':
                        self.download_episode_list_paused(episodes)
                        title = N_('%(count)d new episode added to download list.', '%(count)d new episodes added to download list.', count) % {'count':count}
                        self.show_message(title, _('New episodes available'), widget=self.labelDownloads)
                    else:
                        if (show_new_episodes_dialog and
                                self.config.auto_download == 'show'):
                            self.new_episodes_show(episodes, notification=True)
                        else: # !show_new_episodes_dialog or auto_download == 'ignore'
                            message = N_('%(count)d new episode available', '%(count)d new episodes available', count) % {'count':count}
                            self.pbFeedUpdate.set_text(message)

                    self.show_update_feeds_buttons()

            util.idle_add(update_feed_cache_finish_callback)

    def on_gPodder_delete_event(self, widget, *args):
        """Called when the GUI wants to close the window
        Displays a confirmation dialog (and closes/hides gPodder)
        """

        downloading = self.download_status_model.are_downloads_in_progress()

        if downloading:
            dialog = gtk.MessageDialog(self.gPodder, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_NONE)
            dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
            quit_button = dialog.add_button(gtk.STOCK_QUIT, gtk.RESPONSE_CLOSE)

            title = _('Quit gPodder')
            message = _('You are downloading episodes. You can resume downloads the next time you start gPodder. Do you want to quit now?')

            dialog.set_title(title)
            dialog.set_markup('<span weight="bold" size="larger">%s</span>\n\n%s'%(title, message))

            quit_button.grab_focus()
            result = dialog.run()
            dialog.destroy()

            if result == gtk.RESPONSE_CLOSE:
                self.close_gpodder()
        else:
            self.close_gpodder()

        return True

    def quit_cb(self, macapp):
        """Called when OSX wants to quit the app (Cmd-Q or gPodder > Quit)
        """
        # Event can't really be cancelled - don't even try
        self.close_gpodder()
        return False

    def close_gpodder(self):
        """ clean everything and exit properly
        """
        # Cancel any running background updates of the episode list model
        self.episode_list_model.background_update = None

        self.gPodder.hide()

        # Notify all tasks to to carry out any clean-up actions
        self.download_status_model.tell_all_tasks_to_quit()

        while gtk.events_pending():
            gtk.main_iteration(False)

        self.core.shutdown()

        self.quit()

    def delete_episode_list(self, episodes, confirm=True, skip_locked=True,
            callback=None):
        if not episodes:
            return False

        if skip_locked:
            episodes = [e for e in episodes if not e.archive]

            if not episodes:
                title = _('Episodes are locked')
                message = _('The selected episodes are locked. Please unlock the episodes that you want to delete before trying to delete them.')
                self.notification(message, title, widget=self.treeAvailable)
                return False

        count = len(episodes)
        title = N_('Delete %(count)d episode?', 'Delete %(count)d episodes?', count) % {'count':count}
        message = _('Deleting episodes removes downloaded files.')

        if confirm and not self.show_confirmation(message, title):
            return False

        progress = ProgressIndicator(_('Deleting episodes'), \
                _('Please wait while episodes are deleted'), \
                parent=self.get_dialog_parent())

        def finish_deletion(episode_urls, channel_urls):
            progress.on_finished()

            # Episodes have been deleted - persist the database
            self.db.commit()

            self.update_episode_list_icons(episode_urls)
            self.update_podcast_list_model(channel_urls)
            self.play_or_download()

        @util.run_in_background
        def thread_proc():
            episode_urls = set()
            channel_urls = set()

            episodes_status_update = []
            for idx, episode in enumerate(episodes):
                progress.on_progress(float(idx)/float(len(episodes)))
                if not episode.archive or not skip_locked:
                    progress.on_message(episode.title)
                    episode.delete_from_disk()
                    episode_urls.add(episode.url)
                    channel_urls.add(episode.channel.url)
                    episodes_status_update.append(episode)

            # Notify the web service about the status update + upload
            if self.mygpo_client.can_access_webservice():
                self.mygpo_client.on_delete(episodes_status_update)
                self.mygpo_client.flush()

            if callback is None:
                util.idle_add(finish_deletion, episode_urls, channel_urls)
            else:
                util.idle_add(callback, episode_urls, channel_urls, progress)

        return True

    def on_itemRemoveOldEpisodes_activate(self, widget):
        self.show_delete_episodes_window()

    def show_delete_episodes_window(self, channel=None):
        """Offer deletion of episodes

        If channel is None, offer deletion of all episodes.
        Otherwise only offer deletion of episodes in the channel.
        """
        columns = (
            ('markup_delete_episodes', None, None, _('Episode')),
        )

        msg_older_than = N_('Select older than %(count)d day', 'Select older than %(count)d days', self.config.episode_old_age)
        selection_buttons = {
                _('Select played'): lambda episode: not episode.is_new,
                _('Select finished'): lambda episode: episode.is_finished(),
                msg_older_than % {'count':self.config.episode_old_age}: lambda episode: episode.age_in_days() > self.config.episode_old_age,
        }

        instructions = _('Select the episodes you want to delete:')

        if channel is None:
            channels = self.channels
        else:
            channels = [channel]

        episodes = []
        for channel in channels:
            for episode in channel.get_episodes(gpodder.STATE_DOWNLOADED):
                # Disallow deletion of locked episodes that still exist
                if not episode.archive or not episode.file_exists():
                    episodes.append(episode)

        selected = [not e.is_new or not e.file_exists() for e in episodes]

        gPodderEpisodeSelector(self.gPodder, title = _('Delete episodes'), instructions = instructions, \
                                episodes = episodes, selected = selected, columns = columns, \
                                stock_ok_button = gtk.STOCK_DELETE, callback = self.delete_episode_list, \
                                selection_buttons = selection_buttons, _config=self.config)

    def on_selected_episodes_status_changed(self):
        # The order of the updates here is important! When "All episodes" is
        # selected, the update of the podcast list model depends on the episode
        # list selection to determine which podcasts are affected. Updating
        # the episode list could remove the selection if a filter is active.
        self.update_podcast_list_model(selected=True)
        self.update_episode_list_icons(selected=True)
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
                episode.mark(is_played=episode.is_new)
            else:
                episode.mark(is_played=new_value)
        self.on_selected_episodes_status_changed()

    def on_item_toggle_lock_activate(self, widget, toggle=True, new_value=False):
        for episode in self.get_selected_episodes():
            if toggle:
                episode.mark(is_locked=not episode.archive)
            else:
                episode.mark(is_locked=new_value)
        self.on_selected_episodes_status_changed()

    def on_channel_toggle_lock_activate(self, widget, toggle=True, new_value=False):
        if self.active_channel is None:
            return

        self.active_channel.auto_archive_episodes = not self.active_channel.auto_archive_episodes
        self.active_channel.save()

        for episode in self.active_channel.get_all_episodes():
            episode.mark(is_locked=self.active_channel.auto_archive_episodes)

        self.update_podcast_list_model(selected=True)
        self.update_episode_list_icons(all=True)

    def on_itemUpdateChannel_activate(self, widget=None):
        if self.active_channel is None:
            title = _('No podcast selected')
            message = _('Please select a podcast in the podcasts list to update.')
            self.show_message( message, title, widget=self.treeChannels)
            return

        # Dirty hack to check for "All episodes" (see gpodder.gtkui.model)
        if getattr(self.active_channel, 'ALL_EPISODES_PROXY', False):
            self.update_feed_cache()
        else:
            self.update_feed_cache(channels=[self.active_channel])

    def on_itemUpdate_activate(self, widget=None):
        # Check if we have outstanding subscribe/unsubscribe actions
        self.on_add_remove_podcasts_mygpo()

        if self.channels:
            self.update_feed_cache()
        else:
            def show_welcome_window():
                def on_show_example_podcasts(widget):
                    welcome_window.main_window.response(gtk.RESPONSE_CANCEL)
                    self.on_itemImportChannels_activate(None)

                def on_add_podcast_via_url(widget):
                    welcome_window.main_window.response(gtk.RESPONSE_CANCEL)
                    self.on_itemAddChannel_activate(None)

                def on_setup_my_gpodder(widget):
                    welcome_window.main_window.response(gtk.RESPONSE_CANCEL)
                    self.on_download_subscriptions_from_mygpo(None)

                welcome_window = gPodderWelcome(self.main_window,
                        center_on_widget=self.main_window,
                        on_show_example_podcasts=on_show_example_podcasts,
                        on_add_podcast_via_url=on_add_podcast_via_url,
                        on_setup_my_gpodder=on_setup_my_gpodder)

                welcome_window.main_window.run()
                welcome_window.main_window.destroy()

            util.idle_add(show_welcome_window)

    def download_episode_list_paused(self, episodes):
        self.download_episode_list(episodes, True)

    def download_episode_list(self, episodes, add_paused=False, force_start=False):
        enable_update = False

        if self.config.downloads.chronological_order:
            # Download episodes in chronological order (older episodes first)
            episodes = list(Model.sort_episodes_by_pubdate(episodes))

        for episode in episodes:
            logger.debug('Downloading episode: %s', episode.title)
            if not episode.was_downloaded(and_exists=True):
                task_exists = False
                for task in self.download_tasks_seen:
                    if episode.url == task.url:
                        task_exists = True
                        if task.status not in (task.DOWNLOADING, task.QUEUED):
                            self.download_queue_manager.add_task(task, force_start)
                            enable_update = True
                            continue

                if task_exists:
                    continue

                try:
                    task = download.DownloadTask(episode, self.config)
                except Exception, e:
                    d = {'episode': episode.title, 'message': str(e)}
                    message = _('Download error while downloading %(episode)s: %(message)s')
                    self.show_message(message % d, _('Download error'), important=True)
                    logger.error('While downloading %s', episode.title, exc_info=True)
                    continue

                if add_paused:
                    task.status = task.PAUSED
                else:
                    self.mygpo_client.on_download([task.episode])
                    self.download_queue_manager.add_task(task, force_start)

                self.download_status_model.register_task(task)
                enable_update = True

        if enable_update:
            self.enable_download_list_update()

        # Flush updated episode status
        if self.mygpo_client.can_access_webservice():
            self.mygpo_client.flush()

    def cancel_task_list(self, tasks):
        if not tasks:
            return

        for task in tasks:
            if task.status in (task.QUEUED, task.DOWNLOADING):
                task.status = task.CANCELLED
            elif task.status == task.PAUSED:
                task.status = task.CANCELLED
                # Call run, so the partial file gets deleted
                task.run()

        self.update_episode_list_icons([task.url for task in tasks])
        self.play_or_download()

        # Update the tab title and downloads list
        self.update_downloads_list()

    def new_episodes_show(self, episodes, notification=False, selected=None):
        columns = (
            ('markup_new_episodes', None, None, _('Episode')),
        )

        instructions = _('Select the episodes you want to download:')

        if self.new_episodes_window is not None:
            self.new_episodes_window.main_window.destroy()
            self.new_episodes_window = None

        def download_episodes_callback(episodes):
            self.new_episodes_window = None
            self.download_episode_list(episodes)

        if selected is None:
            # Select all by default
            selected = [True]*len(episodes)

        self.new_episodes_window = gPodderEpisodeSelector(self.gPodder, \
                title=_('New episodes available'), \
                instructions=instructions, \
                episodes=episodes, \
                columns=columns, \
                selected=selected, \
                stock_ok_button = 'gpodder-download', \
                callback=download_episodes_callback, \
                remove_callback=lambda e: e.mark_old(), \
                remove_action=_('Mark as old'), \
                remove_finished=self.episode_new_status_changed, \
                _config=self.config, \
                show_notification=False)

    def on_itemDownloadAllNew_activate(self, widget, *args):
        if not self.offer_new_episodes():
            self.show_message(_('Please check for new episodes later.'), \
                    _('No new episodes available'), widget=self.btnUpdateFeeds)

    def get_new_episodes(self, channels=None):
        return [e for c in channels or self.channels for e in
                filter(lambda e: e.check_is_new(), c.get_all_episodes())]

    def commit_changes_to_database(self):
        """This will be called after the sync process is finished"""
        self.db.commit()

    def on_itemShowToolbar_activate(self, widget):
        self.config.show_toolbar = self.itemShowToolbar.get_active()

    def on_itemShowDescription_activate(self, widget):
        self.config.episode_list_descriptions = self.itemShowDescription.get_active()

    def on_item_view_hide_boring_podcasts_toggled(self, toggleaction):
        self.config.podcast_list_hide_boring = toggleaction.get_active()
        if self.config.podcast_list_hide_boring:
            self.podcast_list_model.set_view_mode(self.config.episode_list_view_mode)
        else:
            self.podcast_list_model.set_view_mode(-1)

    def on_item_view_episodes_changed(self, radioaction, current):
        if current == self.item_view_episodes_all:
            self.config.episode_list_view_mode = EpisodeListModel.VIEW_ALL
        elif current == self.item_view_episodes_undeleted:
            self.config.episode_list_view_mode = EpisodeListModel.VIEW_UNDELETED
        elif current == self.item_view_episodes_downloaded:
            self.config.episode_list_view_mode = EpisodeListModel.VIEW_DOWNLOADED
        elif current == self.item_view_episodes_unplayed:
            self.config.episode_list_view_mode = EpisodeListModel.VIEW_UNPLAYED

        self.episode_list_model.set_view_mode(self.config.episode_list_view_mode)

        if self.config.podcast_list_hide_boring:
            self.podcast_list_model.set_view_mode(self.config.episode_list_view_mode)

    def on_itemPreferences_activate(self, widget, *args):
        gPodderPreferences(self.main_window, \
                _config=self.config, \
                user_apps_reader=self.user_apps_reader, \
                parent_window=self.main_window, \
                mygpo_client=self.mygpo_client, \
                on_send_full_subscriptions=self.on_send_full_subscriptions, \
                on_itemExportChannels_activate=self.on_itemExportChannels_activate)

    def on_goto_mygpo(self, widget):
        self.mygpo_client.open_website()

    def on_download_subscriptions_from_mygpo(self, action=None):
        title = _('Login to gpodder.net')
        message = _('Please login to download your subscriptions.')

        def on_register_button_clicked():
            util.open_website('http://gpodder.net/register/')

        success, (username, password) = self.show_login_dialog(title, message,
                self.config.mygpo.username, self.config.mygpo.password,
                register_callback=on_register_button_clicked)
        if not success:
            return

        self.config.mygpo.username = username
        self.config.mygpo.password = password

        dir = gPodderPodcastDirectory(self.gPodder, _config=self.config, \
                custom_title=_('Subscriptions on gpodder.net'), \
                add_podcast_list=self.add_podcast_list,
                hide_url_entry=True)

        # TODO: Refactor this into "gpodder.my" or mygpoclient, so that
        #       we do not have to hardcode the URL here
        OPML_URL = 'http://gpodder.net/subscriptions/%s.opml' % self.config.mygpo.username
        url = util.url_add_authentication(OPML_URL, \
                self.config.mygpo.username, \
                self.config.mygpo.password)
        dir.download_opml_file(url)

    def on_itemAddChannel_activate(self, widget=None):
        self._add_podcast_dialog = gPodderAddPodcast(self.gPodder, \
                add_podcast_list=self.add_podcast_list)

    def on_itemEditChannel_activate(self, widget, *args):
        if self.active_channel is None:
            title = _('No podcast selected')
            message = _('Please select a podcast in the podcasts list to edit.')
            self.show_message( message, title, widget=self.treeChannels)
            return

        gPodderChannel(self.main_window,
                channel=self.active_channel,
                update_podcast_list_model=self.update_podcast_list_model,
                cover_downloader=self.cover_downloader,
                sections=set(c.section for c in self.channels),
                clear_cover_cache=self.podcast_list_model.clear_cover_cache,
                _config=self.config)

    def on_itemMassUnsubscribe_activate(self, item=None):
        columns = (
            ('title', None, None, _('Podcast')),
        )

        # We're abusing the Episode Selector for selecting Podcasts here,
        # but it works and looks good, so why not? -- thp
        gPodderEpisodeSelector(self.main_window, \
                title=_('Remove podcasts'), \
                instructions=_('Select the podcast you want to remove.'), \
                episodes=self.channels, \
                columns=columns, \
                size_attribute=None, \
                stock_ok_button=_('Remove'), \
                callback=self.remove_podcast_list, \
                _config=self.config)

    def remove_podcast_list(self, channels, confirm=True):
        if not channels:
            return

        if len(channels) == 1:
            title = _('Removing podcast')
            info = _('Please wait while the podcast is removed')
            message = _('Do you really want to remove this podcast and its episodes?')
        else:
            title = _('Removing podcasts')
            info = _('Please wait while the podcasts are removed')
            message = _('Do you really want to remove the selected podcasts and their episodes?')

        if confirm and not self.show_confirmation(message, title):
            return

        progress = ProgressIndicator(title, info, parent=self.get_dialog_parent())

        def finish_deletion(select_url):
            # Upload subscription list changes to the web service
            self.mygpo_client.on_unsubscribe([c.url for c in channels])

            # Re-load the channels and select the desired new channel
            self.update_podcast_list_model(select_url=select_url)
            progress.on_finished()

        @util.run_in_background
        def thread_proc():
            select_url = None

            for idx, channel in enumerate(channels):
                # Update the UI for correct status messages
                progress.on_progress(float(idx)/float(len(channels)))
                progress.on_message(channel.title)

                # Delete downloaded episodes
                channel.remove_downloaded()

                # cancel any active downloads from this channel
                for episode in channel.get_all_episodes():
                    if episode.downloading:
                        episode.download_task.cancel()

                if len(channels) == 1:
                    # get the URL of the podcast we want to select next
                    if channel in self.channels:
                        position = self.channels.index(channel)
                    else:
                        position = -1

                    if position == len(self.channels)-1:
                        # this is the last podcast, so select the URL
                        # of the item before this one (i.e. the "new last")
                        select_url = self.channels[position-1].url
                    else:
                        # there is a podcast after the deleted one, so
                        # we simply select the one that comes after it
                        select_url = self.channels[position+1].url

                # Remove the channel and clean the database entries
                channel.delete()

            # Clean up downloads and download directories
            common.clean_up_downloads()

            # The remaining stuff is to be done in the GTK main thread
            util.idle_add(finish_deletion, select_url)

    def on_itemRemoveChannel_activate(self, widget, *args):
        if self.active_channel is None:
            title = _('No podcast selected')
            message = _('Please select a podcast in the podcasts list to remove.')
            self.show_message( message, title, widget=self.treeChannels)
            return

        self.remove_podcast_list([self.active_channel])

    def get_opml_filter(self):
        filter = gtk.FileFilter()
        filter.add_pattern('*.opml')
        filter.add_pattern('*.xml')
        filter.set_name(_('OPML files')+' (*.opml, *.xml)')
        return filter

    def on_item_import_from_file_activate(self, widget, filename=None):
        if filename is None:
            dlg = gtk.FileChooserDialog(title=_('Import from OPML'),
                    parent=self.main_window,
                    action=gtk.FILE_CHOOSER_ACTION_OPEN)
            dlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
            dlg.add_button(gtk.STOCK_OPEN, gtk.RESPONSE_OK)
            dlg.set_filter(self.get_opml_filter())
            response = dlg.run()
            filename = None
            if response == gtk.RESPONSE_OK:
                filename = dlg.get_filename()
            dlg.destroy()

        if filename is not None:
            dir = gPodderPodcastDirectory(self.gPodder, _config=self.config, \
                    custom_title=_('Import podcasts from OPML file'), \
                    add_podcast_list=self.add_podcast_list,
                    hide_url_entry=True)
            dir.download_opml_file(filename)

    def on_itemExportChannels_activate(self, widget, *args):
        if not self.channels:
            title = _('Nothing to export')
            message = _('Your list of podcast subscriptions is empty. Please subscribe to some podcasts first before trying to export your subscription list.')
            self.show_message(message, title, widget=self.treeChannels)
            return

        dlg = gtk.FileChooserDialog(title=_('Export to OPML'), parent=self.gPodder, action=gtk.FILE_CHOOSER_ACTION_SAVE)
        dlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dlg.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_OK)
        dlg.set_filter(self.get_opml_filter())
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            filename = dlg.get_filename()
            dlg.destroy()
            exporter = opml.Exporter( filename)
            if filename is not None and exporter.write(self.channels):
                count = len(self.channels)
                title = N_('%(count)d subscription exported', '%(count)d subscriptions exported', count) % {'count':count}
                self.show_message(_('Your podcast list has been successfully exported.'), title, widget=self.treeChannels)
            else:
                self.show_message( _('Could not export OPML to file. Please check your permissions.'), _('OPML export failed'), important=True)
        else:
            dlg.destroy()

    def on_itemImportChannels_activate(self, widget, *args):
        self._podcast_directory = gPodderPodcastDirectory(self.main_window,
                _config=self.config,
                add_podcast_list=self.add_podcast_list)

    def on_homepage_activate(self, widget, *args):
        util.open_website(gpodder.__url__)

    def on_wiki_activate(self, widget, *args):
        util.open_website('http://gpodder.org/wiki/User_Manual')

    def on_check_for_updates_activate(self, widget):
        self.check_for_updates(silent=False)

    def check_for_updates(self, silent):
        """Check for updates and (optionally) show a message

        If silent=False, a message will be shown even if no updates are
        available (set silent=False when the check is manually triggered).
        """
        try:
            up_to_date, version, released, days = util.get_update_info()
        except Exception as e:
            if silent:
                logger.warn('Could not check for updates.', exc_info=True)
            else:
                title = _('Could not check for updates')
                message = _('Please try again later.')
                self.show_message(message, title, important=True)
            return

        if up_to_date and not silent:
            title = _('No updates available')
            message = _('You have the latest version of gPodder.')
            self.show_message(message, title, important=True)

        if not up_to_date:
            title = _('New version available')
            message = '\n'.join([
                _('Installed version: %s') % gpodder.__version__,
                _('Newest version: %s') % version,
                _('Release date: %s') % released,
                '',
                _('Download the latest version from gpodder.org?'),
            ])

            if self.show_confirmation(message, title):
                util.open_website('http://gpodder.org/downloads')

    def on_bug_tracker_activate(self, widget, *args):
        util.open_website('https://github.com/gpodder/gpodder/issues')

    def on_item_support_activate(self, widget):
        util.open_website('http://gpodder.org/donate')

    def on_itemAbout_activate(self, widget, *args):
        dlg = gtk.Dialog(_('About gPodder'), self.main_window, \
                gtk.DIALOG_MODAL)
        dlg.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_OK).show()
        dlg.set_resizable(False)

        bg = gtk.HBox(spacing=6)
        pb = gtk.gdk.pixbuf_new_from_file_at_size(gpodder.icon_file, 160, 160)
        bg.pack_start(gtk.image_new_from_pixbuf(pb), expand=False)
        vb = gtk.VBox()
        vb.set_spacing(6)
        label = gtk.Label()
        label.set_alignment(0, 0.5)
        label.set_markup('\n'.join(x.strip() for x in """
        <b>gPodder {version} ({date})</b>
        <i>"{relname}"</i>

        {copyright}
        License: {license}

        <a href="{url}">Website</a> · <a href="{donate_url}">Donate</a> · <a href="{bugs_url}">Bug Tracker</a>
        """.format(version=gpodder.__version__,
                   date=gpodder.__date__,
                   relname=gpodder.__relname__,
                   copyright=gpodder.__copyright__,
                   license=gpodder.__license__,
                   donate_url='http://gpodder.org/donate',
                   bugs_url='https://github.com/gpodder/gpodder/issues',
                   url=cgi.escape(gpodder.__url__)).strip().split('\n')))

        vb.pack_start(label)
        bg.pack_start(vb)
        bg.pack_start(gtk.Label())

        dlg.vbox.pack_start(bg, expand=False)
        dlg.connect('response', lambda dlg, response: dlg.destroy())

        dlg.vbox.show_all()

        dlg.run()

    def on_wNotebook_switch_page(self, notebook, page, page_num):
        if page_num == 0:
            self.play_or_download()
            # The message area in the downloads tab should be hidden
            # when the user switches away from the downloads tab
            if self.message_area is not None:
                self.message_area.hide()
                self.message_area = None
        else:
            self.toolDownload.set_sensitive(False)
            self.toolPlay.set_sensitive(False)
            self.toolCancel.set_sensitive(False)

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

            # Dirty hack to check for "All episodes" (see gpodder.gtkui.model)
            if getattr(self.active_channel, 'ALL_EPISODES_PROXY', False):
                self.itemEditChannel.set_visible(False)
                self.itemRemoveChannel.set_visible(False)
            else:
                self.itemEditChannel.set_visible(True)
                self.itemRemoveChannel.set_visible(True)
        else:
            self.active_channel = None
            self.itemEditChannel.set_visible(False)
            self.itemRemoveChannel.set_visible(False)

        self.update_episode_list_model()

    def on_btnEditChannel_clicked(self, widget, *args):
        self.on_itemEditChannel_activate( widget, args)

    def get_podcast_urls_from_selected_episodes(self):
        """Get a set of podcast URLs based on the selected episodes"""
        return set(episode.channel.url for episode in \
                self.get_selected_episodes())

    def get_selected_episodes(self):
        """Get a list of selected episodes from treeAvailable"""
        selection = self.treeAvailable.get_selection()
        model, paths = selection.get_selected_rows()

        episodes = [model.get_value(model.get_iter(path), EpisodeListModel.C_EPISODE) for path in paths]
        return episodes

    def on_playback_selected_episodes(self, widget):
        self.playback_episodes(self.get_selected_episodes())

    def on_shownotes_selected_episodes(self, widget):
        episodes = self.get_selected_episodes()
        self.shownotes_object.toggle_pane_visibility(episodes)

    def on_download_selected_episodes(self, widget):
        episodes = self.get_selected_episodes()
        self.download_episode_list(episodes)
        self.update_episode_list_icons([episode.url for episode in episodes])
        self.play_or_download()

    def on_treeAvailable_row_activated(self, widget, path, view_column):
        """Double-click/enter action handler for treeAvailable"""
        self.on_shownotes_selected_episodes(widget)

    def restart_auto_update_timer(self):
        if self._auto_update_timer_source_id is not None:
            logger.debug('Removing existing auto update timer.')
            gobject.source_remove(self._auto_update_timer_source_id)
            self._auto_update_timer_source_id = None

        if self.config.auto_update_feeds and \
                self.config.auto_update_frequency:
            interval = 60*1000*self.config.auto_update_frequency
            logger.debug('Setting up auto update timer with interval %d.',
                    self.config.auto_update_frequency)
            self._auto_update_timer_source_id = gobject.timeout_add(\
                    interval, self._on_auto_update_timer)

    def _on_auto_update_timer(self):
        if not util.connection_available():
            logger.debug('Skipping auto update (no connection available)')
            return True

        logger.debug('Auto update timer fired.')
        self.update_feed_cache()

        # Ask web service for sub changes (if enabled)
        if self.mygpo_client.can_access_webservice():
            self.mygpo_client.flush()

        return True

    def on_treeDownloads_row_activated(self, widget, *args):
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

    def on_item_cancel_download_activate(self, widget):
        if self.wNotebook.get_current_page() == 0:
            selection = self.treeAvailable.get_selection()
            (model, paths) = selection.get_selected_rows()
            urls = [model.get_value(model.get_iter(path), \
                    self.episode_list_model.C_URL) for path in paths]
            selected_tasks = [task for task in self.download_tasks_seen \
                    if task.url in urls]
        else:
            selection = self.treeDownloads.get_selection()
            (model, paths) = selection.get_selected_rows()
            selected_tasks = [model.get_value(model.get_iter(path), \
                    self.download_status_model.C_TASK) for path in paths]
        self.cancel_task_list(selected_tasks)

    def on_btnCancelAll_clicked(self, widget, *args):
        self.cancel_task_list(self.download_tasks_seen)

    def on_btnDownloadedDelete_clicked(self, widget, *args):
        episodes = self.get_selected_episodes()
        if len(episodes) == 1:
            self.delete_episode_list(episodes, skip_locked=False)
        else:
            self.delete_episode_list(episodes)

    def on_key_press(self, widget, event):
        # Allow tab switching with Ctrl + PgUp/PgDown/Tab
        if event.state & gtk.gdk.CONTROL_MASK:
            if event.keyval == gtk.keysyms.Page_Up:
                self.wNotebook.prev_page()
                return True
            elif event.keyval == gtk.keysyms.Page_Down:
                self.wNotebook.next_page()
                return True
            elif event.keyval == gtk.keysyms.Tab:
                current_page = self.wNotebook.get_current_page()

                if current_page == self.wNotebook.get_n_pages()-1:
                    self.wNotebook.set_current_page(0)
                else:
                    self.wNotebook.next_page()
                return True

        return False

    def uniconify_main_window(self):
        if self.is_iconified():
            # We need to hide and then show the window in WMs like Metacity
            # or KWin4 to move the window to the active workspace
            # (see http://gpodder.org/bug/1125)
            self.gPodder.hide()
            self.gPodder.show()
            self.gPodder.present()

    def iconify_main_window(self):
        if not self.is_iconified():
            self.gPodder.iconify()

    @dbus.service.method(gpodder.dbus_interface)
    def show_gui_window(self):
        parent = self.get_dialog_parent()
        parent.present()

    @dbus.service.method(gpodder.dbus_interface)
    def subscribe_to_url(self, url):
        # Strip leading application protocol, so these URLs work:
        # gpodder://example.com/episodes.rss
        # gpodder:https://example.org/podcast.xml
        if url.startswith('gpodder:'):
            url = url[len('gpodder:'):]
            while url.startswith('/'):
                url = url[1:]

        self._add_podcast_dialog = gPodderAddPodcast(self.gPodder,
                add_podcast_list=self.add_podcast_list,
                preset_url=url)

    @dbus.service.method(gpodder.dbus_interface)
    def mark_episode_played(self, filename):
        if filename is None:
            return False

        for channel in self.channels:
            for episode in channel.get_all_episodes():
                fn = episode.local_filename(create=False, check_only=True)
                if fn == filename:
                    episode.mark(is_played=True)
                    self.db.commit()
                    self.update_episode_list_icons([episode.url])
                    self.update_podcast_list_model([episode.channel.url])
                    return True

        return False

    def extensions_podcast_update_cb(self, podcast):
        logger.debug('extensions_podcast_update_cb(%s)', podcast)
        self.update_feed_cache(channels=[podcast],
                show_new_episodes_dialog=False)

    def extensions_episode_download_cb(self, episode):
        logger.debug('extension_episode_download_cb(%s)', episode)
        self.download_episode_list(episodes=[episode])

    def on_sync_to_device_activate(self, widget, episodes=None, force_played=True):
        self.sync_ui = gPodderSyncUI(self.config, self.notification,
                self.main_window,
                self.show_confirmation,
                self.toolPreferences,
                self.channels,
                self.download_status_model,
                self.download_queue_manager,
                self.enable_download_list_update,
                self.commit_changes_to_database,
                self.delete_episode_list)

        self.sync_ui.on_synchronize_episodes(self.channels, episodes, force_played)

    def on_update_youtube_subscriptions_activate(self, widget):
        if not self.config.youtube.api_key_v3:
            if self.show_confirmation('\n'.join((_('Please register a YouTube API key and set it in the preferences.'),
                                                 _('Would you like to set up an API key now?'))), _('API key required')):
                self.on_itemPreferences_activate(self, widget)
            return

        failed_urls = []
        migrated_users = []
        for podcast in self.channels:
            url, user = youtube.for_each_feed_pattern(lambda url, channel: (url, channel), podcast.url, (None, None))
            if url is not None and user is not None:
                try:
                    logger.info('Getting channels for YouTube user %s (%s)', user, url)
                    new_urls = youtube.get_channels_for_user(user, self.config.youtube.api_key_v3)
                    logger.debug('YouTube channels retrieved: %r', new_urls)

                    if len(new_urls) == 0 and youtube.get_youtube_id(url) is not None:
                        logger.info('No need to update %s', url)
                        continue

                    if len(new_urls) != 1:
                        failed_urls.append((url, _('No unique URL found')))
                        continue

                    new_url = new_urls[0]
                    if new_url in set(x.url for x in self.model.get_podcasts()):
                        failed_urls.append((url, _('Already subscribed')))
                        continue

                    logger.info('New feed location: %s => %s', url, new_url)
                    podcast.url = new_url
                    podcast.save()
                    migrated_users.append(user)
                except Exception as e:
                    logger.error('Exception happened while updating download list.', exc_info=True)
                    self.show_message(_('Make sure the API key is correct. Error: %(message)s') % {'message': str(e)},
                                      _('Error getting YouTube channels'), important=True)

        if migrated_users:
            self.show_message('\n'.join(migrated_users), _('Successfully migrated subscriptions'))
        elif not failed_urls:
            self.show_message(_('Subscriptions are up to date'))

        if failed_urls:
            self.show_message('\n'.join([_('These URLs failed:'), ''] + ['{0}: {1}'.format(url, message)
                                                                         for url, message in failed_urls]),
                              _('Could not migrate some subscriptions'), important=True)


def main(options=None):
    gobject.threads_init()
    gobject.set_application_name('gPodder')

    for i in range(EpisodeListModel.PROGRESS_STEPS + 1):
        pixbuf = draw_cake_pixbuf(float(i) /
                float(EpisodeListModel.PROGRESS_STEPS))
        icon_name = 'gpodder-progress-%d' % i
        gtk.icon_theme_add_builtin_icon(icon_name, pixbuf.get_width(), pixbuf)

    gtk.window_set_default_icon_name('gpodder')
    gtk.about_dialog_set_url_hook(lambda dlg, link, data: util.open_website(link), None)

    try:
        dbus_main_loop = dbus.glib.DBusGMainLoop(set_as_default=True)
        gpodder.dbus_session_bus = dbus.SessionBus(dbus_main_loop)

        bus_name = dbus.service.BusName(gpodder.dbus_bus_name, bus=gpodder.dbus_session_bus)
    except dbus.exceptions.DBusException, dbe:
        logger.warn('Cannot get "on the bus".', exc_info=True)
        dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, \
                gtk.BUTTONS_CLOSE, _('Cannot start gPodder'))
        dlg.format_secondary_markup(_('D-Bus error: %s') % (str(dbe),))
        dlg.set_title('gPodder')
        dlg.run()
        dlg.destroy()
        sys.exit(0)

    gp = gPodder(bus_name, core.Core(UIConfig, model_class=Model), options)

    if gpodder.ui.osx:
        from gpodder.gtkui import macosx

        # Handle "subscribe to podcast" events from firefox
        macosx.register_handlers(gp)

        # Handle quit event
        if macapp is not None:
            macapp.connect('NSApplicationBlockTermination', gp.quit_cb)
            macapp.ready()

    gp.run()

