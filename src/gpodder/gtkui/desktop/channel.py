# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2010 Thomas Perl and the gPodder Team
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
    def new(self):
        self.gPodderChannel.set_title( self.channel.title)
        self.entryTitle.set_text( self.channel.title)
        self.labelURL.set_text(self.channel.url)
        self.cbSkipFeedUpdate.set_active(not self.channel.feed_update_enabled)

        self.LabelDownloadTo.set_text( self.channel.save_dir)
        self.LabelWebsite.set_text( self.channel.link)

        self.cbNoSync.set_active( not self.channel.sync_to_devices)
        self.musicPlaylist.set_text(self.channel.device_playlist_name)
        if self.channel.username:
            self.FeedUsername.set_text( self.channel.username)
        if self.channel.password:
            self.FeedPassword.set_text( self.channel.password)

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
        targets = [ ('text/uri-list', 0, 2), ('text/plain', 0, 4) ]
        actions = gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_COPY
        self.vboxCoverEditor.drag_dest_set( flags, targets, actions)
        self.vboxCoverEditor.connect( 'drag_data_received', self.drag_data_received)

    def on_btn_website_clicked(self, widget):
        util.open_website(self.channel.link)

    def on_btnDownloadCover_clicked(self, widget):
        dlg = gtk.FileChooserDialog(title=_('Select new podcast cover artwork'), parent=self.gPodderChannel, action=gtk.FILE_CHOOSER_ACTION_OPEN)
        dlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dlg.add_button(gtk.STOCK_OPEN, gtk.RESPONSE_OK)

        if dlg.run() == gtk.RESPONSE_OK:
            url = dlg.get_uri()
            self.cover_downloader.replace_cover(self.channel, url)

        dlg.destroy()

    def on_btnClearCover_clicked(self, widget):
        self.cover_downloader.replace_cover(self.channel)

    def cover_download_finished(self, channel_url, pixbuf):
        if pixbuf is not None:
            self.imgCover.set_from_pixbuf(pixbuf)
        self.gPodderChannel.show()

    def drag_data_received( self, widget, content, x, y, sel, ttype, time):
        files = sel.data.strip().split('\n')
        if len(files) != 1:
            self.show_message( _('You can only drop a single image or URL here.'), _('Drag and drop'))
            return

        file = files[0]

        if file.startswith('file://') or file.startswith('http://'):
            self.cover_downloader.replace_cover(self.channel, file)
            return

        self.show_message( _('You can only drop local files and http:// URLs here.'), _('Drag and drop'))

    def on_gPodderChannel_destroy(self, widget, *args):
        self.cover_downloader.unregister('cover-available', self.cover_download_finished)

    def on_btnOK_clicked(self, widget, *args):
        self.channel.sync_to_devices = not self.cbNoSync.get_active()
        self.channel.feed_update_enabled = not self.cbSkipFeedUpdate.get_active()
        self.channel.device_playlist_name = self.musicPlaylist.get_text()
        self.channel.set_custom_title(self.entryTitle.get_text())
        self.channel.username = self.FeedUsername.get_text().strip()
        self.channel.password = self.FeedPassword.get_text()
        self.channel.save()

        self.cover_downloader.reload_cover_from_disk(self.channel)

        self.gPodderChannel.destroy()
        self.callback_closed()

