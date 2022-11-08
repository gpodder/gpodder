# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2018 The gPodder Team
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

from gi.repository import Gdk, Gio, Gtk

import gpodder
from gpodder import util
from gpodder.gtkui.interface.common import BuilderWidget

_ = gpodder.gettext


class gPodderChannel(BuilderWidget):
    MAX_SIZE = 120

    def new(self):
        self.show_on_cover_load = True

        self.gPodderChannel.set_transient_for(self.parent_widget)
        self.title_label.set_text(self.channel.title)
        self.labelURL.set_text(self.channel.url)
        self.skip_feed_update_switch.set_active(self.channel.pause_subscription)
        self.enable_device_sync_switch.set_active(self.channel.sync_to_mp3_player)

        self.section_list = Gtk.ListStore(str)
        active_index = 0
        for index, section in enumerate(sorted(self.sections)):
            self.section_list.append([section])
            if section == self.channel.section:
                active_index = index
        self.combo_section.set_model(self.section_list)
        cell_renderer = Gtk.CellRendererText()
        self.combo_section.pack_start(cell_renderer, True)
        self.combo_section.add_attribute(cell_renderer, 'text', 0)
        self.combo_section.set_active(active_index)

        self.strategy_list = Gtk.ListStore(str, int)
        active_index = 0
        for index, (checked, strategy_id, strategy) in \
                enumerate(self.channel.get_download_strategies()):
            self.strategy_list.append([strategy, strategy_id])
            if checked:
                active_index = index
        self.combo_strategy.set_model(self.strategy_list)
        cell_renderer = Gtk.CellRendererText()
        self.combo_strategy.pack_start(cell_renderer, True)
        self.combo_strategy.add_attribute(cell_renderer, 'text', 0)
        self.combo_strategy.set_active(active_index)

        self.LabelDownloadTo.set_text(self.channel.save_dir)
        self.website_label.set_markup('<a href="{}">{}</a>'.format(
            self.channel.link, self.channel.link)
            if self.channel.link else '')
        self.website_label.connect('activate-link', lambda label, url: util.open_website(url))

        if self.channel.auth_username:
            self.FeedUsername.set_text(self.channel.auth_username)
        if self.channel.auth_password:
            self.FeedPassword.set_text(self.channel.auth_password)

        # Cover image
        ag = Gio.SimpleActionGroup()
        open_cover_action = Gio.SimpleAction.new("openCover", None)
        open_cover_action.connect('activate', self.on_open_cover_activate)
        ag.add_action(open_cover_action)
        refresh_cover_action = Gio.SimpleAction.new("refreshCover", None)
        refresh_cover_action.connect('activate', self.on_refresh_cover_activate)
        ag.add_action(refresh_cover_action)
        self.main_window.insert_action_group("channel", ag)

        cover_menu = Gio.Menu()
        cover_menu.append("Change cover image", "channel.openCover")
        cover_menu.append("Refresh image", "channel.refreshCover")

        self.cover_menubutton.set_menu_model(cover_menu)

        self.cover_downloader.register('cover-available', self.cover_download_finished)
        self.cover_downloader.request_cover(self.channel)

        if self.channel._update_error:
            err = '\n\n' + (_('ERROR: %s') % self.channel._update_error)
        else:
            err = ''
        self.channel_description.set_text(util.remove_html_tags(self.channel.description) + err)

        # Add Drag and Drop Support
        flags = Gtk.DestDefaults.ALL
        targets = [Gtk.TargetEntry.new('text/uri-list', 0, 2), Gtk.TargetEntry.new('text/plain', 0, 4)]
        actions = Gdk.DragAction.DEFAULT | Gdk.DragAction.COPY
        self.imgCover.drag_dest_set(flags, targets, actions)
        self.imgCover.connect('drag_data_received', self.drag_data_received)
        border = 6
        size = self.MAX_SIZE + border * 2
        self.imgCover.set_size_request(size, size)

        # Title save button state
        self.title_save_button_saves = True

        self._config.connect_gtk_window(self.gPodderChannel, 'channel_editor', True)

        gpodder.user_extensions.on_ui_object_available('channel-gtk', self)

        result = gpodder.user_extensions.on_channel_settings(self.channel)
        if result:
            for label, callback in result:
                sw = Gtk.ScrolledWindow()
                sw.add(callback(self.channel))
                sw.show_all()
                self.notebookChannelEditor.append_page(sw, Gtk.Label(label))

    def on_button_add_section_clicked(self, widget):
        text = self.show_text_edit_dialog(_('Add section'), _('New section:'),
            affirmative_text=_('_Add'))

        if text is not None:
            for index, (section,) in enumerate(self.section_list):
                if text == section:
                    self.combo_section.set_active(index)
                    return

            self.section_list.append([text])
            self.combo_section.set_active(len(self.section_list) - 1)

    def on_open_cover_activate(self, action, *args):
        dlg = Gtk.FileChooserDialog(
            title=_('Select new podcast cover artwork'),
            parent=self.gPodderChannel,
            action=Gtk.FileChooserAction.OPEN)
        dlg.add_button(_('_Cancel'), Gtk.ResponseType.CANCEL)
        dlg.add_button(_('_Open'), Gtk.ResponseType.OK)

        if dlg.run() == Gtk.ResponseType.OK:
            url = dlg.get_uri()
            self.clear_cover_cache(self.channel.url)
            self.cover_downloader.replace_cover(self.channel, custom_url=url)

        dlg.destroy()

    def on_refresh_cover_activate(self, action, *args):
        self.clear_cover_cache(self.channel.url)
        self.cover_downloader.replace_cover(self.channel, custom_url=False)

    def cover_download_finished(self, channel, pixbuf):
        def set_cover(channel, pixbuf):
            if self.channel == channel:
                if pixbuf is not None:
                    self.imgCover.set_from_pixbuf(util.scale_pixbuf(pixbuf, self.MAX_SIZE))
                if self.show_on_cover_load:
                    self.main_window.show()
                    self.show_on_cover_load = False

        util.idle_add(set_cover, channel, pixbuf)

    def drag_data_received(self, widget, content, x, y, sel, ttype, time):
        files = sel.get_text().strip().split('\n')
        if len(files) != 1:
            self.show_message(
                _('You can only drop a single image or URL here.'),
                _('Drag and drop'))
            return

        file = files[0]

        if file.startswith('file://') or file.startswith('http://') or file.startswith('https://'):
            self.clear_cover_cache(self.channel.url)
            self.cover_downloader.replace_cover(self.channel, custom_url=file)
            return

        self.show_message(
            _('You can only drop local files and http:// URLs here.'),
            _('Drag and drop'))

    def on_gPodderChannel_destroy(self, widget, *args):
        self.cover_downloader.unregister('cover-available', self.cover_download_finished)

    # Title editing callbacks
    def on_title_edit_button_clicked(self, button):
        self.title_save_button_saves = True
        self.title_save_button.set_label(_("_Save"))
        self.title_stack.set_visible_child(self.title_edit_box)
        self.title_entry.set_text(self.title_label.get_text())
        self.title_entry.grab_focus()

    def on_title_entry_changed(self, entry):
        if len(entry.get_text()) > 0:
            self.title_save_button_saves = True
            self.title_save_button.set_label(_("_Save"))
        else:
            self.title_save_button_saves = False
            self.title_save_button.set_label(_("Cancel"))

    def on_title_entry_icon_press(self, entry, icon_pos, *args):
        self.title_entry.set_text("")

    def on_title_save_button_clicked(self, button):
        if self.title_save_button_saves:
            self.title_label.set_text(self.title_entry.get_text())
        self.title_stack.set_visible_child(self.title_box)

    def on_feed_url_copy_button_clicked(self, button):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(self.channel.url, -1)

    def on_open_folder_button_clicked(self, button):
        util.gui_open(self.channel.save_dir, gui=self)

    def on_row_activated(self, listbox, row, *args):
        # Find the correct widget in the row to activate
        def _do(w, *args):
            if w.get_name().startswith("no_activation"):
                return
            elif isinstance(w, Gtk.Box):
                w.foreach(_do)
            elif isinstance(w, Gtk.ComboBox):
                w.popup()
            elif isinstance(w, Gtk.Entry):
                w.grab_focus()
            elif isinstance(w, Gtk.Switch):
                w.set_state(not w.get_state())
            elif isinstance(w, Gtk.Button):
                w.emit("clicked")
        row.foreach(_do)

    def on_btnCancel_clicked(self, widget, *args):
        self.main_window.destroy()

    def on_btnOK_clicked(self, widget, *args):
        self.channel.pause_subscription = self.skip_feed_update_switch.get_state()
        self.channel.sync_to_mp3_player = self.enable_device_sync_switch.get_state()
        self.channel.rename(self.title_label.get_text())
        self.channel.auth_username = self.FeedUsername.get_text().strip()
        self.channel.auth_password = self.FeedPassword.get_text()

        self.cover_downloader.unregister('cover-available', self.cover_download_finished)
        self.clear_cover_cache(self.channel.url)
        self.cover_downloader.request_cover(self.channel)

        new_section = self.section_list[self.combo_section.get_active()][0]
        if self.channel.section != new_section:
            self.channel.section = new_section
            section_changed = True
        else:
            section_changed = False

        new_strategy = self.strategy_list[self.combo_strategy.get_active()][1]
        self.channel.set_download_strategy(new_strategy)

        self.channel.save()

        self.main_window.destroy()

        self.update_podcast_list_model(selected=True,
                sections_changed=section_changed)
