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

import os
import gtk
import gtk.gdk
import gobject
import pango
import sys
import shutil
import webbrowser

from xml.sax import saxutils

from threading import Event
from threading import Thread
from string import strip

from gpodder import util
from gpodder import opml
from gpodder import services
from gpodder import download
from gpodder import SimpleGladeApp

from libpodcasts import podcastChannel
from libpodcasts import channelsToModel
from libpodcasts import load_channels
from libpodcasts import save_channels

from libgpodder import gPodderLib
from liblogger import log

from libplayers import UserAppsReader

from libipodsync import gPodder_iPodSync
from libipodsync import gPodder_FSSync
from libipodsync import ipod_supported

from libtagupdate import tagging_supported

app_name = "gpodder"
app_version = "unknown" # will be set in main() call
app_authors = [ 'Thomas Perl <thp@perli.net' ]
app_copyright = 'Copyright (c) 2005-2007 Thomas Perl'
app_website = 'http://gpodder.berlios.de/'

# these will be filled with pathnames in bin/gpodder
glade_dir = [ 'share', 'gpodder' ]
icon_dir = [ 'share', 'pixmaps', 'gpodder.png' ]
scalable_dir = [ 'share', 'icons', 'hicolor', 'scalable', 'apps', 'gpodder.svg' ]


class GladeWidget(SimpleGladeApp.SimpleGladeApp):
    gpodder_main_window = None

    def __init__( self, **kwargs):
        path = os.path.join( glade_dir, '%s.glade' % app_name)
        root = self.__class__.__name__
        domain = app_name

        SimpleGladeApp.SimpleGladeApp.__init__( self, path, root, domain, **kwargs)

        if root == 'gPodder':
            GladeWidget.gpodder_main_window = self.gPodder
        else:
            # If we have a child window, set it transient for our main window
            getattr( self, root).set_transient_for( GladeWidget.gpodder_main_window)
            getattr( self, root).set_position( gtk.WIN_POS_CENTER_ON_PARENT)

    def show_message( self, message, title = None):
        dlg = gtk.MessageDialog( GladeWidget.gpodder_main_window, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK)

        if title:
            dlg.set_title( title)
            dlg.set_markup( '<span weight="bold" size="larger">%s</span>\n\n%s' % ( title, message ))
        else:
            dlg.set_markup( '<span weight="bold" size="larger">%s</span>' % ( message ))
        
        dlg.run()
        dlg.destroy()

    def show_confirmation( self, message, title = None):
        dlg = gtk.MessageDialog( GladeWidget.gpodder_main_window, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO)

        if title:
            dlg.set_title( title)
            dlg.set_markup( '<span weight="bold" size="larger">%s</span>\n\n%s' % ( title, message ))
        else:
            dlg.set_markup('<span weight="bold" size="larger">%s</span>' % message)

        response = dlg.run()
        dlg.destroy()
        
        return response == gtk.RESPONSE_YES



class gPodder(GladeWidget):
    def new(self):
        self.uar = None

        gl = gPodderLib()
        self.gPodder.resize( gl.main_window_width, gl.main_window_height)
        self.gPodder.move( gl.main_window_x, gl.main_window_y)
        self.channelPaned.set_position( gl.paned_position)
        while gtk.events_pending():
            gtk.main_iteration( False)

        if app_version.rfind( "svn") != -1:
            self.gPodder.set_title( 'gPodder %s' % app_version)

        self.default_title = self.gPodder.get_title()

        # cell renderers for channel tree
        namecolumn = gtk.TreeViewColumn( _('Channel'))

        iconcell = gtk.CellRendererPixbuf()
        namecolumn.pack_start( iconcell, False)
        namecolumn.add_attribute( iconcell, 'pixbuf', 8)

        namecell = gtk.CellRendererText()
        namecell.set_property('ellipsize', pango.ELLIPSIZE_END)
        namecolumn.pack_start( namecell, True)
        namecolumn.add_attribute( namecell, 'markup', 7)
        namecolumn.add_attribute( namecell, 'weight', 4)

        newcell = gtk.CellRendererText()
        namecolumn.pack_end( newcell, False)
        namecolumn.add_attribute( newcell, 'text', 5)
        namecolumn.add_attribute( newcell, 'weight', 4)

        self.treeChannels.append_column( namecolumn)

        # enable alternating colors hint
        self.treeAvailable.set_rules_hint( True)
        self.treeChannels.set_rules_hint( True)

        # Add our context menu to treeAvailable
        self.treeAvailable.connect('button-press-event', self.treeview_button_pressed)
        self.treeChannels.connect('button-press-event', self.treeview_channels_button_pressed)

        iconcell = gtk.CellRendererPixbuf()
        iconcolumn = gtk.TreeViewColumn( _("Status"), iconcell, pixbuf = 4)

        namecell = gtk.CellRendererText()
        #namecell.set_property('ellipsize', pango.ELLIPSIZE_END)
        namecolumn = gtk.TreeViewColumn( _("Episode"), namecell, text = 1)
        namecolumn.set_sizing( gtk.TREE_VIEW_COLUMN_AUTOSIZE)

        sizecell = gtk.CellRendererText()
        sizecolumn = gtk.TreeViewColumn( _("Size"), sizecell, text=2)

        releasecell = gtk.CellRendererText()
        releasecolumn = gtk.TreeViewColumn( _("Released"), releasecell, text=5)
        
        desccell = gtk.CellRendererText()
        desccell.set_property('ellipsize', pango.ELLIPSIZE_END)
        desccolumn = gtk.TreeViewColumn( _("Description"), desccell, text=6)

        for itemcolumn in ( iconcolumn, namecolumn, sizecolumn, releasecolumn, desccolumn ):
            itemcolumn.set_resizable( True)
            itemcolumn.set_reorderable( True)
            self.treeAvailable.append_column( itemcolumn)

        # enable search in treeavailable
        self.treeAvailable.set_search_equal_func( self.treeAvailable_search_equal)

        # enable multiple selection support
        self.treeAvailable.get_selection().set_mode( gtk.SELECTION_MULTIPLE)
        self.treeDownloads.get_selection().set_mode( gtk.SELECTION_MULTIPLE)
        
        # columns and renderers for "download progress" tab
        episodecell = gtk.CellRendererText()
        episodecolumn = gtk.TreeViewColumn( _("Episode"), episodecell, text=0)
        
        speedcell = gtk.CellRendererText()
        speedcolumn = gtk.TreeViewColumn( _("Speed"), speedcell, text=1)
        
        progresscell = gtk.CellRendererProgress()
        progresscolumn = gtk.TreeViewColumn( _("Progress"), progresscell, value=2)
        
        for itemcolumn in ( episodecolumn, speedcolumn, progresscolumn ):
            self.treeDownloads.append_column( itemcolumn)

        services.download_status_manager.register( 'list-changed', self.download_status_updated)
        services.download_status_manager.register( 'progress-changed', self.download_progress_updated)

        self.treeDownloads.set_model( services.download_status_manager.tree_model)
        
        #Add Drag and Drop Support
        flags = gtk.DEST_DEFAULT_ALL
        targets = [ ('text/plain', 0, 2), ('STRING', 0, 3), ('TEXT', 0, 4) ]
        actions = gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_COPY
        self.treeChannels.drag_dest_set( flags, targets, actions)
        self.treeChannels.connect( 'drag_data_received', self.drag_data_received)

        # Subscribed channels
        self.active_channel = None
        self.channels = load_channels( load_items = False, offline = True)

        # load list of user applications
        self.user_apps_reader = UserAppsReader()
        Thread( target = self.user_apps_reader.read).start()

        # Clean up old, orphaned download files
        gl.clean_up_downloads( delete_partial = True)

        # Now, update the feed cache, when everything's in place
        self.update_feed_cache( force_update = gl.update_on_startup)

    def treeview_channels_button_pressed( self, treeview, event):
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

            channel_title = model.get_value( model.get_iter( paths[0]), 1)
            item = gtk.ImageMenuItem('')
            ( label, image ) = item.get_children()
            label.set_text( _('Edit %s') % channel_title)
            item.set_image( gtk.image_new_from_stock( gtk.STOCK_EDIT, gtk.ICON_SIZE_MENU))
            item.connect( 'activate', self.on_itemEditChannel_activate)
            menu.append( item)

            item = gtk.ImageMenuItem( _('Remove %s') % ( channel_title, ))
            item.set_image( gtk.image_new_from_stock( gtk.STOCK_DELETE, gtk.ICON_SIZE_MENU))
            item.connect( 'activate', self.on_itemRemoveChannel_activate)
            menu.append( item)

            menu.show_all()
            menu.popup( None, None, None, event.button, event.time)

            return True

    def treeview_button_pressed( self, treeview, event):
        if event.button == 3:
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

            first_url = model.get_value( model.get_iter( paths[0]), 0)

            menu = gtk.Menu()

            ( can_play, can_download, can_transfer, can_cancel ) = self.play_or_download()

            if len(paths) == 1:
                # Single item, add episode information menu item
                episode_title = model.get_value( model.get_iter( paths[0]), 1)
                if len(episode_title) > 30:
                    episode_title = episode_title[:27] + '...'
                item = gtk.ImageMenuItem('')
                ( label, image ) = item.get_children()
                label.set_text( _('Episode information: %s') % episode_title)
                item.set_image( gtk.image_new_from_stock( gtk.STOCK_INFO, gtk.ICON_SIZE_MENU))
                item.connect( 'activate', lambda w: self.on_treeAvailable_row_activated( self.treeAvailable))
                menu.append( item)
                menu.append( gtk.SeparatorMenuItem())
            else:
                episode_title = _('%d selected episodes') % len(paths)

            if can_play:
                item = gtk.ImageMenuItem( _('Play %s') % episode_title)
                item.set_image( gtk.image_new_from_stock( gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_MENU))
                item.connect( 'activate', lambda w: self.on_treeAvailable_row_activated( self.toolPlay))
                menu.append( item)
                item = gtk.ImageMenuItem( _('Remove %s') % episode_title)
                item.set_image( gtk.image_new_from_stock( gtk.STOCK_DELETE, gtk.ICON_SIZE_MENU))
                item.connect( 'activate', self.on_btnDownloadedDelete_clicked)
                menu.append( item)

            if can_download:
                item = gtk.ImageMenuItem( _('Download %s') % episode_title)
                item.set_image( gtk.image_new_from_stock( gtk.STOCK_GO_DOWN, gtk.ICON_SIZE_MENU))
                item.connect( 'activate', lambda w: self.on_treeAvailable_row_activated( self.toolDownload))
                menu.append( item)

                menu.append( gtk.SeparatorMenuItem())
                is_downloaded = gPodderLib().history_is_downloaded( first_url)
                if is_downloaded:
                    item = gtk.ImageMenuItem( _('Mark %s as not downloaded') % episode_title)
                    item.set_image( gtk.image_new_from_stock( gtk.STOCK_UNDELETE, gtk.ICON_SIZE_MENU))
                    item.connect( 'activate', lambda w: self.on_item_toggle_downloaded_activate( w, False, False))
                    menu.append( item)
                else:
                    item = gtk.ImageMenuItem( _('Mark %s as deleted') % episode_title)
                    item.set_image( gtk.image_new_from_stock( gtk.STOCK_DELETE, gtk.ICON_SIZE_MENU))
                    item.connect( 'activate', lambda w: self.on_item_toggle_downloaded_activate( w, False, True))
                    menu.append( item)

            if can_transfer:
                item = gtk.ImageMenuItem( _('Transfer %s to %s') % ( episode_title, gPodderLib().get_device_name() ))
                item.set_image( gtk.image_new_from_stock( gtk.STOCK_NETWORK, gtk.ICON_SIZE_MENU))
                item.connect( 'activate', lambda w: self.on_treeAvailable_row_activated( self.toolTransfer))
                menu.append( item)

            if can_play:
                menu.append( gtk.SeparatorMenuItem())
                is_played = gPodderLib().history_is_played( first_url)
                if is_played:
                    item = gtk.ImageMenuItem( _('Mark %s as unplayed') % episode_title)
                    item.set_image( gtk.image_new_from_stock( gtk.STOCK_CANCEL, gtk.ICON_SIZE_MENU))
                    item.connect( 'activate', lambda w: self.on_item_toggle_played_activate( w, False, False))
                    menu.append( item)
                else:
                    item = gtk.ImageMenuItem( _('Mark %s as played') % episode_title)
                    item.set_image( gtk.image_new_from_stock( gtk.STOCK_APPLY, gtk.ICON_SIZE_MENU))
                    item.connect( 'activate', lambda w: self.on_item_toggle_played_activate( w, False, True))
                    menu.append( item)

            if can_cancel:
                item = gtk.ImageMenuItem( _('_Cancel download'))
                item.set_image( gtk.image_new_from_stock( gtk.STOCK_STOP, gtk.ICON_SIZE_MENU))
                item.connect( 'activate', lambda w: self.on_treeDownloads_row_activated( self.toolCancel))
                menu.append( item)

            menu.show_all()
            menu.popup( None, None, None, event.button, event.time)

            return True

    def download_progress_updated( self, count, percentage):
        title = [ self.default_title ]

        if count == 1:
            title.append( _('downloading one file'))
        elif count > 1:
            title.append( _('downloading %d files') % count)

        if len(title) == 2:
            title[1] = ''.join( [ title[1], ' (%d%%)' % ( percentage, ) ])

        self.gPodder.set_title( ' - '.join( title))

    def playback_episode( self, current_channel, current_podcast):
        ( success, application ) = gPodderLib().playback_episode( current_channel, current_podcast)
        if not success:
            self.show_message( _('The selected player application cannot be found. Please check your media player settings in the preferences dialog.'), _('Error opening player: %s') % ( saxutils.escape( application), ))
        self.download_status_updated()

    def treeAvailable_search_equal( self, model, column, key, iter, data = None):
        if model == None:
            return True

        key = key.lower()

        # columns, as defined in libpodcasts' get model method
        # 1 = episode title, 7 = description
        columns = (1, 7)

        for column in columns:
            value = model.get_value( iter, column).lower()
            if value.find( key) != -1:
                return False

        return True

    def play_or_download( self):
        if self.wNotebook.get_current_page() > 0:
            return

        ( can_play, can_download, can_transfer, can_cancel ) = (False,)*4

        selection = self.treeAvailable.get_selection()
        if selection.count_selected_rows() > 0:
            (model, paths) = selection.get_selected_rows()
         
            for path in paths:
                url = model.get_value( model.get_iter( path), 0)
                local_filename = model.get_value( model.get_iter( path), 8)

                if os.path.exists( local_filename):
                    can_play = True
                else:
                    if services.download_status_manager.is_download_in_progress( url):
                        can_cancel = True
                    else:
                        can_download = True

                if util.file_type_by_extension( util.file_extension_from_url( url)) == 'torrent':
                    can_download = can_download or gPodderLib().use_gnome_bittorrent

        can_download = can_download and not can_cancel
        can_play = can_play and not can_cancel and not can_download
        can_transfer = can_play and gPodderLib().device_type != 'none'

        self.toolPlay.set_sensitive( can_play)
        self.toolDownload.set_sensitive( can_download)
        self.toolTransfer.set_sensitive( can_transfer)
        self.toolCancel.set_sensitive( can_cancel)

        return ( can_play, can_download, can_transfer, can_cancel )

    def download_status_updated( self):
        count = services.download_status_manager.count()
        if count:
            self.labelDownloads.set_text( _('Downloads (%d)') % count)
        else:
            self.labelDownloads.set_text( _('Downloads'))

        for channel in self.channels:
            channel.update_model()

        self.updateComboBox()

    def updateComboBox( self):
        ( model, iter ) = self.treeChannels.get_selection().get_selected()

        if model and iter:
            selected = model.get_path( iter)
        else:
            selected = (0,)

        rect = self.treeChannels.get_visible_rect()
        self.treeChannels.set_model( channelsToModel( self.channels))
        self.treeChannels.scroll_to_point( rect.x, rect.y)
        while gtk.events_pending():
            gtk.main_iteration( False)
        self.treeChannels.scroll_to_point( rect.x, rect.y)

        try:
            self.treeChannels.get_selection().select_path( selected)
        except:
            log( 'Cannot set selection on treeChannels', sender = self)
        self.on_treeChannels_cursor_changed( self.treeChannels)
    
    def updateTreeView( self):
        gl = gPodderLib()

        if self.channels:
            self.treeAvailable.set_model( self.active_channel.tree_model)
            self.treeAvailable.columns_autosize()
            self.play_or_download()
        else:
            if self.treeAvailable.get_model():
                self.treeAvailable.get_model().clear()
    
    def drag_data_received(self, widget, context, x, y, sel, ttype, time):
        result = sel.data
        self.add_new_channel( result)

    def add_new_channel( self, result = None, ask_download_new = True):
        result = util.normalize_feed_url( result)

        if result:
            for old_channel in self.channels:
                if old_channel.url == result:
                    self.show_message( _('You have already subscribed to this channel: %s') % ( saxutils.escape( old_channel.title), ), _('Already added'))
                    log( 'Channel already exists: %s', result)
                    # Select the existing channel in combo box
                    for i in range( len( self.channels)):
                        if self.channels[i] == old_channel:
                            self.treeChannels.get_selection().set_selected( (i,))
                    return
            log( 'Adding new channel: %s', result)
            try:
                channel = podcastChannel.get_by_url( url = result, force_update = True)
            except:
                channel = None

            if channel:
                self.channels.append( channel)
                save_channels( self.channels)
                # download changed channels
                self.update_feed_cache( force_update = False)

                (username, password) = util.username_password_from_url( result)
                if username and self.show_confirmation( _('You have supplied <b>%s</b> as username and a password for this feed. Would you like to use the same authentication data for downloading episodes?') % ( saxutils.escape( username), ), _('Password authentication')):
                    channel.username = username
                    channel.password = password
                    log('Saving authentication data for episode downloads..', sender = self)
                    channel.save_settings()

                # ask user to download some new episodes
                self.treeChannels.get_selection().set_selected( (len( self.channels)-1,))
                if ask_download_new:
                    self.on_btnDownloadNewer_clicked( None)
            else:
                title = _('Error adding channel')
                message = _('The channel could not be added. Please check the spelling of the URL or try again later.')
                self.show_message( message, title)
        else:
            if result:
                title = _('URL scheme not supported')
                message = _('gPodder currently only supports URLs starting with <b>http://</b>, <b>feed://</b> or <b>ftp://</b>.')
                self.show_message( message, title)
    
    def sync_to_ipod_proc( self, sync, episodes = None):
        if not sync.open():
            sync.close( success = False, access_error = True)
            return False

        if episodes == None:
            i = 0
            available_channels = [ c.load_downloaded_episodes() for c in self.channels ]
            downloaded_channels = [ c for c in available_channels if len(c) ]
            for channel in downloaded_channels:
                sync.set_progress_overall( i, len(downloaded_channels))
                channel.load_settings()
                sync.sync_channel( channel, sync_played_episodes = not gPodderLib().only_sync_not_played)
                i += 1
            sync.set_progress_overall( i, len(downloaded_channels))
        else:
            sync.sync_channel( self.active_channel, episodes, True)

        sync.close( success = not sync.cancelled)
        gobject.idle_add( self.updateTreeView)

    def ipod_cleanup_proc( self, sync):
        if not sync.open():
            gobject.idle_add( self.show_message, message, title)
            sync.close( success = False, access_error = True)
            return False

        sync.clean_playlist()
        sync.close( success = not sync.cancelled, cleaned = True)
        gobject.idle_add( self.updateTreeView)

    def update_feed_cache_callback( self, label, progressbar, position, count):
        if len(self.channels) > position:
            title = _('Updating %s') % saxutils.escape( self.channels[position].title)
        else:
            title = _('Please wait...')

        label.set_markup( '<i>%s</i>' % title)

        progressbar.set_text( _('%d of %d channels updated') % ( position, count ))
        if count:
            progressbar.set_fraction( ((1.00*position) / (1.00*count)))

    def update_feed_cache_proc( self, force_update, callback_proc = None, callback_error = None, finish_proc = None):
        self.channels = load_channels( force_update = force_update, callback_proc = callback_proc, callback_error = callback_error, offline = not force_update)
        if finish_proc:
            finish_proc()

    def update_feed_cache(self, force_update = True):
        title = _('Downloading podcast feeds')
        heading = _('Downloading feeds')
        body = _('Podcast feeds contain channel metadata and information about current episodes.')
        
        please_wait = gtk.Dialog( title, self.gPodder, gtk.DIALOG_MODAL, ( gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, ))
        please_wait.set_transient_for( self.gPodder)
        please_wait.set_position( gtk.WIN_POS_CENTER_ON_PARENT)
        please_wait.vbox.set_spacing( 5)
        please_wait.set_border_width( 10)
        please_wait.set_resizable( False)
        
        label_heading = gtk.Label()
        label_heading.set_alignment( 0.0, 0.5)
        label_heading.set_markup( '<span weight="bold" size="larger">%s</span>' % heading)
        
        label_body = gtk.Label()
        label_body.set_text( body)
        label_body.set_alignment( 0.0, 0.5)
        label_body.set_line_wrap( True)
        
        myprogressbar = gtk.ProgressBar()
        
        mylabel = gtk.Label()
        mylabel.set_alignment( 0.0, 0.5)
        mylabel.set_ellipsize( pango.ELLIPSIZE_END)
        
        # put it all together
        please_wait.vbox.pack_start( label_heading)
        please_wait.vbox.pack_start( label_body)
        please_wait.vbox.pack_start( myprogressbar)
        please_wait.vbox.pack_end( mylabel)
        please_wait.show_all()

        # center the dialog on the gPodder main window
        ( x, y ) = self.gPodder.get_position()
        ( w, h ) = self.gPodder.get_size()
        ( pw, ph ) = please_wait.get_size()
        please_wait.move( x + w/2 - pw/2, y + h/2 - ph/2)
        
        # hide separator line
        please_wait.set_has_separator( False)
        
        # let's get down to business..
        callback_proc = lambda pos, count: gobject.idle_add( self.update_feed_cache_callback, mylabel, myprogressbar, pos, count)
        callback_error = lambda x: gobject.idle_add( self.show_message, x)
        finish_proc = lambda: gobject.idle_add( please_wait.destroy)

        args = ( force_update, callback_proc, callback_error, finish_proc, )

        thread = Thread( target = self.update_feed_cache_proc, args = args)
        thread.start()

        please_wait.run()

        self.updateComboBox()
        
        # download all new?
        if force_update and gPodderLib().download_after_update:
            self.on_itemDownloadAllNew_activate( self.gPodder)

    def download_podcast_by_url( self, url, want_message_dialog = True, widget = None):
        if self.active_channel == None:
            return

        current_channel = self.active_channel
        current_podcast = current_channel.find_episode( url)
        filename = current_podcast.local_filename()

        if widget:
            if (widget.get_name() == 'itemPlaySelected' or widget.get_name() == 'toolPlay') and os.path.exists( filename):
                # addDownloadedItem just to make sure the episode is marked correctly in localdb
                current_channel.addDownloadedItem( current_podcast)
                # open the file now
                if current_podcast.file_type() != 'torrent':
                    self.playback_episode( current_channel, current_podcast)
                return
         
            if widget.get_name() == 'treeAvailable':
                play_callback = lambda: self.playback_episode( current_channel, current_podcast)
                download_callback = lambda: self.download_podcast_by_url( url, want_message_dialog, None)
                gpe = gPodderEpisode( episode = current_podcast, channel = current_channel, download_callback = download_callback, play_callback = play_callback, center_on_widget = self.treeAvailable)
                return
        
        if not os.path.exists( filename) and not services.download_status_manager.is_download_in_progress( current_podcast.url):
            download.DownloadThread( current_channel, current_podcast).start()
        else:
            if want_message_dialog and os.path.exists( filename) and not current_podcast.file_type() == 'torrent':
                title = _('Episode already downloaded')
                message = _('You have already downloaded this episode. Click on the episode to play it.')
                self.show_message( message, title)
            elif want_message_dialog and not current_podcast.file_type() == 'torrent':
                title = _('Download in progress')
                message = _('You are currently downloading this episode. Please check the download status tab to check when the download is finished.')
                self.show_message( message, title)

            if os.path.exists( filename):
                log( 'Episode has already been downloaded.')
                current_channel.addDownloadedItem( current_podcast)
                self.updateComboBox()

    def close_gpodder(self, widget, *args):
        if self.channels:
            save_channels( self.channels)

        services.download_status_manager.cancel_all()

        gl = gPodderLib()

        size = self.gPodder.get_size()
        pos = self.gPodder.get_position()
        gl.main_window_width = size[0]
        gl.main_window_height = size[1]
        gl.main_window_x = pos[0]
        gl.main_window_y = pos[1]
        gl.paned_position = self.channelPaned.get_position()
        gl.propertiesChanged()

        self.gtk_main_quit()
        sys.exit( 0)

    def for_each_selected_episode_url( self, callback):
        ( model, paths ) = self.treeAvailable.get_selection().get_selected_rows()
        for path in paths:
            url = model.get_value( model.get_iter( path), 0)
            try:
                callback( url)
            except:
                log( 'Warning: Error in for_each_selected_episode_url for URL %s', url, sender = self)
        self.active_channel.update_model()
        self.updateComboBox()

    def on_item_toggle_downloaded_activate( self, widget, toggle = True, new_value = False):
        if toggle:
            callback = lambda url: gPodderLib().history_mark_downloaded( url, not gPodderLib().history_is_downloaded( url))
        else:
            callback = lambda url: gPodderLib().history_mark_downloaded( url, new_value)

        self.for_each_selected_episode_url( callback)

    def on_item_toggle_played_activate( self, widget, toggle = True, new_value = False):
        if toggle:
            callback = lambda url: gPodderLib().history_mark_played( url, not gPodderLib().history_is_played( url))
        else:
            callback = lambda url: gPodderLib().history_mark_played( url, new_value)

        self.for_each_selected_episode_url( callback)

    def on_itemUpdate_activate(self, widget, *args):
        if self.channels:
            self.update_feed_cache()
        else:
            title = _('No channels available')
            message = _('You need to subscribe to some podcast feeds before you can start downloading podcasts. Use your favorite search engine to look for interesting podcasts.')
            self.show_message( message, title)

    def on_itemDownloadAllNew_activate(self, widget, *args):
        to_download = []

        message_part = ''
        new_sum = 0

        for channel in self.channels:
            new_episodes = channel.get_new_episodes()
            for episode in new_episodes:
                to_download.append( ( channel, episode ))

            if len(new_episodes):
                if len(new_episodes) == 1:
                    new_part = '  ' + _('<b>1</b> new episode in <b>%s</b>') % ( saxutils.escape(channel.title), )
                else:
                    new_part = '  ' + _('<b>%d</b> new episodes in <b>%s</b>') % ( len( new_episodes), saxutils.escape(channel.title), )

                message_part += new_part + "\n"
                new_sum += len(new_episodes)

        if to_download:
            title = _('New episodes available')

            if new_sum == 1:
                title = _('New episode available')

            message = _('New episodes are available to be downloaded:\n\n%s\nDo you want to download these episodes now?') % ( message_part, )

            if self.show_confirmation( message, title):
                for channel, episode in to_download:
                    filename = episode.local_filename()
                    if not os.path.exists( filename) and not services.download_status_manager.is_download_in_progress( episode.url):
                        download.DownloadThread( channel, episode).start()
        else:
            title = _('No new episodes')
            message = _('There are no new episodes to download from your podcast subscriptions. Please check for new episodes later.')
            self.show_message( message, title)

    def on_sync_to_ipod_activate(self, widget, *args):
        gl = gPodderLib()
        if gl.device_type == 'none':
            title = _('No device configured')
            message = _('To use the synchronization feature, please configure your device in the preferences dialog first.')
            self.show_message( message, title)
            return

        if gl.device_type == 'ipod' and not ipod_supported():
            title = _('Libraries needed: gpod, pymad')
            message = _('To use the iPod synchronization feature, you need to install the <b>python-gpod</b> and <b>python-pymad</b> libraries from your distribution vendor. More information about the needed libraries can be found on the gPodder website.')
            self.show_message( message, title)
            return
        
        if gl.device_type in [ 'ipod', 'filesystem' ]:
            sync_class = None

            if gl.device_type == 'filesystem':
                sync_class = gPodder_FSSync
            elif gl.device_type == 'ipod':
                sync_class = gPodder_iPodSync

            if not sync_class:
                return

            sync_win = gPodderSync()
            sync = sync_class( callback_status = sync_win.set_status, callback_progress = sync_win.set_progress, callback_done = sync_win.close)
            sync_win.set_sync_object( sync)
            thread_args = [ sync ]
            if widget == None:
                thread_args.append( args[0])
            thread = Thread( target = self.sync_to_ipod_proc, args = thread_args)
            thread.start()

    def on_cleanup_ipod_activate(self, widget, *args):
        gl = gPodderLib()
        if gl.device_type == 'none':
            title = _('No device configured')
            message = _('To use the synchronization feature, please configure your device in the preferences dialog first.')
            self.show_message( message, title)
            return

        if gl.device_type == 'ipod' and not ipod_supported():
            title = _('Libraries needed: gpod, pymad')
            message = _('To use the iPod synchronization feature, you need to install the <b>python-gpod</b> and <b>python-pymad</b> libraries from your distribution vendor. More information about the needed libraries can be found on the gPodder website.')
            self.show_message( message, title)
            return
        
        if gl.device_type in [ 'ipod', 'filesystem' ]:
            sync_class = None

            if gl.device_type == 'filesystem':
                title = _('Delete podcasts from MP3 player?')
                message = _('Do you really want to completely remove all episodes from your MP3 player?')
                if self.show_confirmation( message, title):
                    sync_class = gPodder_FSSync
            elif gl.device_type == 'ipod':
                title = _('Delete podcasts on iPod?')
                message = _('Do you really want to completely remove all episodes in the <b>Podcasts</b> playlist on your iPod?')
                if self.show_confirmation( message, title):
                    sync_class = gPodder_iPodSync

            if not sync_class:
                return

            sync_win = gPodderSync()
            sync = sync_class( callback_status = sync_win.set_status, callback_progress = sync_win.set_progress, callback_done = sync_win.close)
            sync_win.set_sync_object( sync)
            thread = Thread( target = self.ipod_cleanup_proc, args = ( sync, ))
            thread.start()

    def on_itemPreferences_activate(self, widget, *args):
        prop = gPodderProperties()
        prop.set_uar( self.user_apps_reader)
        prop.set_callback_finished( self.updateComboBox)

    def on_itemAddChannel_activate(self, widget, *args):
        if self.channelPaned.get_position() < 200:
            self.channelPaned.set_position( 200)
        self.entryAddChannel.set_text( _('Enter podcast URL'))
        self.entryAddChannel.grab_focus()

    def on_itemEditChannel_activate(self, widget, *args):
        if self.active_channel == None:
            title = _('No channel selected')
            message = _('Please select a channel in the channels list to edit.')
            self.show_message( message, title)
            return

        gPodderChannel( channel = self.active_channel, callback_closed = self.updateComboBox)

    def on_itemRemoveChannel_activate(self, widget, *args):
        try:
            title = _('Remove channel and episodes?')
            message = _('Do you really want to remove <b>%s</b> and all downloaded episodes?') % ( self.active_channel.title, )
            if self.show_confirmation( message, title):
                self.active_channel.remove_downloaded()
                # only delete partial files if we do not have any downloads in progress
                delete_partial = not services.download_status_manager.has_items()
                gPodderLib().clean_up_downloads( delete_partial)
                self.channels.remove( self.active_channel)
                save_channels( self.channels)
                self.update_feed_cache( force_update = False)
        except:
            pass

    def on_itemExportChannels_activate(self, widget, *args):
        if not self.channels:
            title = _('Nothing to export')
            message = _('Your list of channel subscriptions is empty. Please subscribe to some podcasts first before trying to export your subscription list.')
            self.show_message( message, title)
            return

        dlg = gtk.FileChooserDialog( title=_("Export to OPML"), parent = None, action = gtk.FILE_CHOOSER_ACTION_SAVE)
        dlg.add_button( gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dlg.add_button( gtk.STOCK_SAVE, gtk.RESPONSE_OK)
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            filename = dlg.get_filename()
            exporter = opml.Exporter( filename)
            if not exporter.write( self.channels):
                self.show_message( _('Could not export OPML to file. Please check your permissions.'), _('OPML export failed'))

        dlg.destroy()

    def on_itemImportChannels_activate(self, widget, *args):
        gPodderOpmlLister().get_channels_from_url( gPodderLib().opml_url, lambda url: self.add_new_channel(url,False), lambda: self.on_itemDownloadAllNew_activate( self.gPodder))

    def on_btnTransfer_clicked(self, widget, *args):
        self.on_treeAvailable_row_activated( widget, args)

    def on_homepage_activate(self, widget, *args):
        Thread( target = webbrowser.open, args = ( app_website, )).start()

    def on_wishlist_activate(self, widget, *args):
        Thread( target = webbrowser.open, args = ( 'http://www.amazon.de/gp/registry/2PD2MYGHE6857', )).start()

    def on_mailinglist_activate(self, widget, *args):
        Thread( target = webbrowser.open, args = ( 'http://lists.berlios.de/mailman/listinfo/gpodder-devel', )).start()

    def on_itemAbout_activate(self, widget, *args):
        dlg = gtk.AboutDialog()
        dlg.set_name( app_name)
        dlg.set_version( app_version)
        dlg.set_authors( app_authors)
        dlg.set_copyright( app_copyright)
        dlg.set_website( app_website)
        dlg.set_translator_credits( _('translator-credits'))
        dlg.connect( 'response', lambda dlg, response: dlg.destroy())

        try:
            dlg.set_logo( gtk.gdk.pixbuf_new_from_file_at_size( scalable_dir, 200, 200))
        except:
            pass
        
        dlg.run()

    def on_wNotebook_switch_page(self, widget, *args):
        page_num = args[1]
        if page_num == 0:
            self.play_or_download()
        else:
            self.toolDownload.set_sensitive( False)
            self.toolPlay.set_sensitive( False)
            self.toolTransfer.set_sensitive( False)
            self.toolCancel.set_sensitive( services.download_status_manager.has_items())

    def on_treeChannels_row_activated(self, widget, *args):
        self.on_itemEditChannel_activate( self.treeChannels)

    def on_treeChannels_cursor_changed(self, widget, *args):
        ( model, iter ) = self.treeChannels.get_selection().get_selected()

        if model != None and iter != None:
            id = model.get_path( iter)[0]
            self.active_channel = self.channels[id]

            self.itemEditChannel.get_child().set_text( _('Edit "%s"') % ( self.active_channel.title,))
            self.itemRemoveChannel.get_child().set_text( _('Remove "%s"') % ( self.active_channel.title,))
            self.itemEditChannel.show_all()
            self.itemRemoveChannel.show_all()
        else:
            self.active_channel = None
            self.itemEditChannel.hide_all()
            self.itemRemoveChannel.hide_all()

        self.updateTreeView()

    def on_entryAddChannel_changed(self, widget, *args):
        active = self.entryAddChannel.get_text() not in ('', _('Enter podcast URL'))
        self.btnAddChannel.set_sensitive( active)

    def on_btnAddChannel_clicked(self, widget, *args):
        url = self.entryAddChannel.get_text()
        self.entryAddChannel.set_text('')
        self.add_new_channel( url)

    def on_btnEditChannel_clicked(self, widget, *args):
        self.on_itemEditChannel_activate( widget, args)

    def on_treeAvailable_row_activated(self, widget, *args):
        try:
            selection = self.treeAvailable.get_selection()
            selection_tuple = selection.get_selected_rows()
            transfer_files = False
            episodes = []

            if selection.count_selected_rows() > 1:
                widget_to_send = None
                show_message_dialog = False
            else:
                widget_to_send = widget
                show_message_dialog = True

            if widget.get_name() == 'itemTransferSelected' or widget.get_name() == 'toolTransfer':
                transfer_files = True

            for apath in selection_tuple[1]:
                selection_iter = self.treeAvailable.get_model().get_iter( apath)
                url = self.treeAvailable.get_model().get_value( selection_iter, 0)

                if transfer_files:
                    episodes.append( self.active_channel.find_episode( url))
                else:
                    self.download_podcast_by_url( url, show_message_dialog, widget_to_send)

            if transfer_files and len(episodes):
                self.on_sync_to_ipod_activate( None, episodes)
        except:
            title = _('Nothing selected')
            message = _('Please select an episode that you want to download and then click on the download button to start downloading the selected episode.')
            self.show_message( message, title)

    def on_btnDownload_clicked(self, widget, *args):
        self.on_treeAvailable_row_activated( widget, args)

    def on_treeAvailable_button_release_event(self, widget, *args):
        self.play_or_download()

    def on_btnDownloadNewer_clicked(self, widget, *args):
        channel = self.active_channel
        episodes_to_download = channel.get_new_episodes()

        if not episodes_to_download:
            title = _('No episodes to download')
            message = _('You have already downloaded the most recent episodes from <b>%s</b>.') % ( channel.title, )
            self.show_message( message, title)
        else:
            if len(episodes_to_download) > 1:
                if len(episodes_to_download) < 10:
                    e_str = '\n'.join( [ '  <b>'+saxutils.escape(e.title)+'</b>' for e in episodes_to_download ] )
                else:
                    e_str = '\n'.join( [ '  <b>'+saxutils.escape(e.title)+'</b>' for e in episodes_to_download[:7] ] )
                    e_str_2 = _('(...%d more episodes...)') % ( len(episodes_to_download)-7, )
                    e_str = '%s\n  <i>%s</i>' % ( e_str, e_str_2, )
                title = _('Download new episodes?')
                message = _('New episodes are available for download. If you want, you can download these episodes to your computer now.')
                message = '%s\n\n%s' % ( message, e_str, )
            else:
                title = _('Download %s?') % saxutils.escape(episodes_to_download[0].title)
                message = _('A new episode is available for download. If you want, you can download this episode to your computer now.')

            if not self.show_confirmation( message, title):
                return

        for episode in episodes_to_download:
            self.download_podcast_by_url( episode.url, False)

    def on_btnSelectAllAvailable_clicked(self, widget, *args):
        self.treeAvailable.get_selection().select_all()
        self.on_treeAvailable_row_activated( self.toolDownload, args)
        self.treeAvailable.get_selection().unselect_all()

    def on_treeDownloads_row_activated(self, widget, *args):
        cancel_urls = []

        if self.wNotebook.get_current_page() > 0:
            # Use the download list treeview + model
            ( tree, column ) = ( self.treeDownloads, 3 )
        else:
            # Use the available podcasts treeview + model
            ( tree, column ) = ( self.treeAvailable, 0 )

        selection = tree.get_selection()
        (model, paths) = selection.get_selected_rows()
        for path in paths:
            url = model.get_value( model.get_iter( path), column)
            cancel_urls.append( url)

        if len( cancel_urls) == 0:
            log('Nothing selected.', sender = self)
            return

        if len( cancel_urls) == 1:
            title = _('Cancel download?')
            message = _("Cancelling this download will remove the partially downloaded file and stop the download.")
        else:
            title = _('Cancel downloads?')
            message = _("Cancelling the download will stop the %d selected downloads and remove partially downloaded files.") % selection.count_selected_rows()

        if self.show_confirmation( message, title):
            for url in cancel_urls:
                services.download_status_manager.cancel_by_url( url)

    def on_btnCancelDownloadStatus_clicked(self, widget, *args):
        self.on_treeDownloads_row_activated( widget, None)

    def on_btnCancelAll_clicked(self, widget, *args):
        self.treeDownloads.get_selection().select_all()
        self.on_treeDownloads_row_activated( self.toolCancel, None)
        self.treeDownloads.get_selection().unselect_all()

    def on_btnDownloadedExecute_clicked(self, widget, *args):
        self.on_treeAvailable_row_activated( widget, args)

    def on_btnDownloadedDelete_clicked(self, widget, *args):
        if self.active_channel == None:
            return

        channel_url = self.active_channel.url
        selection = self.treeAvailable.get_selection()
        ( model, paths ) = selection.get_selected_rows()
        
        if selection.count_selected_rows() == 0:
            log( 'Nothing selected - will not remove any downloaded episode.')
            return

        if selection.count_selected_rows() == 1:
            title = _('Remove %s?')  % model.get_value( model.get_iter( paths[0]), 1)
            message = _("If you remove this episode, it will be deleted from your computer. If you want to listen to this episode again, you will have to re-download it.")
        else:
            title = _('Remove %d episodes?') % selection.count_selected_rows()
            message = _('If you remove these episodes, they will be deleted from your computer. If you want to listen to any of these episodes again, you will have to re-download the episodes in question.')
        
        # if user confirms deletion, let's remove some stuff ;)
        if self.show_confirmation( message, title):
            try:
                # iterate over the selection, see also on_treeDownloads_row_activated
                for path in paths:
                    url = model.get_value( model.get_iter( path), 0)
                    self.active_channel.delete_episode_by_url( url)
                    gPodderLib().history_mark_downloaded( url)
      
                # now, clear local db cache so we can re-read it
                self.updateComboBox()
            except:
                log( 'Error while deleting (some) downloads.')

        # only delete partial files if we do not have any downloads in progress
        delete_partial = not services.download_status_manager.has_items()
        gPodderLib().clean_up_downloads( delete_partial)
        self.active_channel.force_update_tree_model()
        self.updateTreeView()

    def on_btnDeleteAll_clicked(self, widget, *args):
        self.treeAvailable.get_selection().select_all()
        self.on_btnDownloadedDelete_clicked( widget, args)
        self.treeAvailable.get_selection().unselect_all()


class gPodderChannel(GladeWidget):
    def new(self):
        self.gPodderChannel.set_title( self.channel.title)
        self.entryTitle.set_text( self.channel.title)
        self.entryURL.set_text( self.channel.url)

        self.LabelDownloadTo.set_text( self.channel.save_dir)
        self.LabelWebsite.set_text( self.channel.link)

        self.channel.load_settings()
        self.cbNoSync.set_active( not self.channel.sync_to_devices)
        self.musicPlaylist.set_text( self.channel.device_playlist_name)
        self.cbMusicChannel.set_active( self.channel.is_music_channel)
        if self.channel.username:
            self.FeedUsername.set_text( self.channel.username)
        if self.channel.password:
            self.FeedPassword.set_text( self.channel.password)

        self.on_btnClearCover_clicked( self.btnClearCover, delete_file = False)
        self.on_btnDownloadCover_clicked( self.btnDownloadCover, url = False)
        
        b = gtk.TextBuffer()
        b.set_text( self.channel.description)
        self.channel_description.set_buffer( b)

        #Add Drag and Drop Support
        flags = gtk.DEST_DEFAULT_ALL
        targets = [ ('text/uri-list', 0, 2), ('text/plain', 0, 4) ]
        actions = gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_COPY
        self.vboxCoverEditor.drag_dest_set( flags, targets, actions)
        self.vboxCoverEditor.connect( 'drag_data_received', self.drag_data_received)

    def on_btnClearCover_clicked( self, widget, delete_file = True):
        self.imgCover.clear()
        if delete_file:
            util.delete_file( self.channel.cover_file)
        self.btnClearCover.set_sensitive( os.path.exists( self.channel.cover_file))
        self.btnDownloadCover.set_sensitive( not os.path.exists( self.channel.cover_file) and bool(self.channel.image))
        self.labelCoverStatus.set_text( _('You can drag a cover file here.'))
        self.labelCoverStatus.show()

    def on_btnDownloadCover_clicked( self, widget, url = None):
        if url == None:
            url = self.channel.image

        if url != False:
            self.btnDownloadCover.set_sensitive( False)

        self.labelCoverStatus.show()
        gPodderLib().get_image_from_url( url, self.imgCover.set_from_pixbuf, self.labelCoverStatus.set_text, self.cover_download_finished, self.channel.cover_file)

    def cover_download_finished( self):
        self.labelCoverStatus.hide()
        self.btnClearCover.set_sensitive( os.path.exists( self.channel.cover_file))
        self.btnDownloadCover.set_sensitive( not os.path.exists( self.channel.cover_file) and bool(self.channel.image))

    def drag_data_received( self, widget, content, x, y, sel, ttype, time):
        files = sel.data.strip().split('\n')
        if len(files) != 1:
            self.show_message( _('You can only drop a single image or URL here.'), _('Drag and drop'))
            return

        file = files[0]

        if file.startswith( 'file://') or file.startswith( 'http://'):
            self.on_btnClearCover_clicked( self.btnClearCover)
            if file.startswith( 'file://'):
                filename = file[len('file://'):]
                shutil.copyfile( filename, self.channel.cover_file)
            self.on_btnDownloadCover_clicked( self.btnDownloadCover, url = file)
            return
        
        self.show_message( _('You can only drop local files and http:// URLs here.'), _('Drag and drop'))

    def on_gPodderChannel_destroy(self, widget, *args):
        self.callback_closed()

    def on_cbMusicChannel_toggled(self, widget, *args):
        self.musicPlaylist.set_sensitive( self.cbMusicChannel.get_active())

    def on_btnOK_clicked(self, widget, *args):
        self.channel.sync_to_devices = not self.cbNoSync.get_active()
        self.channel.is_music_channel = self.cbMusicChannel.get_active()
        self.channel.device_playlist_name = self.musicPlaylist.get_text()
        self.channel.set_custom_title( self.entryTitle.get_text())
        self.channel.username = self.FeedUsername.get_text().strip()
        self.channel.password = self.FeedPassword.get_text()
        self.channel.save_settings()

        self.gPodderChannel.destroy()


class gPodderProperties(GladeWidget):
    def new(self):
        self.callback_finished = None
        gl = gPodderLib()
        self.httpProxy.set_text( gl.http_proxy)
        self.ftpProxy.set_text( gl.ftp_proxy)
        self.openApp.set_text( gl.open_app)
        self.iPodMountpoint.set_label( gl.ipod_mount)
        self.ipodIcon.set_from_icon_name( 'gnome-dev-ipod', gtk.ICON_SIZE_BUTTON)
        self.filesystemMountpoint.set_label( gl.mp3_player_folder)
        self.opmlURL.set_text( gl.opml_url)
        if gl.downloaddir:
            self.chooserDownloadTo.set_filename( gl.downloaddir)
        if gl.torrentdir:
            self.chooserBitTorrentTo.set_filename( gl.torrentdir)
        self.radio_copy_torrents.set_active( not gl.use_gnome_bittorrent)
        self.radio_gnome_bittorrent.set_active( gl.use_gnome_bittorrent)
        self.updateonstartup.set_active(gl.update_on_startup)
        self.downloadnew.set_active(gl.download_after_update)
        self.cbLimitDownloads.set_active(gl.limit_rate)
        self.spinLimitDownloads.set_value(gl.limit_rate_value)
        self.cbMaxDownloads.set_active(gl.max_downloads_enabled)
        self.cbCustomSyncName.set_active(gl.custom_sync_name_enabled)
        self.entryCustomSyncName.set_text(gl.custom_sync_name)
        self.entryCustomSyncName.set_sensitive( self.cbCustomSyncName.get_active())
        self.spinMaxDownloads.set_value(gl.max_downloads)
        self.only_sync_not_played.set_active(gl.only_sync_not_played)
        if tagging_supported():
            self.updatetags.set_active(gl.update_tags)
        else:
            self.updatetags.set_sensitive( False)
            new_label = '%s (%s)' % ( self.updatetags.get_label(), _('needs python-eyed3') )
            self.updatetags.set_label( new_label)
        # device type
        self.comboboxDeviceType.set_active( 0)
        if gl.device_type == 'ipod':
            self.comboboxDeviceType.set_active( 1)
        elif gl.device_type == 'filesystem':
            self.comboboxDeviceType.set_active( 2)
        # the use proxy env vars check box
        self.cbEnvironmentVariables.set_active( gl.proxy_use_environment)
        # setup cell renderers
        cellrenderer = gtk.CellRendererPixbuf()
        self.comboPlayerApp.pack_start( cellrenderer, False)
        self.comboPlayerApp.add_attribute( cellrenderer, 'pixbuf', 2)
        cellrenderer = gtk.CellRendererText()
        self.comboPlayerApp.pack_start( cellrenderer, True)
        self.comboPlayerApp.add_attribute( cellrenderer, 'markup', 0)

    def update_mountpoint( self, ipod):
        if ipod == None or ipod.mount_point == None:
            self.iPodMountpoint.set_label( '')
        else:
            self.iPodMountpoint.set_label( ipod.mount_point)
    
    def set_uar( self, uar):
        self.comboPlayerApp.set_model( uar.get_applications_as_model())
        # try to activate an item
        index = self.find_active()
        self.comboPlayerApp.set_active( index)
    
    def set_callback_finished( self, cb):
        self.callback_finished = cb
    
    def find_active( self):
        model = self.comboPlayerApp.get_model()
        iter = model.get_iter_first()
        index = 0
        while iter != None:
            command = model.get_value( iter, 1)
            if command == self.openApp.get_text():
                return index
            iter = model.iter_next( iter)
            index = index + 1
        # return last item = custom command
        return index-1
    
    def set_download_dir( self, new_download_dir, event = None):
        gl = gPodderLib()
        gl.downloaddir = self.chooserDownloadTo.get_filename()
        if gl.downloaddir != self.chooserDownloadTo.get_filename():
            gobject.idle_add( self.show_message, _('There has been an error moving your downloads to the specified location. The old download directory will be used instead.'), _('Error moving downloads'))

        if event:
            event.set()

    def on_cbCustomSyncName_toggled( self, widget, *args):
        self.entryCustomSyncName.set_sensitive( widget.get_active())

    def on_btnCustomSyncNameHelp_clicked( self, widget):
        examples = [
                '<i>{episode.title}</i> -&gt; <b>Interview with RMS</b>',
                '<i>{episode.basename}</i> -&gt; <b>70908-interview-rms</b>',
                '<i>{episode.published}</i> -&gt; <b>20070908</b>'
        ]

        info = [
                _('You can specify a custom format string for the file names on your MP3 player here.'),
                _('The format string will be used to generate a file name on your device. The file extension (e.g. ".mp3") will be added automatically.'),
                '\n'.join( [ '   %s' % s for s in examples ])
        ]

        self.show_message( '\n\n'.join( info), _('Custom format strings'))

    def on_gPodderProperties_destroy(self, widget, *args):
        self.on_btnOK_clicked( widget, *args)

    def on_comboPlayerApp_changed(self, widget, *args):
        # find out which one
        iter = self.comboPlayerApp.get_active_iter()
        model = self.comboPlayerApp.get_model()
        command = model.get_value( iter, 1)
        if command == '':
            self.openApp.set_sensitive( True)
            self.openApp.show()
            self.labelCustomCommand.show()
        else:
            self.openApp.set_text( command)
            self.openApp.set_sensitive( False)
            self.openApp.hide()
            self.labelCustomCommand.hide()

    def on_cbMaxDownloads_toggled(self, widget, *args):
        self.spinMaxDownloads.set_sensitive( self.cbMaxDownloads.get_active())

    def on_cbLimitDownloads_toggled(self, widget, *args):
        self.spinLimitDownloads.set_sensitive( self.cbLimitDownloads.get_active())

    def on_cbEnvironmentVariables_toggled(self, widget, *args):
         sens = not self.cbEnvironmentVariables.get_active()
         self.httpProxy.set_sensitive( sens)
         self.ftpProxy.set_sensitive( sens)

    def on_comboboxDeviceType_changed(self, widget, *args):
        active_item = self.comboboxDeviceType.get_active()

        # iPod
        if active_item == 1:
            self.ipodLabel.show()
            self.btn_iPodMountpoint.set_sensitive( True)
            self.btn_iPodMountpoint.show_all()
        else:
            self.ipodLabel.hide()
            self.btn_iPodMountpoint.set_sensitive( False)
            self.btn_iPodMountpoint.hide()

        # filesystem-based MP3 player
        if active_item == 2:
            self.filesystemLabel.show()
            self.btn_filesystemMountpoint.set_sensitive( True)
            self.btn_filesystemMountpoint.show_all()
        else:
            self.filesystemLabel.hide()
            self.btn_filesystemMountpoint.set_sensitive( False)
            self.btn_filesystemMountpoint.hide()

    def on_btn_iPodMountpoint_clicked(self, widget, *args):
        fs = gtk.FileChooserDialog( title = _('Select iPod mountpoint'), action = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
        fs.add_button( gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        fs.add_button( gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        gl = gPodderLib()
        fs.set_filename( self.iPodMountpoint.get_label())
        if fs.run() == gtk.RESPONSE_OK:
            self.iPodMountpoint.set_label( fs.get_filename())
        fs.destroy()

    def on_btn_FilesystemMountpoint_clicked(self, widget, *args):
        fs = gtk.FileChooserDialog( title = _('Select folder for MP3 player'), action = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
        fs.add_button( gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        fs.add_button( gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        gl = gPodderLib()
        fs.set_filename( self.filesystemMountpoint.get_label())
        if fs.run() == gtk.RESPONSE_OK:
            self.filesystemMountpoint.set_label( fs.get_filename())
        fs.destroy()

    def on_btnOK_clicked(self, widget, *args):
        gl = gPodderLib()
        gl.http_proxy = self.httpProxy.get_text()
        gl.ftp_proxy = self.ftpProxy.get_text()
        gl.open_app = self.openApp.get_text()
        gl.proxy_use_environment = self.cbEnvironmentVariables.get_active()
        gl.ipod_mount = self.iPodMountpoint.get_label()
        gl.mp3_player_folder = self.filesystemMountpoint.get_label()
        gl.opml_url = self.opmlURL.get_text()

        if gl.downloaddir != self.chooserDownloadTo.get_filename():
            new_download_dir = self.chooserDownloadTo.get_filename()
            download_dir_size = util.calculate_size( gl.downloaddir)
            download_dir_size_string = util.format_filesize( download_dir_size, 'MB')
            event = Event()

            dlg = gtk.Dialog( _('Moving downloads folder'), self.gPodderProperties)
            dlg.vbox.set_spacing( 5)
            dlg.set_border_width( 5)
         
            label = gtk.Label()
            label.set_line_wrap( True)
            label.set_markup( _('Moving downloads from <b>%s</b> to <b>%s</b>...') % ( gl.downloaddir, new_download_dir, ))
            myprogressbar = gtk.ProgressBar()
         
            # put it all together
            dlg.vbox.pack_start( label)
            dlg.vbox.pack_end( myprogressbar)

            # switch windows
            dlg.show_all()
            self.gPodderProperties.hide_all()
         
            # hide action area and separator line
            dlg.action_area.hide()
            dlg.set_has_separator( False)

            args = ( new_download_dir, event, )

            thread = Thread( target = self.set_download_dir, args = args)
            thread.start()

            while not event.isSet():
                new_download_dir_size = util.calculate_size( new_download_dir)
                fract = (1.00*new_download_dir_size) / (1.00*download_dir_size)
                if fract < 0.99:
                    myprogressbar.set_text( _('%s of %s') % ( util.format_filesize( new_download_dir_size, 'MB'), download_dir_size_string, ))
                else:
                    myprogressbar.set_text( _('Finishing... please wait.'))
                myprogressbar.set_fraction( fract)
                event.wait( 0.1)
                while gtk.events_pending():
                    gtk.main_iteration( False)

            dlg.destroy()

        gl.torrentdir = self.chooserBitTorrentTo.get_filename()
        gl.use_gnome_bittorrent = self.radio_gnome_bittorrent.get_active()
        gl.update_on_startup = self.updateonstartup.get_active()
        gl.download_after_update = self.downloadnew.get_active()
        gl.limit_rate = self.cbLimitDownloads.get_active()
        gl.limit_rate_value = self.spinLimitDownloads.get_value()
        gl.max_downloads_enabled = self.cbMaxDownloads.get_active()
        gl.max_downloads = int(self.spinMaxDownloads.get_value())
        gl.custom_sync_name = self.entryCustomSyncName.get_text()
        gl.custom_sync_name_enabled = self.cbCustomSyncName.get_active()
        gl.update_tags = self.updatetags.get_active()
        gl.only_sync_not_played = self.only_sync_not_played.get_active()
        device_type = self.comboboxDeviceType.get_active()
        if device_type == 0:
            gl.device_type = 'none'
        elif device_type == 1:
            gl.device_type = 'ipod'
        elif device_type == 2:
            gl.device_type = 'filesystem'
        gl.propertiesChanged()
        self.gPodderProperties.destroy()
        if self.callback_finished:
            self.callback_finished()


class gPodderEpisode(GladeWidget):
    def new(self):
        services.download_status_manager.register( 'list-changed', self.on_download_status_changed)
        services.download_status_manager.register( 'progress-detail', self.on_download_status_progress)

        self.episode_title.set_markup( '<span weight="bold" size="larger">%s</span>' % saxutils.escape( self.episode.title))

        b = gtk.TextBuffer()
        b.set_text( strip( self.episode.description))
        self.episode_description.set_buffer( b)

        self.gPodderEpisode.set_title( self.episode.title)
        self.LabelDownloadLink.set_text( self.episode.url)
        self.LabelWebsiteLink.set_text( self.episode.link)
        self.labelPubDate.set_markup( self.episode.pubDate)

        self.channel_title.set_markup( _('<i>from %s</i>') % self.channel.title)

        self.hide_show_widgets()
        services.download_status_manager.request_progress_detail( self.episode.url)

        if hasattr( self, 'center_on_widget'):
            ( x, y ) = self.gpodder_main_window.get_position()
            a = self.center_on_widget.allocation
            ( x, y ) = ( x + a.x, y + a.y )
            ( w, h ) = ( a.width, a.height )
            ( pw, ph ) = self.gPodderEpisode.get_size()
            self.gPodderEpisode.move( x + w/2 - pw/2, y + h/2 - ph/2)

    def on_btnCancel_clicked( self, widget):
        services.download_status_manager.cancel_by_url( self.episode.url)

    def on_gPodderEpisode_destroy( self, widget):
        services.download_status_manager.unregister( 'list-changed', self.on_download_status_changed)
        services.download_status_manager.unregister( 'progress-detail', self.on_download_status_progress)

    def on_download_status_changed( self):
        self.hide_show_widgets()

    def on_download_status_progress( self, url, progress, speed):
        if url == self.episode.url:
            self.progress_bar.set_fraction( 1.0*progress/100.0)
            self.progress_bar.set_text( 'Downloading: %d%% (%s)' % ( progress, speed, ))

    def hide_show_widgets( self):
        is_downloading = services.download_status_manager.is_download_in_progress( self.episode.url)
        if is_downloading:
            self.progress_bar.show_all()
            self.btnCancel.show_all()
            self.btnPlay.hide_all()
            self.btnSaveFile.hide_all()
            self.btnDownload.hide_all()
        else:
            self.progress_bar.hide_all()
            self.btnCancel.hide_all()
            if os.path.exists( self.episode.local_filename()):
                self.btnPlay.show_all()
                self.btnSaveFile.show_all()
                self.btnDownload.hide_all()
            else:
                self.btnPlay.hide_all()
                self.btnSaveFile.hide_all()
                self.btnDownload.show_all()

    def on_btnCloseWindow_clicked(self, widget, *args):
        self.gPodderEpisode.destroy()

    def on_btnDownload_clicked(self, widget, *args):
        if self.download_callback:
            self.download_callback()

    def on_btnPlay_clicked(self, widget, *args):
        if self.play_callback:
            self.play_callback()

        self.gPodderEpisode.destroy()

    def on_btnSaveFile_clicked(self, widget, *args):
        fn = self.episode.local_filename()
        ext = os.path.splitext(fn)[1]
        suggestion = self.channel.title + ' - ' + self.episode.title + ext

        dlg = gtk.FileChooserDialog( title=_("Save episode as file"), parent = self.gPodderEpisode, action = gtk.FILE_CHOOSER_ACTION_SAVE)
        dlg.set_current_name( suggestion)
        dlg.set_current_folder( os.path.expanduser('~'))
        dlg.add_button( gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dlg.add_button( gtk.STOCK_SAVE, gtk.RESPONSE_OK)
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            foutname = dlg.get_filename()
            if foutname[-len(ext):] != ext:
                foutname = foutname + ext
            log( 'Saving episode as: %s', foutname, sender = self)
            try:
                shutil.copyfile( fn, foutname)
            except:
                log('Error saving file :/', sender = self)

        dlg.destroy()


class gPodderSync(GladeWidget):
    def new(self):
        self.pos_overall = 0
        self.max_overall = 1
        self.pos_episode = 0
        self.max_episode = 1
        self.cancel_button.set_sensitive( False)
        self.sync = None
        self.default_title = self.gPodderSync.get_title()
        self.default_header = self.label_header.get_text()
        self.default_body = self.label_text.get_text()

        self.imageSync.set_from_icon_name( 'gnome-dev-ipod', gtk.ICON_SIZE_DIALOG)

    def set_sync_object( self, sync):
        self.sync = sync
        if self.sync.can_cancel:
            self.cancel_button.set_sensitive( True)

    def set_progress( self, pos, max, is_overall = False, is_sub_episode = False):
        pos = min(pos, max)
        if is_sub_episode:
            fraction_episode = 1.0*(self.pos_episode+1.0*pos/max)/self.max_episode
            self.pbEpisode.set_fraction( fraction_episode)
            self.pbSync.set_fraction( 1.0*(self.pos_overall+fraction_episode)/self.max_overall)
            return

        if is_overall:
            progressbar = self.pbSync
            self.pos_overall = pos
            self.max_overall = max
            progressbar.set_fraction( 1.0*pos/max)
        else:
            progressbar = self.pbEpisode
            self.pos_episode = pos
            self.max_episode = max
            progressbar.set_fraction( 1.0*pos/max)
            self.pbSync.set_fraction( 1.0*(self.pos_overall+1.0*pos/max)/self.max_overall)

        percent = _('%d of %d done') % ( pos, max )
        progressbar.set_text( percent)

    def set_status( self, episode = None, channel = None, progressbar = None, title = None, header = None, body = None):
        if episode != None:
            self.labelEpisode.set_markup( '<i>%s</i>' % episode)

        if channel != None:
            self.labelChannel.set_markup( '<i>%s</i>' % channel)

        if progressbar != None:
            self.pbSync.set_text( progressbar)

        if title != None:
            self.gPodderSync.set_title( title)
        else:
            self.gPodderSync.set_title( self.default_title)

        if header != None:
            self.label_header.set_markup( '<b><big>%s</big></b>' % header)
        else:
            self.label_header.set_markup( '<b><big>%s</big></b>' % self.default_header)

        if body != None:
            self.label_text.set_markup( body)
        else:
            self.label_text.set_markup( self.default_body)


    def close( self, success = True, access_error = False, cleaned = False, error_messages = []):
        if self.sync:
            self.sync.cancelled = True
        self.cancel_button.set_label( gtk.STOCK_CLOSE)
        self.cancel_button.set_use_stock( True)
        self.cancel_button.set_sensitive( True)
        self.gPodderSync.set_resizable( True)
        self.pbSync.hide_all()
        self.pbEpisode.hide_all()
        self.labelChannel.hide_all()
        self.labelEpisode.hide_all()
        self.gPodderSync.set_resizable( False)
        if success and not cleaned:
            title = _('Synchronization finished')
            header = _('Copied Podcasts')
            body = _('The selected episodes have been copied to your device. You can now unplug the device.')
        elif access_error:
            title = _('Synchronization error')
            header = _('Cannot access device')
            body = _('Make sure your device is connected to your computer and mounted. Please also make sure you have set the correct path to your device in the preferences dialog.')
        elif cleaned:
            title = _('Device cleaned')
            header = _('Podcasts removed')
            body = _('Synchronized Podcasts have been removed from your device.')
        elif len(error_messages):
            title = _('Synchronization error')
            header = _('An error has occurred')
            body = '\n'.join( error_messages)
        else:
            title = _('Synchronization aborted')
            header = _('Aborted')
            body = _('The synchronization progress has been interrupted by the user. Please retry synchronization at a later time.')
        self.gPodderSync.set_title( title)
        self.label_header.set_markup( '<big><b>%s</b></big>' % header)
        self.label_text.set_text( body)

    def on_gPodderSync_destroy(self, widget, *args):
        pass

    def on_cancel_button_clicked(self, widget, *args):
        if self.sync:
            if self.sync.cancelled:
                self.gPodderSync.destroy()
            else:
                self.sync.cancelled = True
                self.cancel_button.set_sensitive( False)
        else:
            self.gPodderSync.destroy()


class gPodderOpmlLister(GladeWidget):
    def new(self):
        # initiate channels list
        self.channels = []
        self.callback_for_channel = None
        self.callback_finished = None

        togglecell = gtk.CellRendererToggle()
        togglecell.set_property( 'activatable', True)
        togglecell.connect( 'toggled', self.callback_edited)
        togglecolumn = gtk.TreeViewColumn( '', togglecell, active=0)
        
        titlecell = gtk.CellRendererText()
        titlecolumn = gtk.TreeViewColumn( _('Channel'), titlecell, markup=1)

        for itemcolumn in ( togglecolumn, titlecolumn ):
            self.treeviewChannelChooser.append_column( itemcolumn)

    def callback_edited( self, cell, path):
        model = self.treeviewChannelChooser.get_model()

        url = model[path][2]

        model[path][0] = not model[path][0]
        if model[path][0]:
            self.channels.append( url)
        else:
            self.channels.remove( url)

        self.btnOK.set_sensitive( bool(len(self.channels)))

    def thread_func( self):
        url = self.entryURL.get_text()
        importer = opml.Importer( url)
        model = importer.get_model()
        gobject.idle_add( self.treeviewChannelChooser.set_model, model)
        gobject.idle_add( self.labelStatus.set_label, '')
        gobject.idle_add( self.btnDownloadOpml.set_sensitive, True)
        gobject.idle_add( self.entryURL.set_sensitive, True)
        gobject.idle_add( self.treeviewChannelChooser.set_sensitive, True)
        self.channels = []
    
    def get_channels_from_url( self, url, callback_for_channel = None, callback_finished = None):
        if callback_for_channel:
            self.callback_for_channel = callback_for_channel
        if callback_finished:
            self.callback_finished = callback_finished
        self.labelStatus.set_label( _('Downloading, please wait...'))
        self.entryURL.set_text( url)
        self.btnDownloadOpml.set_sensitive( False)
        self.entryURL.set_sensitive( False)
        self.btnOK.set_sensitive( False)
        self.treeviewChannelChooser.set_sensitive( False)
        Thread( target = self.thread_func).start()

    def on_gPodderOpmlLister_destroy(self, widget, *args):
        pass

    def on_btnDownloadOpml_clicked(self, widget, *args):
        self.get_channels_from_url( self.entryURL.get_text())

    def on_btnOK_clicked(self, widget, *args):
        self.gPodderOpmlLister.destroy()

        # add channels that have been selected
        for url in self.channels:
            if self.callback_for_channel:
                self.callback_for_channel( url)

        if self.callback_finished:
            self.callback_finished()

    def on_btnCancel_clicked(self, widget, *args):
        self.gPodderOpmlLister.destroy()


def main():
    gobject.threads_init()
    gtk.window_set_default_icon_name( 'gpodder')

    gPodder().run()

