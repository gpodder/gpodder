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

import gtk
import hildon
import pango
from xml.sax import saxutils

import gpodder
_ = gpodder.gettext
N_ = gpodder.ngettext

from gpodder import util
from gpodder.liblogger import log

from gpodder.gtkui.interface.common import BuilderWidget
from gpodder.gtkui.interface.common import Orientation

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
    finger_friendly_widgets = ['btnRemoveAction', 'btnOK']
    
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

        if hasattr(self, 'instructions'):
            #self.show_message(self.instructions)
            pass

        if self.remove_callback is not None:
            self.btnRemoveAction.show()
            self.btnRemoveAction.set_label(self.remove_action)

        if hasattr(self, 'stock_ok_button'):
            if self.stock_ok_button == 'gpodder-download':
                self.btnOK.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_DOWN, gtk.ICON_SIZE_BUTTON))
                self.btnOK.set_label(_('Download'))
            else:
                self.btnOK.set_label(self.stock_ok_button)
                self.btnOK.set_use_stock(True)

        # Work around Maemo bug #4718
        self.btnOK.set_name('HildonButton-finger')
        self.btnRemoveAction.set_name('HildonButton-finger')

        # Make sure the window comes up quick
        self.main_window.show()
        self.main_window.present()
        while gtk.events_pending():
            gtk.main_iteration(False)

        next_column = self.COLUMN_ADDITIONAL
        for name, sort_name, sort_type, caption in self.columns:
            renderer = gtk.CellRendererText()
            if next_column < self.COLUMN_ADDITIONAL + 2:
                renderer.set_property('ellipsize', pango.ELLIPSIZE_END)
            column = gtk.TreeViewColumn(caption, renderer, markup=next_column)
            column.set_resizable( True)
            # Only set "expand" on the first column
            if next_column < self.COLUMN_ADDITIONAL + 1:
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

        column_types = [ int, str, bool ]
        # add string column type plus sort column type if it exists
        for name, sort_name, sort_type, caption in self.columns:
            column_types.append(str)
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

        self.treeviewEpisodes.set_rules_hint( True)
        self.treeviewEpisodes.set_model( self.model)
        self.treeviewEpisodes.columns_autosize()
        self.calculate_total_size()

        selection = self.treeviewEpisodes.get_selection()
        selection.connect('changed', self.on_selection_changed)
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        selection.unselect_all()

        appmenu = hildon.AppMenu()
        for action in (self.action_select_all, \
                       self.action_select_none):
            button = gtk.Button()
            action.connect_proxy(button)
            appmenu.append(button)

        if self.selection_buttons:
            for label in self.selection_buttons:
                button = gtk.Button(label)
                button.connect('clicked', self.custom_selection_button_clicked, label)
                appmenu.append(button)

        appmenu.show_all()
        self.main_window.set_app_menu(appmenu)

    def on_window_orientation_changed(self, orientation):
        self.labelTotalSize.set_property('visible', \
                orientation == Orientation.LANDSCAPE)

    def on_selection_changed(self, selection):
        self.calculate_total_size()

    def on_treeview_button_release(self, widget, event):
        selection = widget.get_selection()
        self.on_selection_changed(widget.get_selection())

    def on_select_all_button_clicked(self, widget):
        selection = self.treeviewEpisodes.get_selection()
        selection.select_all()
        self.calculate_total_size()

    def on_select_none_button_clicked(self, widget):
        selection = self.treeviewEpisodes.get_selection()
        selection.unselect_all()
        self.calculate_total_size()

    def on_close_button_clicked(self, widget):
        self.on_btnCancel_clicked(widget)

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
            else:
                text.append(N_('%d episode', '%d episodes', count) % count)
            if total_size > 0: 
                text.append(_('size: %s') % util.format_filesize(total_size))
            self.labelTotalSize.set_text(', '.join(text))
            self.btnOK.set_sensitive(count>0)
            self.btnRemoveAction.set_sensitive(count>0)
        else:
            selection = self.treeviewEpisodes.get_selection()
            selected_rows = selection.count_selected_rows()
            self.btnOK.set_sensitive(selected_rows > 0)
            self.btnRemoveAction.set_sensitive(selected_rows > 0)
            self.labelTotalSize.set_text('')

    def custom_selection_button_clicked(self, button, label):
        callback = self.selection_buttons[label]

        selection = self.treeviewEpisodes.get_selection()
        selection.unselect_all()
        for index, row in enumerate(self.model):
            if callback(self.episodes[index]):
                selection.select_path(row.path)

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

        # Close the window when there are no episodes left
        model = self.treeviewEpisodes.get_model()
        if model.get_iter_first() is None:
            self.on_btnCancel_clicked(None)

    def get_selected_episodes( self, remove_episodes=False):
        selection = self.treeviewEpisodes.get_selection()
        model, paths = selection.get_selected_rows()

        selected_episodes = [self.episodes[model.get_value(\
                model.get_iter(path), self.COLUMN_INDEX)] \
                for path in paths]

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
        selected = self.get_selected_episodes()
        self.gPodderEpisodeSelector.destroy()
        if self.callback is not None:
            self.callback(selected)

    def on_btnCancel_clicked(self, widget):
        self.gPodderEpisodeSelector.destroy()
        if self.callback is not None:
            self.callback([])

