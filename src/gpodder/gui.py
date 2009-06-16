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

from xml.sax import saxutils

from threading import Event
from threading import Thread
from threading import Semaphore
from string import strip

import gpodder

import dbus
import dbus.service
import dbus.mainloop
import dbus.glib

from gpodder import feedcore
from gpodder import util
from gpodder import opml
from gpodder import services
from gpodder import download
from gpodder import uibase
from gpodder import maemo
from gpodder import my
from gpodder import widgets
from gpodder.liblogger import log
from gpodder.dbsqlite import db
from gpodder import resolver

_ = gpodder.gettext

from libpodcasts import PodcastChannel
from libpodcasts import LocalDBReader
from libpodcasts import channels_to_model
from libpodcasts import update_channel_model_by_iter
from libpodcasts import load_channels
from libpodcasts import update_channels
from libpodcasts import save_channels
from libpodcasts import can_restore_from_opml

from gpodder.libgpodder import gl

import hildon

app_authors = [
    _('Current maintainer:'), 'Thomas Perl <thpinfo.com>',
    '',
    _('Patches, bug reports and donations by:'), 'Adrien Beaucreux',
    'Alain Tauch', 'Alex Ghitza', 'Alistair Sutton', 'Anders Kvist', 'Andrei Dolganov', 'Andrew Bennett', 'Andy Busch',
    'Antonio Roversi', 'Aravind Seshadri', 'Atte André Jensen', 'audioworld', 
    'Bastian Staeck', 'Bernd Schlapsi', 'Bill Barnard', 'Bill Peters', 'Bjørn Rasmussen', 'Camille Moncelier', 'Casey Watson',
    'Carlos Moffat', 'Chris Arnold', 'Chris Moffitt', 'Clark Burbidge', 'Corey Goldberg', 'Cory Albrecht', 'daggpod', 'Daniel Ramos',
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

class BuilderWidget(uibase.GtkBuilderWidget):
    gpodder_main_window = None
    finger_friendly_widgets = []

    def __init__( self, **kwargs):
        uibase.GtkBuilderWidget.__init__(self, gpodder.ui_folder, gpodder.textdomain, **kwargs)

        # Set widgets to finger-friendly mode if on Maemo
        for widget_name in self.finger_friendly_widgets:
            if hasattr(self, widget_name):
                self.set_finger_friendly(getattr(self, widget_name))
            else:
                log('Finger-friendly widget not found: %s', widget_name, sender=self)

        if self.__class__.__name__ == 'gPodder':
            BuilderWidget.gpodder_main_window = self.gPodder
        else:
            # If we have a child window, set it transient for our main window
            self.main_window.set_transient_for(BuilderWidget.gpodder_main_window)

            if gpodder.interface == gpodder.GUI:
                if hasattr(self, 'center_on_widget'):
                    (x, y) = self.gpodder_main_window.get_position()
                    a = self.center_on_widget.allocation
                    (x, y) = (x + a.x, y + a.y)
                    (w, h) = (a.width, a.height)
                    (pw, ph) = self.main_window.get_size()
                    self.main_window.move(x + w/2 - pw/2, y + h/2 - ph/2)
                else:
                    self.main_window.set_position(gtk.WIN_POS_CENTER_ON_PARENT)

    def notification(self, message, title=None):
        util.idle_add(self.show_message, message, title)

    def show_message( self, message, title = None):
        dlg = hildon.hildon_note_new_information(BuilderWidget.gpodder_main_window, message)
        dlg.run()
        dlg.destroy()

    def set_finger_friendly(self, widget):
        """
        If we are on Maemo, we carry out the necessary
        operations to turn a widget into a finger-friendly
        one, depending on which type of widget it is (i.e.
        buttons will have more padding, TreeViews a thick
        scrollbar, etc..)
        """
        if widget is None:
            return None

        if gpodder.interface == gpodder.MAEMO:
            if isinstance(widget, gtk.Misc):
                widget.set_padding(0, 5)
            elif isinstance(widget, gtk.Button):
                for child in widget.get_children():
                    if isinstance(child, gtk.Alignment):
                        child.set_padding(5, 5, 5, 5)
                    else:
                        child.set_padding(5, 5)
            elif isinstance(widget, gtk.TreeView) or isinstance(widget, gtk.TextView):
                parent = widget.get_parent()
                if isinstance(parent, gtk.ScrolledWindow):
                    hildon.hildon_helper_set_thumb_scrollbar(parent, True)
            elif isinstance(widget, gtk.MenuItem):
                for child in widget.get_children():
                    self.set_finger_friendly(child)
                submenu = widget.get_submenu()
                if submenu is not None:
                    for child in submenu.get_children():
                        self.set_finger_friendly(child)
            elif isinstance(widget, gtk.Menu):
                for child in widget.get_children():
                    self.set_finger_friendly(child)
            else:
                log('Cannot set widget finger-friendly: %s', widget, sender=self)
                
        return widget

    def show_confirmation( self, message, title = None):
        dlg = hildon.hildon_note_new_confirmation(BuilderWidget.gpodder_main_window, message)
        response = dlg.run()
        dlg.destroy()
        
        return response == gtk.RESPONSE_OK

    def UsernamePasswordDialog( self, title, message, username=None, password=None, username_prompt=_('Username'), register_callback=None):
        """ An authentication dialog based on
                http://ardoris.wordpress.com/2008/07/05/pygtk-text-entry-dialog/ """

        dialog = gtk.MessageDialog(
            BuilderWidget.gpodder_main_window,
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            gtk.MESSAGE_QUESTION,
            gtk.BUTTONS_OK_CANCEL )

        dialog.set_image(gtk.image_new_from_stock(gtk.STOCK_DIALOG_AUTHENTICATION, gtk.ICON_SIZE_DIALOG))

        dialog.set_markup('<span weight="bold" size="larger">' + title + '</span>')
        dialog.set_title(_('Authentication required'))
        dialog.format_secondary_markup(message)
        dialog.set_default_response(gtk.RESPONSE_OK)

        if register_callback is not None:
            dialog.add_button(_('New user'), gtk.RESPONSE_HELP)

        username_entry = gtk.Entry()
        password_entry = gtk.Entry()

        username_entry.connect('activate', lambda w: password_entry.grab_focus())
        password_entry.set_visibility(False)
        password_entry.set_activates_default(True)

        if username is not None:
            username_entry.set_text(username)
        if password is not None:
            password_entry.set_text(password)

        table = gtk.Table(2, 2)
        table.set_row_spacings(6)
        table.set_col_spacings(6)

        username_label = gtk.Label()
        username_label.set_markup('<b>' + username_prompt + ':</b>')
        username_label.set_alignment(0.0, 0.5)
        table.attach(username_label, 0, 1, 0, 1, gtk.FILL, 0)
        table.attach(username_entry, 1, 2, 0, 1)

        password_label = gtk.Label()
        password_label.set_markup('<b>' + _('Password') + ':</b>')
        password_label.set_alignment(0.0, 0.5)
        table.attach(password_label, 0, 1, 1, 2, gtk.FILL, 0)
        table.attach(password_entry, 1, 2, 1, 2)

        dialog.vbox.pack_end(table, True, True, 0)
        dialog.show_all()
        response = dialog.run()

        while response == gtk.RESPONSE_HELP:
            register_callback()
            response = dialog.run()

        password_entry.set_visibility(True)
        dialog.destroy()

        return response == gtk.RESPONSE_OK, ( username_entry.get_text(), password_entry.get_text() )


class gPodder(BuilderWidget, dbus.service.Object):
    finger_friendly_widgets = ['btnCancelFeedUpdate', 'label2', 'labelDownloads', 'btnCleanUpDownloads']
    TREEVIEW_WIDGETS = ('treeAvailable', 'treeChannels')
    _app_menu = (
            ('btn_update_feeds', maemo.Button(_('Check for new episodes'))),
            ('btn_show_downloads', maemo.Button(_('Downloads'))),
            ('btn_subscribe', maemo.Button(_('Add new podcast'))),
            ('btn_unsubscribe', maemo.Button(_('Unsubscribe'))),
            #('btn_remove_old', maemo.Button(_('Remove old episodes'))),
            ('btn_preferences', maemo.Button(_('Preferences'))),
            ('btn_about', maemo.Button(_('About gPodder'))),
            ('btn_podcast_directory', maemo.Button(_('Podcast directory'))),
    )

    def on_btn_update_feeds_clicked(self, widget):
        self.on_itemUpdate_activate(widget)

    def on_btn_show_downloads_clicked(self, widget):
        self.downloads_window.show()

    def on_btn_subscribe_clicked(self, widget):
        gPodderAddPodcastDialog(url_callback=self.add_new_channel)

    def on_btn_podcast_directory_clicked(self, widget):
        self.on_itemImportChannels_activate(None)

    def on_btn_unsubscribe_clicked(self, widget):
        self.on_itemRemoveChannel_activate()

    def on_btn_preferences_clicked(self, widget):
        gPodderMaemoPreferences()

    def on_btn_about_clicked(self, widget):
        dlg = gtk.AboutDialog()
        dlg.set_name('gPodder')
        dlg.set_version(gpodder.__version__)
        dlg.set_copyright(gpodder.__copyright__)
        dlg.set_website(gpodder.__url__)
        dlg.set_translator_credits(_('translator-credits'))
        dlg.connect( 'response', lambda dlg, response: dlg.destroy())
        dlg.set_authors(app_authors)
        try:
            dlg.set_logo(gtk.gdk.pixbuf_new_from_file(gpodder.icon_file))
        except:
            dlg.set_logo_icon_name('gpodder')
        dlg.run()

    def __init__(self, bus_name):
        dbus.service.Object.__init__(self, object_path=gpodder.dbus_gui_object_path, bus_name=bus_name)
        BuilderWidget.__init__(self)
    
    def new(self):
        maemo.create_app_menu(self)
        gpodder.icon_file = gpodder.icon_file.replace('.svg', '.png')
        
        self.app = hildon.Program()
        self.app.add_window(self.gPodder)
        gtk.set_application_name('gPodder')
        self.wNotebook.set_show_tabs(False)
        
        self.gPodder.show()
    
        self.downloads_window = gPodderStackableDownloads(
                downloads_list_vbox=self.vboxDownloadStatusWidgets,
                cleanup_callback=self.on_btnCleanUpDownloads_clicked,
                set_status_on_all_downloads=self.set_status_on_all_downloads)
        
        self.gPodder.connect('key-press-event', self.on_key_press)

        self.gpodder_episode_window = None

        self.download_status_manager = services.DownloadStatusManager()
        self.download_queue_manager = download.DownloadQueueManager(self.download_status_manager)

        self.fullscreen = False
        self.minimized = False
        self.gPodder.connect('window-state-event', self.window_state_event)
        
        gl.config.connect_gtk_window(self.gPodder, 'main_window')
        gl.config.connect_gtk_paned('paned_position', self.channelPaned)

        self.default_title = None
        if gpodder.__version__.rfind('git') != -1:
            self.set_title('gPodder %s' % gpodder.__version__)
        else:
            self.set_title(_('Welcome!'))

        gtk.about_dialog_set_url_hook(lambda dlg, link, data: util.open_website(link), None)

        # cell renderers for channel tree
        iconcolumn = gtk.TreeViewColumn('')

        iconcell = gtk.CellRendererPixbuf()
        iconcolumn.pack_start( iconcell, False)
        iconcolumn.add_attribute( iconcell, 'pixbuf', 5)
        self.cell_channel_icon = iconcell

        namecolumn = gtk.TreeViewColumn('')
        namecell = gtk.CellRendererText()
        namecell.set_property('ellipsize', pango.ELLIPSIZE_END)
        namecolumn.pack_start( namecell, True)
        namecolumn.add_attribute( namecell, 'markup', 2)

        iconcell = gtk.CellRendererPixbuf()
        iconcell.set_property('xalign', 1.0)
        namecolumn.pack_start( iconcell, False)
        namecolumn.add_attribute( iconcell, 'pixbuf', 3)
        namecolumn.add_attribute(iconcell, 'visible', 7)
        self.cell_channel_pill = iconcell

        self.treeChannels.append_column(iconcolumn)
        self.treeChannels.append_column(namecolumn)
        self.treeChannels.set_headers_visible(False)
        self.treeAvailable.set_headers_visible(False)

        # enable alternating colors hint
        self.treeAvailable.set_rules_hint( True)
        self.treeChannels.set_rules_hint( True)

        self.currently_updating = False

        self.treeview_available_buttonpress = (0, 0)
        self.treeAvailable.connect('button-press-event', self.treeview_button_savepos)
        self.treeAvailable.connect('button-release-event', self.treeview_button_pressed)

        self.treeview_channels_buttonpress = (0, 0)
        self.treeChannels.connect('button-press-event', self.treeview_channels_button_pressed)
        self.treeChannels.connect('button-release-event', self.treeview_channels_button_released)

        self.treeDownloads.connect('button-press-event', self.treeview_downloads_button_pressed)

        iconcell = gtk.CellRendererPixbuf()
        iconcell.set_fixed_size(-1, 52)
        iconcolumn = gtk.TreeViewColumn('', iconcell, pixbuf=4)

        namecell = gtk.CellRendererText()
        namecell.set_property('ellipsize', pango.ELLIPSIZE_END)
        namecolumn = gtk.TreeViewColumn(_("Episode"), namecell, markup=6)
        namecolumn.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        namecolumn.set_resizable(True)
        namecolumn.set_expand(True)

        sizecell = gtk.CellRendererText()
        sizecolumn = gtk.TreeViewColumn( _("Size"), sizecell, text=2)

        releasecell = gtk.CellRendererText()
        releasecolumn = gtk.TreeViewColumn( _("Released"), releasecell, text=5)
        
        for itemcolumn in (iconcolumn, namecolumn, sizecolumn, releasecolumn):
            itemcolumn.set_reorderable(False)
            self.treeAvailable.append_column(itemcolumn)

        # Due to screen space contraints, we
        # hide these columns here by default
        self.column_size = sizecolumn
        self.column_released = releasecolumn
        self.column_released.set_visible(False)
        self.column_size.set_visible(False)

        # on Maemo 5, we need to set hildon-ui-mode of TreeView widgets to 1
        HUIM = 'hildon-ui-mode'
        if HUIM in [p.name for p in gobject.list_properties(gtk.TreeView)]:
            for treeview_name in self.TREEVIEW_WIDGETS:
                treeview = getattr(self, treeview_name)
                treeview.set_property(HUIM, 1)

        # enable multiple selection support
        self.treeAvailable.get_selection().set_mode(gtk.SELECTION_SINGLE)
        self.treeDownloads.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

        if hasattr(self.treeDownloads, 'set_rubber_banding'):
            # Available in PyGTK 2.10 and above
            self.treeDownloads.set_rubber_banding(True)
        
        # columns and renderers for "download progress" tab
        DownloadStatusManager = services.DownloadStatusManager

        # First column: [ICON] Episodename
        column = gtk.TreeViewColumn(_('Episode'))

        cell = gtk.CellRendererPixbuf()
        cell.set_property('stock-size', gtk.ICON_SIZE_DIALOG)
        column.pack_start(cell, expand=False)
        column.add_attribute(cell, 'stock-id', \
                DownloadStatusManager.C_ICON_NAME)

        cell = gtk.CellRendererText()
        cell.set_property('ellipsize', pango.ELLIPSIZE_END)
        column.pack_start(cell, expand=True)
        column.add_attribute(cell, 'text', DownloadStatusManager.C_NAME)

        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        column.set_resizable(True)
        column.set_expand(True)
        self.treeDownloads.append_column(column)

        # Second column: Progress
        column = gtk.TreeViewColumn(_('Progress'), gtk.CellRendererProgress(),
                value=DownloadStatusManager.C_PROGRESS, \
                text=DownloadStatusManager.C_PROGRESS_TEXT)
        self.treeDownloads.append_column(column)

        # Third column: Size
        if gpodder.interface != gpodder.MAEMO:
            column = gtk.TreeViewColumn(_('Size'), gtk.CellRendererText(),
                    text=DownloadStatusManager.C_SIZE_TEXT)
            self.treeDownloads.append_column(column)

        # Fourth column: Speed
        column = gtk.TreeViewColumn(_('Speed'), gtk.CellRendererText(),
                text=DownloadStatusManager.C_SPEED_TEXT)
        self.treeDownloads.append_column(column)

        # Fifth column: Status
        column = gtk.TreeViewColumn(_('Status'), gtk.CellRendererText(),
                text=DownloadStatusManager.C_STATUS_TEXT)
        self.treeDownloads.append_column(column)

        # a dictionary that maps episode URLs to the current
        # treeAvailable row numbers to generate tree paths
        self.url_path_mapping = {}

        # a dictionary that maps channel URLs to the current
        # treeChannels row numbers to generate tree paths
        self.channel_url_path_mapping = {}

        services.cover_downloader.register('cover-available', self.cover_download_finished)
        services.cover_downloader.register('cover-removed', self.cover_file_removed)
        self.cover_cache = {}

        self.treeDownloads.set_model(self.download_status_manager.get_tree_model())
        gobject.timeout_add(1500, self.update_downloads_list)
        self.download_tasks_seen = set()
        self.last_download_count = 0
        
        #Add Drag and Drop Support
        flags = gtk.DEST_DEFAULT_ALL
        targets = [ ('text/plain', 0, 2), ('STRING', 0, 3), ('TEXT', 0, 4) ]
        actions = gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_COPY
        self.treeChannels.drag_dest_set( flags, targets, actions)
        self.treeChannels.connect( 'drag_data_received', self.drag_data_received)

        # Subscribed channels
        self.active_channel = None
        self.channels = load_channels()
        self.channel_list_changed = True

        # Last folder used for saving episodes
        self.folder_for_saving_episodes = None

        # Now, update the feed cache, when everything's in place
        self.updating_feed_cache = False
        self.feed_cache_update_cancelled = False
        self.update_feed_cache(force_update=gl.config.update_on_startup)

        # Clean up old, orphaned download files
        partial_files = gl.find_partial_files()

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
                self.downloads_window.show()
                dlg = hildon.hildon_note_new_information(self.main_window, _('There are unfinished downloads from your last session. Pick the ones you want to continue downloading.'))
                dlg.run()
                dlg.destroy()

            gl.clean_up_downloads(delete_partial=False)
        else:
            gl.clean_up_downloads(delete_partial=True)

        # Start the auto-update procedure
        self.auto_update_procedure(first_run=True)

        # Delete old episodes if the user wishes to
        if gl.config.auto_remove_old_episodes:
            old_episodes = self.get_old_episodes()
            if len(old_episodes) > 0:
                self.delete_episode_list(old_episodes, confirm=False)
                self.updateComboBox()

        # First-time users should be asked if they want to see the OPML
        if len(self.channels) == 0:
            util.idle_add(self.on_itemUpdate_activate)

    def on_btnCleanUpDownloads_clicked(self, button=None):
        model = self.treeDownloads.get_model()

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

    def set_status_on_all_downloads(self, status):
        model = self.treeDownloads.get_model()

        all_tasks = [row[0] for row in model]
        changed_episode_urls = []
        for task in all_tasks:
            if status == download.DownloadTask.QUEUED:
                # Only queue task when its paused/failed/cancelled
                if task.status in (task.PAUSED, task.FAILED, task.CANCELLED):
                    self.download_queue_manager.add_task(task)
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
                changed_episode_urls.append(task.url)

        # Tell the podcasts tab to update icons for our removed podcasts
        self.update_episode_list_icons(changed_episode_urls)

    def on_tool_downloads_toggled(self, toolbutton):
        if toolbutton.get_active():
            self.downloads_window.show()
            #self.wNotebook.set_current_page(1)
            toolbutton.set_active(False)
        else:
            self.wNotebook.set_current_page(0)

    def update_downloads_list(self):
        try:
            model = self.treeDownloads.get_model()

            downloading, failed, finished, queued, others = 0, 0, 0, 0, 0
            total_speed, total_size, done_size = 0, 0, 0

            # Keep a list of all download tasks that we've seen
            download_tasks_seen = set()

            # Remember the progress and speed for the episode that
            # has been opened in the episode shownotes dialog (if any)
            if self.gpodder_episode_window is not None:
                episode_window_episode = self.gpodder_episode_window.episode
                episode_window_task = None
            else:
                episode_window_episode = None

            # Do not go through the list of the model is not (yet) available
            if model is None:
                model = ()

            for row in model:
                self.download_status_manager.request_update(row.iter)

                task = row[self.download_status_manager.C_TASK]
                speed, size, status, progress = task.speed, task.total_size, task.status, task.progress

                total_size += size
                done_size += size*progress

                if episode_window_episode is not None and \
                        episode_window_episode.url == task.url:
                    episode_window_task = task

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

            if downloading + queued:
                self.btn_show_downloads.set_value(_('%d active') % (downloading + queued))
            elif failed:
                self.btn_show_downloads.set_value(_('%d failed') % failed)
            elif others:
                self.btn_show_downloads.set_value(_('%d waiting') % others)
            elif finished:
                self.btn_show_downloads.set_value(_('%d done') % finished)
            else:
                self.btn_show_downloads.set_value(_('idle'))

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
                total_speed = gl.format_filesize(total_speed)
                title[1] += ' (%d%%, %s/s)' % (percentage, total_speed)
            elif self.last_download_count > 0:
                # XXX Hildonization
                #hildon.hildon_banner_show_information(self.gPodder, None, 'gPodder: %s' % _('All downloads finished'))
                log('All downloads have finished.', sender=self)
                if gl.config.cmd_all_downloads_complete:
                    util.run_external_command(gl.config.cmd_all_downloads_complete)
            self.last_download_count = count

            self.gPodder.set_title(' - '.join(title))

            self.update_episode_list_icons(episode_urls)
            if self.gpodder_episode_window is not None:
                if episode_window_task and episode_window_task.url in episode_urls:
                    self.gpodder_episode_window.download_status_changed(episode_window_task)
                elif episode_window_task != self.gpodder_episode_window.task:
                    self.gpodder_episode_window.download_status_changed(episode_window_task)
                self.gpodder_episode_window.download_status_progress()
            if channel_urls:
                self.updateComboBox(only_these_urls=channel_urls)
            return True
        except Exception, e:
            log('Exception happened while updating download list.', sender=self, traceback=True)
            self.show_message('%s\n\n%s' % (_('Please report this problem and restart gPodder:'), str(e)), _('Unhandled exception'))
            # We return False here, so the update loop won't be called again,
            # that's why we require the restart of gPodder in the message.
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
                return True

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
            
            selected_tasks = [model.get_value(model.get_iter(path), 0) for path in paths]
            if len(selected_tasks) == 1:
                task = selected_tasks[0]
                self.show_episode_shownotes(task.episode)
                return True

    def treeview_channels_button_pressed( self, treeview, event):
        self.treeview_channels_buttonpress = (event.x, event.y)
        return True

    def cover_file_removed(self, channel_url):
        """
        The Cover Downloader calls this when a previously-
        available cover has been removed from the disk. We
        have to update our cache to reflect this change.
        """
        (COLUMN_URL, COLUMN_PIXBUF) = (0, 5)
        for row in self.treeChannels.get_model():
            if row[COLUMN_URL] == channel_url:
                row[COLUMN_PIXBUF] = None
                key = (channel_url, gl.config.podcast_list_icon_size, \
                        gl.config.podcast_list_icon_size)
                if key in self.cover_cache:
                    del self.cover_cache[key]
        
    
    def cover_download_finished(self, channel_url, pixbuf):
        """
        The Cover Downloader calls this when it has finished
        downloading (or registering, if already downloaded)
        a new channel cover, which is ready for displaying.
        """
        if pixbuf is not None:
            (COLUMN_URL, COLUMN_PIXBUF) = (0, 5)
            model = self.treeChannels.get_model()
            if model is None:
                # Not yet ready (race condition) - simply ignore
                return

            for row in model:
                if row[COLUMN_URL] == channel_url and row[COLUMN_PIXBUF] is None:
                    new_pixbuf = util.resize_pixbuf_keep_ratio(pixbuf, gl.config.podcast_list_icon_size, gl.config.podcast_list_icon_size, channel_url, self.cover_cache)
                    row[COLUMN_PIXBUF] = new_pixbuf or pixbuf

    def treeview_button_savepos(self, treeview, event):
        if event.button == 1:
            self.treeview_available_buttonpress = (event.x, event.y)
            return True

    def treeview_channels_button_released(self, treeview, event):
        if event.button == 1:
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

    def treeview_button_pressed( self, treeview, event):
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
        else:
            # Scrolling has been done
            return True
        
        # Use right-click for the Desktop version and left-click for Maemo
        if event.button == 1:
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
            if not len(paths):
                return True

            if self.active_channel and len(paths) == 1:
                first_url = model.get_value(model.get_iter(paths[0]), 0)
                episode = db.load_episode(first_url, factory=self.active_channel.episode_factory)
                self.show_episode_shownotes(episode)
                return True

    def set_title(self, new_title):
        self.default_title = 'gPodder - ' + new_title
        self.gPodder.set_title(self.default_title)

    def update_selected_episode_list_icons(self):
        """
        Updates the status icons in the episode list
        """
        selection = self.treeAvailable.get_selection()
        (model, paths) = selection.get_selected_rows()
        for path in paths:
            iter = model.get_iter(path)
            self.active_channel.iter_set_downloading_columns(model, iter, downloading=self.episode_is_downloading)

    def update_episode_list_icons(self, urls):
        """
        Updates the status icons in the episode list
        Only update the episodes that have an URL in
        the "urls" iterable object (e.g. a list of URLs)
        """
        if self.active_channel is None or not urls:
            return

        model = self.treeAvailable.get_model()
        if model is None:
            return

        for url in urls:
            if url in self.url_path_mapping:
                path = (self.url_path_mapping[url],)
                self.active_channel.iter_set_downloading_columns(model, model.get_iter(path), downloading=self.episode_is_downloading)
 
    def playback_episode(self, episode, stream=False):
        # FIXME: show "opening file..." banner (HILDONIZATION)
        (success, application) = gl.playback_episode(episode, stream)
        if not success:
            self.show_message( _('The selected player application cannot be found. Please check your media player settings in the preferences dialog.'), _('Error opening player: %s') % ( saxutils.escape( application), ))
        self.update_selected_episode_list_icons()
        self.updateComboBox(only_selected_channel=True)

    def episode_new_status_changed(self, urls):
        self.updateComboBox()
        self.update_episode_list_icons(urls)

    def updateComboBox(self, selected_url=None, only_selected_channel=False, only_these_urls=None):
        selection = self.treeChannels.get_selection()
        (model, iter) = selection.get_selected()

        if only_selected_channel:
            # very cheap! only update selected channel
            if iter and self.active_channel is not None:
                update_channel_model_by_iter(model, iter,
                    self.active_channel,
                    self.cover_cache,
                    gl.config.podcast_list_icon_size,
                    gl.config.podcast_list_icon_size)
        elif not self.channel_list_changed:
            # we can keep the model, but have to update some
            if only_these_urls is None:
                # still cheaper than reloading the whole list
                iter = model.get_iter_first()
                while iter is not None:
                    (index,) = model.get_path(iter)
                    update_channel_model_by_iter(model, iter,
                        self.channels[index],
                        self.cover_cache,
                        gl.config.podcast_list_icon_size,
                        gl.config.podcast_list_icon_size)
                    iter = model.iter_next(iter)
            else:
                # ok, we got a bunch of urls to update
                for url in only_these_urls:
                    if url in self.channel_url_path_mapping:
                        index = self.channel_url_path_mapping[url]
                        path = (index,)
                        iter = model.get_iter(path)
                        update_channel_model_by_iter(model, iter,
                            self.channels[index],
                            self.cover_cache,
                            gl.config.podcast_list_icon_size,
                            gl.config.podcast_list_icon_size)
        else:
            if model and iter and selected_url is None:
                # Get the URL of the currently-selected podcast
                selected_url = model.get_value(iter, 0)

            (model, urls) = channels_to_model(self.channels,
                    self.cover_cache,
                    gl.config.podcast_list_icon_size,
                    gl.config.podcast_list_icon_size)

            self.channel_url_path_mapping = dict(zip(urls, range(len(urls))))
            self.treeChannels.set_model(model)

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
    
    def updateTreeView(self):
        if self.channels and self.active_channel is not None:
            # XXX: FIX BANNER SHOWING HILDONIZATION
            #banner = hildon.hildon_banner_show_information(self.main_window, 'hildon22-ignored', _('Loading episodes for %s') % saxutils.escape(self.active_channel.title))
            banner = None
            def thread_func(self, banner, active_channel):
                (model, urls) = self.active_channel.get_tree_model(self.episode_is_downloading)
                mapping = dict(zip(urls, range(len(urls))))
                def update_gui_with_new_model(self, channel, model, urls, mapping, banner):
                    if self.active_channel is not None and channel is not None:
                        log('%s <=> %s', self.active_channel.title, channel.title, sender=self)
                    if self.active_channel == channel:
                        self.treeAvailable.set_model(model)
                        self.url_path_mapping = mapping
                        self.treeAvailable.columns_autosize()
                    if banner is not None:
                        banner.destroy()
                    self.currently_updating = False
                    return False
                gobject.idle_add(lambda: update_gui_with_new_model(self, active_channel, model, urls, mapping, banner))
            self.currently_updating = True
            Thread(target=thread_func, args=[self, banner, self.active_channel]).start()
        else:
            model = self.treeAvailable.get_model()
            if model is not None:
                model.clear()
    
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
            services.cover_downloader.replace_cover(dnd_channel, result)
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

        waitdlg = hildon.hildon_note_new_information(self.main_window, _('Downloading episode information for %s') % result)
        waitdlg.show_all()

        self.entryAddChannel.set_text(_('Downloading feed...'))
        self.entryAddChannel.set_sensitive(False)
        self.btnAddChannel.set_sensitive(False)
        args = (result, self.add_new_channel_finish, authentication_tokens, ask_download_new, quiet, waitdlg)
        thread = Thread( target=self.add_new_channel_proc, args=args )
        thread.start()

        while block and thread.isAlive():
            while gtk.events_pending():
                gtk.main_iteration( False)
            time.sleep(0.1)


    def add_new_channel_proc( self, url, callback, authentication_tokens, *callback_args):
        log( 'Adding new channel: %s', url)
        channel = error = None
        try:
            channel = PodcastChannel.load(url=url, create=True, authentication_tokens=authentication_tokens)
        except feedcore.AuthenticationRequired, e:
            error = e
        except feedcore.WifiLogin, e:
            error = e
        except Exception, e:
            log('Error in PodcastChannel.load(%s): %s', url, e, traceback=True, sender=self)

        util.idle_add( callback, channel, url, error, *callback_args )

    def add_new_channel_finish( self, channel, url, error, ask_download_new, quiet, waitdlg):
        if channel is not None:
            self.channels.append( channel)
            self.channel_list_changed = True
            save_channels( self.channels)
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
                self.channels = load_channels()
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

        waitdlg.destroy()


    def update_feed_cache_finish_callback(self, updated_urls=None, select_url_afterwards=None):
        db.commit()
        self.updating_feed_cache = False
        hildon.hildon_gtk_window_set_progress_indicator(self.main_window, 0)

        self.channels = load_channels()
        self.channel_list_changed = True
        self.updateComboBox(selected_url=select_url_afterwards)

        # Only search for new episodes in podcasts that have been
        # updated, not in other podcasts (for single-feed updates)
        episodes = self.get_new_episodes([c for c in self.channels if c.url in updated_urls])

        if not episodes:
            # Nothing new here - but inform the user
            self.feed_cache_update_cancelled = True
            self.show_message(_('No new episodes available at the moment.'))
        elif self.minimized:
            # New episodes are available, but we are minimized
            if gl.config.auto_download_when_minimized:
                self.download_episode_list(episodes)
        else:
            # New episodes are available and we are not minimized
            self.new_episodes_show(episodes)

    def update_feed_cache_proc(self, channels, select_url_afterwards):
        total = len(channels)

        for updated, channel in enumerate(channels):
            if not self.feed_cache_update_cancelled:
                try:
                    channel.update()
                except feedcore.Offline:
                    self.feed_cache_update_cancelled = True
                    if not self.minimized:
                        util.idle_add(self.show_message, _('The feed update has been cancelled because you appear to be offline.'), _('Cannot connect to server'))
                    break
                except Exception, e:
                    util.idle_add(self.show_message, _('There has been an error updating %s: %s') % (saxutils.escape(channel.url), saxutils.escape(str(e))), _('Error while updating feed'))
                    log('Error: %s', str(e), sender=self, traceback=True)

            # By the time we get here the update may have already been cancelled
            if not self.feed_cache_update_cancelled:
                def update_progress():
                    progression = _('Updated %s (%d/%d)') % (channel.title, updated, total)
                    self.pbFeedUpdate.set_text(progression)
                    self.pbFeedUpdate.set_fraction(float(updated)/float(total))
                util.idle_add(update_progress)

            if self.feed_cache_update_cancelled:
                break

        updated_urls = [c.url for c in channels]
        util.idle_add(self.update_feed_cache_finish_callback, updated_urls, select_url_afterwards)

    def update_feed_cache(self, channels=None, force_update=True, select_url_afterwards=None):
        if self.updating_feed_cache: 
            return

        if not force_update:
            self.channels = load_channels()
            self.channel_list_changed = True
            self.updateComboBox(selected_url=select_url_afterwards)
            return
        
        self.updating_feed_cache = True
        hildon.hildon_gtk_window_set_progress_indicator(self.main_window, 1)

        if channels is None:
            channels = self.channels

        self.feed_cache_update_cancelled = False

        args = (channels, select_url_afterwards)
        Thread(target=self.update_feed_cache_proc, args=args).start()

    def on_gPodder_delete_event(self, widget, *args):
        """Called when the GUI wants to close the window
        Displays a confirmation dialog (and closes/hides gPodder)
        """

        downloading = self.download_status_manager.are_downloads_in_progress()

        if downloading:
            message = _('You are downloading episodes. You can resume downloads the next time you start gPodder. Do you want to quit now?')
            if self.show_confirmation(message):
                self.close_gpodder()
        else:
            self.close_gpodder()

        return True

    def close_gpodder(self):
        """ clean everything and exit properly
        """
        if self.channels:
            if save_channels(self.channels):
                if gl.config.my_gpodder_autoupload:
                    log('Uploading to my.gpodder.org on close', sender=self)
                    util.idle_add(self.on_upload_to_mygpo, None)
            else:
                self.show_message(_('Please check your permissions and free disk space.'), _('Error saving podcast list'))

        self.gPodder.hide()

        # Notify all tasks to to carry out any clean-up actions
        self.download_status_manager.tell_all_tasks_to_quit()

        while gtk.events_pending():
            gtk.main_iteration(False)

        db.close()

        self.quit()
        sys.exit(0)

    def get_old_episodes(self):
        episodes = []
        for channel in self.channels:
            for episode in channel.get_downloaded_episodes():
                if episode.is_old() and not episode.is_locked and episode.is_played:
                    episodes.append(episode)
        return episodes

    def for_each_selected_episode_url( self, callback):
        ( model, paths ) = self.treeAvailable.get_selection().get_selected_rows()
        for path in paths:
            url = model.get_value( model.get_iter( path), 0)
            try:
                callback( url)
            except Exception, e:
                log( 'Warning: Error in for_each_selected_episode_url for URL %s: %s', url, e, sender = self)

        self.update_selected_episode_list_icons()
        self.updateComboBox(only_selected_channel=True)
        db.commit()

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
        db.commit()

        #self.download_status_updated(episode_urls, channel_urls)

    def on_itemRemoveOldEpisodes_activate( self, widget):
        columns = (
                ('title_and_description', None, None, _('Episode')),
                ('channel_prop', None, None, _('Podcast')),
                ('filesize_prop', 'length', gobject.TYPE_INT, _('Size')),
                ('pubdate_prop', 'pubDate', gobject.TYPE_INT, _('Released')),
                ('played_prop', None, None, _('Status')),
                ('age_prop', None, None, _('Downloaded')),
        )

        selection_buttons = {
                _('Select played'): lambda episode: episode.is_played,
                _('Select older than %d days') % gl.config.episode_old_age: lambda episode: episode.is_old(),
        }

        instructions = _('Select the episodes you want to delete from your hard disk.')

        episodes = []
        selected = []
        for channel in self.channels:
            for episode in channel.get_downloaded_episodes():
                if not episode.is_locked:
                    episodes.append(episode)
                    selected.append(episode.is_played)

        gPodderEpisodeSelector( title = _('Remove old episodes'), instructions = instructions, \
                                episodes = episodes, selected = selected, columns = columns, \
                                stock_ok_button = gtk.STOCK_DELETE, callback = self.delete_episode_list, \
                                selection_buttons = selection_buttons)

    def on_itemUpdate_activate(self, widget=None):
        if self.channels:
            self.update_feed_cache()
            return

        restore_from = can_restore_from_opml()
        if restore_from is not None:
            title = _('Database upgrade required')
            message = _('gPodder is now using a new (much faster) database backend and needs to convert your current data. This can take some time. Start the conversion now?')
            if self.show_confirmation(message, title):
                add_callback = lambda url: self.add_new_channel(url, False, True)
                w = gtk.Dialog(_('Migrating to SQLite'), self.gPodder, 0, (gtk.STOCK_CLOSE, gtk.RESPONSE_ACCEPT))
                w.set_has_separator(False)
                w.set_response_sensitive(gtk.RESPONSE_ACCEPT, False)
                w.set_default_size(500, -1)
                pb = gtk.ProgressBar()
                l = gtk.Label()
                l.set_padding(6, 3)
                l.set_markup('<b><big>%s</big></b>' % _('SQLite migration'))
                l.set_alignment(0.0, 0.5)
                w.vbox.pack_start(l)
                l = gtk.Label()
                l.set_padding(6, 3)
                l.set_alignment(0.0, 0.5)
                l.set_text(_('Please wait while your settings are converted.'))
                w.vbox.pack_start(l)
                w.vbox.pack_start(pb)
                lb = gtk.Label()
                lb.set_ellipsize(pango.ELLIPSIZE_END)
                lb.set_alignment(0.0, 0.5)
                lb.set_padding(6, 6)
                w.vbox.pack_start(lb)

                def set_pb_status(pb, lb, fraction, text):
                    pb.set_fraction(float(fraction)/100.0)
                    pb.set_text('%.0f %%' % fraction)
                    lb.set_markup('<i>%s</i>' % saxutils.escape(text))
                    while gtk.events_pending():
                        gtk.main_iteration(False)
                status_callback = lambda fraction, text: set_pb_status(pb, lb, fraction, text)
                get_localdb = lambda channel: LocalDBReader(channel.url).read(channel.index_file)
                w.show_all()
                start = datetime.datetime.now()
                gl.migrate_to_sqlite(add_callback, status_callback, load_channels, get_localdb)
                # Refresh the view with the updated episodes
                self.updateComboBox()
                time_taken = str(datetime.datetime.now()-start)
                status_callback(100.0, _('Migration finished in %s') % time_taken)
                w.set_response_sensitive(gtk.RESPONSE_ACCEPT, True)
                w.run()
                w.destroy()
        else:
            self.on_itemImportChannels_activate(None)
            #gPodderWelcome(center_on_widget=self.gPodder, show_example_podcasts_callback=self.on_itemImportChannels_activate, setup_my_gpodder_callback=self.on_download_from_mygpo)

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
                        task_exists = True
                        continue

                if task_exists:
                    continue

                try:
                    task = download.DownloadTask(episode)
                except Exception, e:
                    self.show_message(_('Download error while downloading %s:\n\n%s') % (episode.title, str(e)), _('Download error'))
                    log('Download error while downloading %s', episode.title, sender=self, traceback=True)
                    continue

                if add_paused:
                    task.status = task.PAUSED
                    self.download_queue_manager.add_resumed_task(task)
                else:
                    self.download_queue_manager.add_task(task)

    def new_episodes_show(self, episodes):
        columns = (
                ('title_and_description', None, None, _('Episode')),
        #        ('channel_prop', None, None, _('Podcast')),
        #        ('filesize_prop', 'length', gobject.TYPE_INT, _('Size')),
        #        ('pubdate_prop', 'pubDate', gobject.TYPE_INT, _('Released')),
        )

        instructions = _('Select the episodes you want to download now.')

        gPodderEpisodeSelector(title=_('New episodes available - pick the ones to download'), instructions=instructions, \
                               episodes=episodes, columns=columns, selected_default=True, \
                               stock_ok_button = 'gpodder-download', \
                               callback=self.download_episode_list, \
                               remove_callback=lambda e: e.mark_old(), \
                               remove_action=_('Remove'), \
                               remove_finished=self.episode_new_status_changed)

    def on_itemDownloadAllNew_activate(self, widget, *args):
        new_episodes = self.get_new_episodes()
        if len(new_episodes):
            self.new_episodes_show(new_episodes)
        else:
            msg = _('No new episodes available for download')
            self.show_message(msg, _('No new episodes'))

    def get_new_episodes(self, channels=None):
        if channels is None:
            channels = self.channels
        episodes = []
        for channel in channels:
            for episode in channel.get_new_episodes(downloading=self.episode_is_downloading):
                episodes.append(episode)

        return episodes

    def require_my_gpodder_authentication(self):
        if not gl.config.my_gpodder_username or not gl.config.my_gpodder_password:
            success, authentication = self.UsernamePasswordDialog(_('Login to my.gpodder.org'), _('Please enter your e-mail address and your password.'), username=gl.config.my_gpodder_username, password=gl.config.my_gpodder_password, username_prompt=_('E-Mail Address'), register_callback=lambda: util.open_website('http://my.gpodder.org/register'))
            if success and authentication[0] and authentication[1]:
                gl.config.my_gpodder_username, gl.config.my_gpodder_password = authentication
                return True
            else:
                return False

        return True
    
    def my_gpodder_offer_autoupload(self):
        if not gl.config.my_gpodder_autoupload:
            if self.show_confirmation(_('gPodder can automatically upload your subscription list to my.gpodder.org when you close it. Do you want to enable this feature?'), _('Upload subscriptions on quit')):
                gl.config.my_gpodder_autoupload = True
    
    def on_download_from_mygpo(self, widget):
        if self.require_my_gpodder_authentication():
            client = my.MygPodderClient(gl.config.my_gpodder_username, gl.config.my_gpodder_password)
            opml_data = client.download_subscriptions()
            if len(opml_data) > 0:
                fp = open(gl.channel_opml_file, 'w')
                fp.write(opml_data)
                fp.close()
                (added, skipped) = (0, 0)
                i = opml.Importer(gl.channel_opml_file)
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
                gl.config.my_gpodder_password = ''
                self.on_download_from_mygpo(widget)
        else:
            self.show_message(_('Please set up your username and password first.'), _('Username and password needed'))

    def on_upload_to_mygpo(self, widget):
        if self.require_my_gpodder_authentication():
            client = my.MygPodderClient(gl.config.my_gpodder_username, gl.config.my_gpodder_password)
            save_channels(self.channels)
            success, messages = client.upload_subscriptions(gl.channel_opml_file)
            if widget is not None:
                self.show_message('\n'.join(messages), _('Results of upload'))
                if not success:
                    gl.config.my_gpodder_password = ''
                    self.on_upload_to_mygpo(widget)
                else:
                    self.my_gpodder_offer_autoupload()
            elif not success:
                log('Upload to my.gpodder.org failed, but widget is None!', sender=self)
        elif widget is not None:
            self.show_message(_('Please set up your username and password first.'), _('Username and password needed'))

    def on_itemRemoveChannel_activate(self, widget=None, *args):
        try:
            if self.show_confirmation(_('Do you really want to remove "%s" and all downloaded episodes?') % saxutils.escape(self.active_channel.title)):
                # delete downloaded episodes
                self.active_channel.remove_downloaded()

                # Clean up downloads and download directories
                gl.clean_up_downloads()

                # cancel any active downloads from this channel
                for episode in self.active_channel.get_all_episodes():
                    self.download_status_manager.cancel_by_url(episode.url)

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
                save_channels(self.channels)

                # Re-load the channels and select the desired new channel
                self.update_feed_cache(force_update=False, select_url_afterwards=select_url)
        except:
            log('There has been an error removing the channel.', traceback=True, sender=self)

    def get_opml_filter(self):
        filter = gtk.FileFilter()
        filter.add_pattern('*.opml')
        filter.add_pattern('*.xml')
        filter.set_name(_('OPML files')+' (*.opml, *.xml)')
        return filter

    def on_item_import_from_file_activate(self, widget, filename=None):
        if filename is None:
            # XXX: Hildonization?
            dlg = gtk.FileChooserDialog(title=_('Import from OPML'), parent=None, action=gtk.FILE_CHOOSER_ACTION_OPEN)
            dlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
            dlg.add_button(gtk.STOCK_OPEN, gtk.RESPONSE_OK)
            dlg.set_filter(self.get_opml_filter())
            response = dlg.run()
            filename = None
            if response == gtk.RESPONSE_OK:
                filename = dlg.get_filename()
            dlg.destroy()

        if filename is not None:
            gPodderOpmlLister(custom_title=_('Import podcasts from OPML file'), hide_url_entry=True).get_channels_from_url(filename, lambda url: self.add_new_channel(url,False,block=True), lambda: self.on_itemDownloadAllNew_activate(self.gPodder))

    def on_itemImportChannels_activate(self, widget, *args):
        gPodderOpmlLister().get_channels_from_url(gl.config.opml_url, lambda url: self.add_new_channel(url,False,block=True), lambda: self.on_itemDownloadAllNew_activate(self.gPodder))

    def on_wNotebook_switch_page(self, widget, *args):
        # The message area in the downloads tab should be hidden
        # when the user switches away from the downloads tab
        if self.message_area is not None:
            self.message_area.hide()
            self.message_area = None

    def on_treeChannels_row_activated(self, widget, path, *args):
        # double-click action of the podcast list or enter
        self.treeChannels.set_cursor(path)

    def on_treeChannels_cursor_changed(self, widget, *args):
        ( model, iter ) = self.treeChannels.get_selection().get_selected()

        if model is not None and iter is not None:
            old_active_channel = self.active_channel
            (id,) = model.get_path(iter)
            self.active_channel = self.channels[id]

            if self.active_channel == old_active_channel:
                return

            self.set_title(self.active_channel.title)
        else:
            self.active_channel = None

        self.updateTreeView()

    def on_treeAvailable_row_activated(self, widget, path=None, view_column=None):
        try:
            selection = self.treeAvailable.get_selection()
            (model, paths) = selection.get_selected_rows()

            episodes = []
            for path in paths:
                url = model.get_value(model.get_iter(path), 0)
                episode = self.active_channel.find_episode(url)
                episodes.append(episode)

            if len(episodes):
                self.show_episode_shownotes(episodes[0])
        except:
            log('Error in on_treeAvailable_row_activated', traceback=True, sender=self)

    def show_episode_shownotes(self, episode):
        def play_callback():
            self.playback_episode(episode)
        def download_callback():
            self.download_episode_list([episode])
        def delete_callback():
            self.delete_episode_list([episode])
        def close_callback():
            self.gpodder_episode_window = None

        self.gpodder_episode_window = gPodderStackableEpisode(
                episode=episode,
                download_status_manager=self.download_status_manager,
                episode_is_downloading=self.episode_is_downloading,
                download_callback=download_callback,
                play_callback=play_callback,
                delete_callback=delete_callback,
                close_callback=close_callback,
                update_episode_icon_callback=self.update_selected_episode_list_icons)

    def auto_update_procedure(self, first_run=False):
        log('auto_update_procedure() got called', sender=self)
        if not first_run and gl.config.auto_update_feeds:
            self.update_feed_cache(force_update=True)

        next_update = 60*1000*gl.config.auto_update_frequency
        gobject.timeout_add(next_update, self.auto_update_procedure)

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
            elif task.status == task.DONE:
                model.remove(model.get_iter(tree_row_reference.get_path()))

    def on_btnCancelAll_clicked(self, widget, *args):
        self.treeDownloads.get_selection().select_all()
        #self.on_treeDownloads_row_activated( self.toolCancel, None)
        self.treeDownloads.get_selection().unselect_all()

    def on_key_press(self, widget, event):
        if event.keyval == gtk.keysyms.F6:
            if self.fullscreen:
                self.gPodder.unfullscreen()
            else:
                self.gPodder.fullscreen()
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
        self.fullscreen = bool(event.new_window_state & gtk.gdk.WINDOW_STATE_FULLSCREEN)
        self.minimized = bool(event.new_window_state & gtk.gdk.WINDOW_STATE_WITHDRAWN)
    
    @dbus.service.method(gpodder.dbus_interface)
    def show_gui_window(self):
        self.gPodder.present()


class gPodderAddPodcastDialog(BuilderWidget):
    def new(self):
        if not hasattr(self, 'url_callback'):
            log('No url callback set', sender=self)
            self.url_callback = None
        if hasattr(self, 'custom_label'):
            self.label_add.set_text(self.custom_label)
        if hasattr(self, 'custom_title'):
            self.gPodderAddPodcastDialog.set_title(self.custom_title)
        if hasattr(self, 'preset_url'):
            self.entry_url.set_text(self.preset_url)
        self.gPodderAddPodcastDialog.show()

    def on_btn_paste_clicked(self, widget):
        clipboard = gtk.Clipboard()
        clipboard.request_text(self.receive_clipboard_text)

    def receive_clipboard_text(self, clipboard, text, data=None):
        if text is not None:
            self.entry_url.set_text(text)
        else:
            self.show_message(_('Nothing to paste.'), _('Clipboard is empty'))

    def on_entry_url_changed(self, widget):
        self.btn_add.set_sensitive(self.entry_url.get_text().strip() != '')

    def on_btn_add_clicked(self, widget):
        url = self.entry_url.get_text()
        self.gPodderAddPodcastDialog.destroy()
        if self.url_callback is not None:
            self.url_callback(url)
        

class gPodderMaemoPreferences(BuilderWidget):
    finger_friendly_widgets = ['btn_close', 'btn_advanced']
    audio_players = [
            ('default', 'Media Player'),
            ('panucci', 'Panucci'),
    ]
    video_players = [
            ('default', 'Media Player'),
            ('mplayer', 'MPlayer'),
    ]
    
    def new(self):
        #gl.config.connect_gtk_togglebutton('on_quit_ask', self.check_ask_on_quit)
        #gl.config.connect_gtk_togglebutton('maemo_enable_gestures', self.check_enable_gestures)
        setattr(self, 'userconfigured_player', None)
        setattr(self, 'userconfigured_videoplayer', None)

        player_selector = hildon.hildon_touch_selector_new_text()
        self.combo_player.set_selector(player_selector)
        self.combo_player.set_alignment(0.5, 0.5, 1.0, 0.0)

        videoplayer_selector = hildon.hildon_touch_selector_new_text()
        self.combo_videoplayer.set_selector(videoplayer_selector)
        self.combo_videoplayer.set_alignment(0.5, 0.5, 1.0, 0.0)

        for item in self.audio_players:
            command, caption = item
            if util.find_command(command) is None and command != 'default':
                self.audio_players.remove(item)

        for item in self.video_players:
            command, caption = item
            if util.find_command(command) is None and command != 'default':
                self.video_players.remove(item)

        # Set up the audio player combobox
        found = False
        for id, audio_player in enumerate(self.audio_players):
            command, caption = audio_player
            player_selector.append_text(caption)
            if gl.config.player == command:
                self.combo_player.set_value(caption)
                found = True
        if not found:
            player_selector.append_text('User-configured (%s)' % gl.config.player)
            self.combo_player.set_value('User-configured (%s)' % gl.config.player)
            self.userconfigured_player = gl.config.player

        # Set up the video player combobox
        found = False
        for id, video_player in enumerate(self.video_players):
            command, caption = video_player
            videoplayer_selector.append_text(caption)
            if gl.config.videoplayer == command:
                self.combo_videoplayer.set_value(caption)
                found = True
        if not found:
            videoplayer_selector.append_text('User-configured (%s)' % gl.config.videoplayer)
            self.combo_videoplayer.set_value('User-configured (%s)' % gl.config.videoplayer)
            self.userconfigured_videoplayer = gl.config.videoplayer

        self.gPodderMaemoPreferences.show()

    def on_combo_player_changed(self, combobox):
        for command, caption in self.audio_players:
            if self.combo_player.get_value() == caption:
                gl.config.player = command
                return
        if self.userconfigured_player is not None:
            gl.config.player = self.userconfigured_player

    def on_combo_videoplayer_changed(self, combobox):
        for command, caption in self.video_players:
            if self.combo_videoplayer.get_value() == caption:
                gl.config.videoplayer = command
                return
        if self.userconfigured_videoplayer is not None:
            gl.config.videoplayer = self.userconfigured_videoplayer

    def on_btn_advanced_clicked(self, widget):
        self.gPodderMaemoPreferences.destroy()
        gPodderConfigEditor()

    def on_btn_close_clicked(self, widget):
        self.gPodderMaemoPreferences.destroy()


class gPodderStackableDownloads(BuilderWidget):
    _app_menu = (
            ('btn_pause_all', maemo.Button(_('Pause all'))),
            ('btn_resume_all', maemo.Button(_('Resume all'))),
            ('btn_cancel_all', maemo.Button(_('Cancel all'))),
            ('btn_clean_up', maemo.Button(_('Clean up list'))),
    )

    def new(self):
        maemo.create_app_menu(self)
        self.downloads_list_vbox.reparent(self.main_window)
        self.downloads_list_vbox.show()

    def show(self):
        self.main_window.show()

    def on_delete_event(self, widget, event):
        self.main_window.hide()
        return True

    def on_btn_pause_all_clicked(self, widget):
        self.set_status_on_all_downloads(download.DownloadTask.PAUSED)

    def on_btn_resume_all_clicked(self, widget):
        self.set_status_on_all_downloads(download.DownloadTask.QUEUED)

    def on_btn_cancel_all_clicked(self, widget):
        self.set_status_on_all_downloads(download.DownloadTask.CANCELLED)

    def on_btn_clean_up_clicked(self, widget):
        self.cleanup_callback()


class gPodderStackableEpisode(BuilderWidget):
    _app_menu = (
            ('btn_play', maemo.Button(_('Play'))),
            ('btn_download_delete', maemo.Button(_('Download'))),
            ('btn_mark_as_new', maemo.Button(_('Do not download'))),
            ('btn_download_resume', maemo.Button(_('Pause download'))),
            ('btn_visit_website', maemo.Button(_('Open website'))),
    )

    def new(self):
        maemo.create_app_menu(self)
        self.main_window.set_title(self.episode.title)
        setattr(self, 'task', None)

        if not self.episode.link:
            self.btn_visit_website.set_sensitive(False)

        # Cover, episode title and podcast title
        cover = services.cover_downloader.get_cover(self.episode.channel)
        if cover is not None:
            cover = cover.scale_simple(100, 100, gtk.gdk.INTERP_BILINEAR)
            self.imagePodcast.set_from_pixbuf(cover)
        else:
            self.imagePodcast.hide()
        self.labelPodcast.set_alignment(0.0, 0.5)
        self.labelPodcast.set_markup('<b><big>%s</big></b>\nfrom %s' %
                (saxutils.escape(self.episode.title),
                 saxutils.escape(self.episode.channel.title)))

        # Shownotes
        b = gtk.TextBuffer()
        self.textview.set_buffer(b)
        b.insert(b.get_end_iter(), util.remove_html_tags(self.episode.description))
        self.hide_show_widgets()

    def on_delete_event(self, widget, event):
        self.close_callback()
        return False

    def download_status_changed(self, task):
        self.task = task
        self.episode.reload_from_db()
        self.hide_show_widgets()

    def download_status_progress(self):
        if self.task is None:
            return

        progress = self.task.progress
        self.progressbar.set_fraction(self.task.progress)

        if self.task.status == download.DownloadTask.QUEUED:
            long_text = _('Download is waiting in queue (%d%%)') % (100.*self.task.progress,)
            short_text = ''
        elif self.task.status == download.DownloadTask.PAUSED:
            long_text = _('Download has been paused (%d%%)') % (100.*self.task.progress,)
            short_text = '%d%%' % (100*self.progressbar.get_fraction(),)
        elif self.task.status == download.DownloadTask.FAILED:
            long_text = _('Download has failed: %s') % (self.task.error_message,)
            short_text = _('Failed')
        elif self.task.status == download.DownloadTask.CANCELLED:
            long_text = '' # Statusbar not visible
            short_text = gl.format_filesize(self.episode.length)
        else:
            # downloading
            long_text = _('Downloading: %d%% (%s/s)') % (100.*self.task.progress, gl.format_filesize(self.task.speed),)
            short_text = '%d%%' % (100*self.progressbar.get_fraction(),)

        self.progressbar.set_text(long_text)
        if self.task.status != download.DownloadTask.DONE:
            self.btn_download_delete.set_value(short_text)

    def hide_show_widgets(self):
        if self.episode.was_downloaded(and_exists=True):
            self.btn_play.set_title(_('Play'))
            self.btn_play.set_sensitive(True)
            self.btn_download_delete.set_title('Delete')
            self.btn_download_delete.set_value(gl.format_filesize(self.episode.length))
            self.btn_mark_as_new.set_title(_('Do not download'))
            self.btn_mark_as_new.set_sensitive(False)
            self.btn_mark_as_new.show()
            self.btn_download_resume.hide()
            self.progressbar.hide()
        elif self.episode_is_downloading(self.episode):
            self.btn_play.set_title(_('Play'))
            self.btn_play.set_sensitive(False)
            self.btn_download_delete.set_title('Cancel download')
            self.btn_mark_as_new.set_title(_('Do not download'))
            self.btn_mark_as_new.hide()
            self.btn_download_resume.show()
            if self.task and self.task.status == download.DownloadTask.PAUSED:
                self.btn_download_resume.set_title(_('Resume download'))
            else:
                self.btn_download_resume.set_title(_('Pause download'))
            self.progressbar.show()
        else:
            self.btn_play.set_title(_('Stream from server'))
            self.btn_play.set_sensitive(True)
            self.btn_download_delete.set_title(_('Download'))
            self.btn_download_delete.set_value(gl.format_filesize(self.episode.length))
            if self.episode.is_new(self.episode_is_downloading):
                self.btn_mark_as_new.set_title(_('Do not download'))
            else:
                self.btn_mark_as_new.set_title(_('Mark as new'))
            self.btn_mark_as_new.set_sensitive(True)
            self.btn_mark_as_new.show()
            self.btn_download_resume.hide()
            self.progressbar.hide()

    def on_btn_play_clicked(self, widget):
        self.play_callback()
    
    def on_btn_download_delete_clicked(self, widget):
        if self.episode_is_downloading(self.episode) and self.task:
            self.task.status = download.DownloadTask.CANCELLED
        elif self.episode.was_downloaded(and_exists=True):
            self.delete_callback()
        else:
            self.download_callback()
        self.update_episode_icon_callback()
        self.hide_show_widgets()

    def on_btn_mark_as_new_clicked(self, widget):
        if self.episode.is_new():
            self.episode.mark_old()
        else:
            self.episode.mark_new()
        self.update_episode_icon_callback()
        self.hide_show_widgets()

    def on_btn_visit_website_clicked(self, widget):
        util.open_website(self.episode.link)

    def on_btn_download_resume_clicked(self, widget):
        if self.task and self.task.status == download.DownloadTask.PAUSED:
            self.download_callback()
        elif self.task and self.task.status in (download.DownloadTask.DOWNLOADING, download.DownloadTask.QUEUED):
            self.task.status = download.DownloadTask.PAUSED



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

    def setup_treeview(self, tv):
        titlecell = gtk.CellRendererText()
        titlecell.set_property('ellipsize', pango.ELLIPSIZE_END)
        titlecolumn = gtk.TreeViewColumn(_('Podcast'), titlecell, markup=1)
        tv.set_property('hildon-ui-mode', 1)
        tv.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        tv.append_column(titlecolumn)

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

        model, paths = self.get_treeview(tab).get_selection().get_selected_rows()
        for path in paths:
            url = model.get_value(model.get_iter(path), 2)
            channels.append(url)

        return channels

    def thread_finished(self, model, tab=0):
        if tab == 1:
            tv = self.treeviewTopPodcastsChooser
        elif tab == 2:
            tv = self.treeviewYouTubeChooser
            self.entryYoutubeSearch.set_sensitive(True)
            self.btnSearchYouTube.set_sensitive(True)
        else:
            tv = self.treeviewChannelChooser
            self.btnDownloadOpml.set_sensitive(True)
            self.entryURL.set_sensitive(True)
            self.channels = []

        tv.set_model(model)
        tv.set_sensitive(True)

    def thread_func(self, tab=0):
        if tab == 1:
            model = opml.Importer(gl.config.toplist_url).get_model()
            if len(model) == 0:
                self.notification(_('The specified URL does not provide any valid OPML podcast items.'), _('No feeds found'))
        elif tab == 2:
            model = resolver.find_youtube_channels(self.entryYoutubeSearch.get_text())
            if len(model) == 0:
                self.notification(_('There are no YouTube channels that would match this query.'), _('No channels found'))
        else:
            url = self.entryURL.get_text()
            if not os.path.isfile(url) and not url.lower().startswith('http://'):
                log('Using podcast.de search')
                url = 'http://api.podcast.de/opml/podcasts/suche/%s' % (urllib.quote(url),)
            model = opml.Importer(url).get_model()
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
        self.treeviewChannelChooser.set_sensitive( False)
        Thread( target = self.thread_func).start()
        Thread( target = lambda: self.thread_func(1)).start()

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
        self.get_treeview().get_selection().select_all()
    
    def on_btnSelectNone_clicked(self, widget, *args):
        self.get_treeview().get_selection().unselect_all()

    def on_btnOK_clicked(self, widget, *args):
        self.channels = self.get_selected_channels()
        self.gPodderOpmlLister.destroy()

        # add channels that have been selected
        for url in self.channels:
            if self.callback_for_channel:
                self.callback_for_channel( url)

        if self.callback_finished:
            util.idle_add(self.callback_finished)

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

class gPodderEpisodeSelector( BuilderWidget):
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
                 (default is [('title_and_description', None, None, 'Episode'),])
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
    """
    finger_friendly_widgets = [ 'btnOK', 'btnCheckAll', 'btnCheckNone', 'treeviewEpisodes']
    
    COLUMN_INDEX = 0
    COLUMN_TOOLTIP = 1
#    COLUMN_TOGGLE = 2
    COLUMN_ADDITIONAL = 2

    def new( self):
        self.treeviewEpisodes.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        gl.config.connect_gtk_window(self.gPodderEpisodeSelector, 'episode_selector', True)
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

        if not hasattr( self, 'selection_buttons'):
            self.selection_buttons = {}

        if not hasattr( self, 'selected_default'):
            self.selected_default = False

        if not hasattr( self, 'selected'):
            self.selected = [self.selected_default]*len(self.episodes)

        if len(self.selected) < len(self.episodes):
            self.selected += [self.selected_default]*(len(self.episodes)-len(self.selected))

        if not hasattr( self, 'columns'):
            self.columns = (('title_and_description', None, None, _('Episode')),)

        if hasattr( self, 'title'):
            self.gPodderEpisodeSelector.set_title( self.title)

        if hasattr(self, 'stock_ok_button'):
            if self.stock_ok_button == 'gpodder-download':
                #self.btnOK.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_DOWN, gtk.ICON_SIZE_BUTTON))
                self.btnOK.set_title(_('Download'))
            else:
                self.btnOK.set_title(self.stock_ok_button)
                self.btnOK.set_use_stock(True)

        # check/uncheck column
#        toggle_cell = gtk.CellRendererToggle()
#        toggle_cell.connect( 'toggled', self.toggle_cell_handler)
#        self.treeviewEpisodes.append_column( gtk.TreeViewColumn( '', toggle_cell, active=self.COLUMN_TOGGLE))
        
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

        column_types = [ gobject.TYPE_INT, gobject.TYPE_STRING ]
        # add string column type plus sort column type if it exists
        for name, sort_name, sort_type, caption in self.columns:
            column_types.append(gobject.TYPE_STRING)
            if sort_name is not None:
                column_types.append(sort_type)
        self.model = gtk.ListStore( *column_types)

        for index, episode in enumerate( self.episodes):
            row = [ index, None ]
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

        self.treeviewEpisodes.connect('button-press-event', self.treeview_episodes_button_pressed)
        self.treeviewEpisodes.set_rules_hint( True)
        self.treeviewEpisodes.set_model( self.model)
        self.treeviewEpisodes.columns_autosize()

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
            menu.popup(None, None, None, event.button, event.time)

            return True

    def calculate_total_size( self):
        if self.size_attribute is not None:
            (total_size, count) = (0, 0)
            for episode in self.get_selected_episodes():
                try:
                    total_size += int(getattr( episode, self.size_attribute))
                    count += 1
                except:
                    log( 'Cannot get size for %s', episode.title, sender = self)

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

    def custom_selection_button_clicked(self, button, label):
        callback = self.selection_buttons[label]

        for index, row in enumerate( self.model):
            new_value = callback( self.episodes[index])
            self.model.set_value( row.iter, self.COLUMN_TOGGLE, new_value)

    def on_btnCheckAll_clicked( self, widget):
        self.treeviewEpisodes.get_selection().select_all()

    def on_btnCheckNone_clicked( self, widget):
        self.treeviewEpisodes.get_selection().unselect_all()

    def on_remove_action_activate(self, widget):
        episodes = self.get_selected_episodes(remove_episodes=True)

        urls = []
        for episode in episodes:
            urls.append(episode.url)
            self.remove_callback(episode)

        if self.remove_finished is not None:
            self.remove_finished(urls)

    def get_selected_episodes( self, remove_episodes=False):
        selected_episodes = []

        model, paths = self.treeviewEpisodes.get_selection().get_selected_rows()

        for path in paths:
            index = model.get_value(model.get_iter(path), self.COLUMN_INDEX)
            selected_episodes.append(self.episodes[index])

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
        selected_episodes = self.get_selected_episodes()
        self.gPodderEpisodeSelector.destroy()
        if self.callback is not None:
            self.callback(selected_episodes)

    def on_btnCancel_clicked( self, widget):
        self.gPodderEpisodeSelector.destroy()
        if self.callback is not None:
            self.callback([])

class gPodderConfigEditor(BuilderWidget):
    finger_friendly_widgets = ['btnShowAll', 'btnClose', 'configeditor']
    
    def new(self):
        name_column = gtk.TreeViewColumn(_('Setting'))
        name_renderer = gtk.CellRendererText()
        name_column.pack_start(name_renderer)
        name_column.add_attribute(name_renderer, 'text', 0)
        name_column.add_attribute(name_renderer, 'style', 5)
        self.configeditor.append_column(name_column)

        value_column = gtk.TreeViewColumn(_('Set to'))
        value_check_renderer = gtk.CellRendererToggle()
        value_column.pack_start(value_check_renderer, expand=False)
        value_column.add_attribute(value_check_renderer, 'active', 7)
        value_column.add_attribute(value_check_renderer, 'visible', 6)
        value_column.add_attribute(value_check_renderer, 'activatable', 6)
        value_check_renderer.connect('toggled', self.value_toggled)

        value_renderer = gtk.CellRendererText()
        value_column.pack_start(value_renderer)
        value_column.add_attribute(value_renderer, 'text', 2)
        value_column.add_attribute(value_renderer, 'visible', 4)
        value_column.add_attribute(value_renderer, 'editable', 4)
        value_column.add_attribute(value_renderer, 'style', 5)
        value_renderer.connect('edited', self.value_edited)
        self.configeditor.append_column(value_column)

        self.model = gl.config.model()
        self.filter = self.model.filter_new()
        self.filter.set_visible_func(self.visible_func)

        self.configeditor.set_model(self.filter)
        self.configeditor.set_rules_hint(True)
        self.configeditor.get_selection().connect( 'changed',
            self.on_configeditor_row_changed )

    def visible_func(self, model, iter, user_data=None):
        text = self.entryFilter.get_text().lower()
        if text == '':
            return True
        else:
            # either the variable name or its value
            return (text in model.get_value(iter, 0).lower() or
                    text in model.get_value(iter, 2).lower())

    def value_edited(self, renderer, path, new_text):
        model = self.configeditor.get_model()
        iter = model.get_iter(path)
        name = model.get_value(iter, 0)
        type_cute = model.get_value(iter, 1)

        if not gl.config.update_field(name, new_text):
            self.notification(_('Cannot set value of <b>%s</b> to <i>%s</i>.\n\nNeeded data type: %s') % (saxutils.escape(name), saxutils.escape(new_text), saxutils.escape(type_cute)), _('Error updating %s') % saxutils.escape(name))
    
    def value_toggled(self, renderer, path):
        model = self.configeditor.get_model()
        iter = model.get_iter(path)
        field_name = model.get_value(iter, 0)
        field_type = model.get_value(iter, 3)

        # Flip the boolean config flag
        if field_type == bool:
            gl.config.toggle_flag(field_name)
    
    def on_entryFilter_changed(self, widget):
        self.filter.refilter()

    def on_btnShowAll_clicked(self, widget):
        self.entryFilter.set_text('')
        self.entryFilter.grab_focus()

    def on_btnClose_clicked(self, widget):
        self.gPodderConfigEditor.destroy()

    def on_configeditor_row_changed(self, treeselection):
        model, iter = treeselection.get_selected()
        if iter is not None:
            option_name = gl.config.get_description( model.get(iter, 0)[0] )
            self.config_option_description_label.set_text(option_name)


class gPodderWelcome(BuilderWidget):
    def new(self):
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

    uibase.GtkBuilderWidget.use_fingerscroll = True
    gp = gPodder(bus_name)
    gp.run()



