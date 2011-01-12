# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
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

from xml.sax import saxutils

class gPodderChannel(BuilderWidget):
    def new(self):
        self.title_updated()

        self.cover_downloader.register('cover-available', \
                self.cover_download_finished)
        self.cover_downloader.request_cover(self.channel)

        b = self.textview.get_buffer()
        b.set_text(self.channel.description)
        b.place_cursor(b.get_start_iter())
        self.main_window.show()

        menu = gtk.Menu()
        menu.append(self.action_rename.create_menu_item())
        menu.append(self.action_authentication.create_menu_item())
        menu.append(gtk.SeparatorMenuItem())
        menu.append(self.action_refresh_cover.create_menu_item())
        menu.append(self.action_custom_cover.create_menu_item())
        menu.append(gtk.SeparatorMenuItem())
        menu.append(self.action_visit_website.create_menu_item())
        menu.append(gtk.SeparatorMenuItem())
        menu.append(self.action_close.create_menu_item())
        self.main_window.set_menu(self.set_finger_friendly(menu))
        self.main_window.connect('key-press-event', self._on_key_press_event)

    def _on_key_press_event(self, widget, event):
        if event.keyval == gtk.keysyms.Escape:
            self.on_close_button_clicked(widget)
            return True
        else:
            return False

    def title_updated(self):
        self.main_window.set_title(_('Edit %s') % self.channel.title)
        self.label_title.set_markup('<b><big>%s</big></b>\n%s' % (\
                saxutils.escape(self.channel.title),
                saxutils.escape(self.channel.url)))

    def on_custom_cover_button_clicked(self, widget):
        import hildon
        dlg = hildon.FileChooserDialog(self.main_window, \
                gtk.FILE_CHOOSER_ACTION_OPEN)

        if dlg.run() == gtk.RESPONSE_OK:
            url = dlg.get_uri()
            self.cover_downloader.replace_cover(self.channel, url)

        dlg.destroy()

    def on_rename_button_clicked(self, widget):
        new_title = self.show_text_edit_dialog(_('Rename podcast'), \
                _('New name:'), self.channel.title)
        if new_title is not None and new_title != self.channel.title:
            self.channel.set_custom_title(new_title)
            self.title_updated()
            self.channel.save()
            self.show_message(_('New name: %s') % new_title, \
                    _('Podcast renamed'))

    def on_authentication_button_clicked(self, widget):
        title = _('Edit podcast authentication')
        message = _('Please enter your username and password.')
        success, auth_tokens = self.show_login_dialog(title, message, \
                username=self.channel.username, password=self.channel.password)
        if success:
            username, password = auth_tokens
            if self.channel.username != username or \
               self.channel.password != password:
                self.channel.username = username
                self.channel.password = password
                self.channel.save()
                if not username and not password:
                    self.show_message(_('Username and password removed.'), \
                            _('Authentication updated'))
                else:
                    self.show_message(_('Username and password saved.'), \
                            _('Authentication updated'))

    def on_refresh_cover_button_clicked(self, widget):
        self.cover_downloader.replace_cover(self.channel)
        self.cover_downloader.request_cover(self.channel)

    def on_visit_website_button_clicked(self, widget):
        util.open_website(self.channel.link)

    def on_close_button_clicked(self, widget):
        self.main_window.destroy()

    def cover_download_finished(self, channel_url, pixbuf):
        if channel_url == self.channel.url:
            if pixbuf is None:
                self.image_cover.set_size_request(-1, -1)
                self.image_cover.clear()
            else:
                target_width, target_height = 128, 128
                width, height = pixbuf.get_width(), pixbuf.get_height()
                if width > height:
                    target_height = int(target_height*height/width)
                elif height > width:
                    target_width = int(target_width*width/height)

                pixbuf = pixbuf.scale_simple(target_width, target_height, \
                        gtk.gdk.INTERP_BILINEAR)
                self.image_cover.set_size_request(128, 128)
                self.image_cover.set_from_pixbuf(pixbuf)

    def on_gPodderChannel_destroy(self, widget):
        self.cover_downloader.unregister('cover-available', \
                self.cover_download_finished)
        self.callback_closed()

