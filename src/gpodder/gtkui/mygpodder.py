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

# gpodder.gtkui.mygpodder- UI code for my.gpodder.org settings
# Thomas Perl <thpinfo.com>; 2010-01-19

import gtk
import threading

import gpodder

_ = gpodder.gettext

from gpodder import util

from gpodder.gtkui.interface.progress import ProgressIndicator
from gpodder.gtkui.interface.common import BuilderWidget


class DeviceList(gtk.ListStore):
    C_UID, C_CAPTION, C_DEVICE_TYPE, C_ICON_NAME = range(4)

    def __init__(self, devices):
        gtk.ListStore.__init__(self, str, str, str, str)
        for uid, caption, device_type in devices:
            if device_type == 'desktop':
                icon_name = 'computer'
            elif device_type == 'mobile':
                icon_name = 'phone'
            elif device_type == 'server':
                icon_name = 'server'
            elif device_type == 'laptop':
                icon_name = 'stock_notebook'
            else:
                icon_name = 'audio-x-generic'
            self.append((uid, caption, device_type, icon_name))

class DeviceBrowser(gtk.Dialog):
    def __init__(self, model, parent=None):
        gtk.Dialog.__init__(self, _('Select a device'), parent)

        self._model = model

        hbox = gtk.HBox()
        hbox.set_border_width(6)
        hbox.set_spacing(6)
        self.vbox.add(hbox)
        hbox.pack_start(gtk.Label(_('Device:')), expand=False)

        combobox = gtk.ComboBox()
        hbox.add(combobox)
        cell = gtk.CellRendererPixbuf()
        combobox.pack_start(cell, expand=False)
        combobox.add_attribute(cell, 'icon-name', DeviceList.C_ICON_NAME)
        cell = gtk.CellRendererText()
        combobox.pack_start(cell)
        combobox.add_attribute(cell, 'text', DeviceList.C_CAPTION)

        combobox.set_model(self._model)
        combobox.set_active(0)
        self._combobox = combobox

        self.add_button(_('Cancel'), gtk.RESPONSE_CANCEL)
        self.add_button(_('Use device'), gtk.RESPONSE_OK)

    def get_selected(self):
        result = None

        self.show_all()
        if self.run() == gtk.RESPONSE_OK:
            active = self._combobox.get_active()
            result = (self._model[active][DeviceList.C_UID],
                      self._model[active][DeviceList.C_CAPTION],
                      self._model[active][DeviceList.C_DEVICE_TYPE])
        self.destroy()

        return result


class MygPodderSettings(BuilderWidget):
    # Valid types defined in mygpoclient.api.PodcastDevice
    VALID_TYPES = (
            ('desktop', _('Desktop')),
            ('laptop', _('Laptop')),
            ('mobile', _('Mobile phone')),
            ('server', _('Server')),
            ('other', _('Other')),
    )

    # Columns IDs for the combo box model
    C_ID, C_CAPTION = range(2)

    def new(self):
        # We need to have a MygPoClient instance available
        assert getattr(self, 'mygpo_client', None) is not None

        active_index = 0
        self._model = gtk.ListStore(str, str)
        for index, data in enumerate(self.VALID_TYPES):
            id, caption = data
            if id == self.config.mygpo_device_type:
                active_index = index
            self._model.append(data)
        self.combo_type.set_model(self._model)

        cell = gtk.CellRendererText()
        self.combo_type.pack_start(cell, True)
        self.combo_type.add_attribute(cell, 'text', 1)

        # Initialize the UI state with configuration settings
        self.checkbutton_enable.set_active(self.config.mygpo_enabled)
        self.entry_username.set_text(self.config.mygpo_username)
        self.entry_password.set_text(self.config.mygpo_password)
        self.label_uid_value.set_label(self.config.mygpo_device_uid)
        self.entry_caption.set_text(self.config.mygpo_device_caption)
        self.combo_type.set_active(active_index)

        if gpodder.ui.fremantle:
            self.checkbutton_enable.set_name('HildonButton-finger')
            self.button_overwrite.set_name('HildonButton-finger')
            self.button_list_uids.set_name('HildonButton-finger')

        # Disable mygpo sync while the dialog is open
        self._enable_mygpo = self.config.mygpo_enabled
        self.config.mygpo_enabled = False

    def on_enabled_toggled(self, widget):
        # Only update indirectly (see on_delete_event)
        self._enable_mygpo = widget.get_active()

    def on_username_changed(self, widget):
        self.config.mygpo_username = widget.get_text()

    def on_password_changed(self, widget):
        self.config.mygpo_password = widget.get_text()

    def on_device_caption_changed(self, widget):
        self.config.mygpo_device_caption = widget.get_text()

    def on_device_type_changed(self, widget):
        model = widget.get_model()
        it = widget.get_active_iter()
        device_type = model.get_value(it, self.C_ID)
        self.config.mygpo_device_type = device_type

    def on_button_overwrite_clicked(self, button):
        title = _('Replace subscription list on server')
        message = _('Remote podcasts that have not been added locally will be removed on the server. Continue?')
        if self.show_confirmation(message, title):
            def thread_proc():
                self.config.mygpo_enabled = True
                self.on_send_full_subscriptions()
                self.config.mygpo_enabled = False
            threading.Thread(target=thread_proc).start()

    def on_button_list_uids_clicked(self, button):
        indicator = ProgressIndicator(_('Downloading device list'),
                _('Getting the list of devices from your account.'),
                False, self.main_window)

        def thread_proc():
            try:
                devices = self.mygpo_client.get_devices()
            except Exception, e:
                indicator.on_finished()
                def show_error(e):
                    if str(e):
                        message = str(e)
                    else:
                        message = e.__class__.__name__
                    self.show_message(message,
                            _('Error getting list'),
                            important=True)
                util.idle_add(show_error, e)
                return

            indicator.on_finished()

            def ui_callback(devices):
                model = DeviceList(devices)
                dialog = DeviceBrowser(model, self.main_window)
                result = dialog.get_selected()
                if result is not None:
                    uid, caption, device_type = result

                    # Update config and label with new UID
                    self.config.mygpo_device_uid = uid
                    self.label_uid_value.set_label(uid)

                    self.entry_caption.set_text(caption)
                    for index, data in enumerate(self.VALID_TYPES):
                        d_type, d_name = data
                        if device_type == d_type:
                            self.combo_type.set_active(index)
                            break
            util.idle_add(ui_callback, devices)

        threading.Thread(target=thread_proc).start()

    def on_delete_event(self, widget, event):
        # Re-enable mygpo sync if the user has selected it
        self.config.mygpo_enabled = self._enable_mygpo
        # Flush settings for mygpo client now
        self.mygpo_client.flush(now=True)

    def on_button_close_clicked(self, button):
        self.on_delete_event(self.main_window, None)
        self.main_window.destroy()

