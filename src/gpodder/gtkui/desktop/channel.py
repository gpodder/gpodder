# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2015 Thomas Perl and the gPodder Team
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
import gtk.gdk

import gpodder

_ = gpodder.gettext

from gpodder import util

from gpodder.gtkui.interface.common import BuilderWidget


class gPodderChannel(BuilderWidget):
    MAX_SIZE = 120

    def new(self):
        self.show_on_cover_load = True

        self.gPodderChannel.set_title( self.channel.title)
        self.entryTitle.set_text( self.channel.title)
        self.labelURL.set_text(self.channel.url)
        self.cbSkipFeedUpdate.set_active(self.channel.pause_subscription)
        self.cbEnableDeviceSync.set_active(self.channel.sync_to_mp3_player)

        self.section_list = gtk.ListStore(str)
        active_index = 0
        for index, section in enumerate(sorted(self.sections)):
            self.section_list.append([section])
            if section == self.channel.section:
                active_index = index
        self.combo_section.set_model(self.section_list)
        cell_renderer = gtk.CellRendererText()
        self.combo_section.pack_start(cell_renderer)
        self.combo_section.add_attribute(cell_renderer, 'text', 0)
        self.combo_section.set_active(active_index)

        self.strategy_list = gtk.ListStore(str, int)
        active_index = 0
        for index, (checked, strategy_id, strategy) in \
            enumerate(self.channel.get_download_strategies()):
            self.strategy_list.append([strategy, strategy_id])
            if checked:
                active_index = index
        self.combo_strategy.set_model(self.strategy_list)
        cell_renderer = gtk.CellRendererText()
        self.combo_strategy.pack_start(cell_renderer)
        self.combo_strategy.add_attribute(cell_renderer, 'text', 0)
        self.combo_strategy.set_active(active_index)

        self.LabelDownloadTo.set_text( self.channel.save_dir)
        self.LabelWebsite.set_text( self.channel.link)

        if self.channel.auth_username:
            self.FeedUsername.set_text( self.channel.auth_username)
        if self.channel.auth_password:
            self.FeedPassword.set_text( self.channel.auth_password)

        self.cover_downloader.register('cover-available', self.cover_download_finished)
        self.cover_downloader.request_cover(self.channel)

        # Hide the website button if we don't have a valid URL
        if not self.channel.link:
            self.btn_website.hide_all()

        b = gtk.TextBuffer()
        b.set_text( self.channel.description)
        self.channel_description.set_buffer( b)

        #Add Drag and Drop Support
        flags = gtk.DEST_DEFAULT_ALL
        targets = [('text/uri-list', 0, 2), ('text/plain', 0, 4)]
        actions = gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_COPY
        self.imgCover.drag_dest_set(flags, targets, actions)
        self.imgCover.connect('drag_data_received', self.drag_data_received)
        border = 6
        self.imgCover.set_size_request(*((self.MAX_SIZE+border*2,)*2))
        self.imgCoverEventBox.connect('button-press-event',
                self.on_cover_popup_menu)

    def on_button_add_section_clicked(self, widget):
        text = self.show_text_edit_dialog(_('Add section'), _('New section:'),
            affirmative_text=gtk.STOCK_ADD)

        if text is not None:
            for index, (section,) in enumerate(self.section_list):
                if text == section:
                    self.combo_section.set_active(index)
                    return

            self.section_list.append([text])
            self.combo_section.set_active(len(self.section_list)-1)

    def on_cover_popup_menu(self, widget, event):
        if event.button != 3:
            return

        menu = gtk.Menu()

        item = gtk.ImageMenuItem(gtk.STOCK_OPEN)
        item.connect('activate', self.on_btnDownloadCover_clicked)
        menu.append(item)

        item = gtk.ImageMenuItem(gtk.STOCK_REFRESH)
        item.connect('activate', self.on_btnClearCover_clicked)
        menu.append(item)

        menu.show_all()
        menu.popup(None, None, None, event.button, event.time, None)

    def on_btn_website_clicked(self, widget):
        util.open_website(self.channel.link)

    def on_btnDownloadCover_clicked(self, widget):
        dlg = gtk.FileChooserDialog(title=_('Select new podcast cover artwork'), parent=self.gPodderChannel, action=gtk.FILE_CHOOSER_ACTION_OPEN)
        dlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dlg.add_button(gtk.STOCK_OPEN, gtk.RESPONSE_OK)

        if dlg.run() == gtk.RESPONSE_OK:
            url = dlg.get_uri()
            self.clear_cover_cache(self.channel.url)
            self.cover_downloader.replace_cover(self.channel, custom_url=url)

        dlg.destroy()

    def on_btnClearCover_clicked(self, widget):
        self.clear_cover_cache(self.channel.url)
        self.cover_downloader.replace_cover(self.channel, custom_url=False)

    def cover_download_finished(self, channel, pixbuf):
        def set_cover(channel, pixbuf):
            if self.channel == channel:
                self.imgCover.set_from_pixbuf(self.scale_pixbuf(pixbuf))
                if self.show_on_cover_load:
                    self.main_window.show()
                    self.show_on_cover_load = False

        util.idle_add(set_cover, channel, pixbuf)

    def drag_data_received( self, widget, content, x, y, sel, ttype, time):
        files = sel.data.strip().split('\n')
        if len(files) != 1:
            self.show_message( _('You can only drop a single image or URL here.'), _('Drag and drop'))
            return

        file = files[0]

        if file.startswith('file://') or file.startswith('http://'):
            self.clear_cover_cache(self.channel.url)
            self.cover_downloader.replace_cover(self.channel, custom_url=file)
            return

        self.show_message( _('You can only drop local files and http:// URLs here.'), _('Drag and drop'))

    def on_gPodderChannel_destroy(self, widget, *args):
        self.cover_downloader.unregister('cover-available', self.cover_download_finished)

    def scale_pixbuf(self, pixbuf):

        # Resize if width is too large
        if pixbuf.get_width() > self.MAX_SIZE:
            f = float(self.MAX_SIZE)/pixbuf.get_width()
            (width, height) = (int(pixbuf.get_width()*f), int(pixbuf.get_height()*f))
            pixbuf = pixbuf.scale_simple(width, height, gtk.gdk.INTERP_BILINEAR)

        # Resize if height is too large
        if pixbuf.get_height() > self.MAX_SIZE:
            f = float(self.MAX_SIZE)/pixbuf.get_height()
            (width, height) = (int(pixbuf.get_width()*f), int(pixbuf.get_height()*f))
            pixbuf = pixbuf.scale_simple(width, height, gtk.gdk.INTERP_BILINEAR)

        return pixbuf

    def on_btnOK_clicked(self, widget, *args):
        self.channel.pause_subscription = self.cbSkipFeedUpdate.get_active()
        self.channel.sync_to_mp3_player = self.cbEnableDeviceSync.get_active()
        self.channel.rename(self.entryTitle.get_text())
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

