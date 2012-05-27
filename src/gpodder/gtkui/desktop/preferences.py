# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2012 Thomas Perl and the gPodder Team
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
import pango
import threading
import cgi

import logging
logger = logging.getLogger(__name__)

import gpodder

_ = gpodder.gettext
N_ = gpodder.ngettext

from gpodder import util

from gpodder.gtkui.interface.common import BuilderWidget
from gpodder.gtkui.interface.configeditor import gPodderConfigEditor

from gpodder.gtkui.desktopfile import PlayerListModel

class NewEpisodeActionList(gtk.ListStore):
    C_CAPTION, C_AUTO_DOWNLOAD = range(2)

    ACTION_NONE, ACTION_ASK, ACTION_MINIMIZED, ACTION_ALWAYS = range(4)

    def __init__(self, config):
        gtk.ListStore.__init__(self, str, str)
        self._config = config
        self.append((_('Do nothing'), 'ignore'))
        self.append((_('Show episode list'), 'show'))
        self.append((_('Add to download list'), 'queue'))
        self.append((_('Download immediately'), 'download'))

    def get_index(self):
        for index, row in enumerate(self):
            if self._config.auto_download == row[self.C_AUTO_DOWNLOAD]:
                return index

        return 1 # Some sane default

    def set_index(self, index):
        self._config.auto_download = self[index][self.C_AUTO_DOWNLOAD]


class gPodderFlattrSignIn(BuilderWidget):

    def new(self):
        try:
            import webkit
            
            self.web = webkit.WebView()
            self.web.connect('resource-request-starting', self.on_web_request)            
            
            auth_uri = self.flattr.get_auth_uri()
            logger.info(auth_uri)
            self.web.open(auth_uri)
            
            self.scrolledwindow_web.add(self.web)
            self.web.show()
        except ImportError:
            # TODO: Error-Message
            logger.info('import error webkit')

    def on_web_request(self, web_view, web_frame, web_resource, request, response):
        uri = request.get_uri()
        if uri.startswith(self.flattr.get_callback_uri()):
            logger.info('callback-uri: %s' % uri)
            dummy, code = uri.split('=')
            self._config.flattr.token = self.flattr.request_access_token(code)
            
            # at the moment destroying the window results in a core dump, so we have
            # to save the configuration data so the access token is stored correctly
            # for the next start of gPodder
            self._config.save()
            
            self.gPodderFlattrSignIn.destroy()


class gPodderPreferences(BuilderWidget):
    C_TOGGLE, C_LABEL, C_EXTENSION = range(3)

    def new(self):
        for cb in (self.combo_audio_player_app, self.combo_video_player_app):
            cellrenderer = gtk.CellRendererPixbuf()
            cb.pack_start(cellrenderer, False)
            cb.add_attribute(cellrenderer, 'pixbuf', PlayerListModel.C_ICON)
            cellrenderer = gtk.CellRendererText()
            cellrenderer.set_property('ellipsize', pango.ELLIPSIZE_END)
            cb.pack_start(cellrenderer, True)
            cb.add_attribute(cellrenderer, 'markup', PlayerListModel.C_NAME)
            cb.set_row_separator_func(PlayerListModel.is_separator)

        self.audio_player_model = self.user_apps_reader.get_model('audio')
        self.combo_audio_player_app.set_model(self.audio_player_model)
        index = self.audio_player_model.get_index(self._config.player)
        self.combo_audio_player_app.set_active(index)

        self.video_player_model = self.user_apps_reader.get_model('video')
        self.combo_video_player_app.set_model(self.video_player_model)
        index = self.video_player_model.get_index(self._config.videoplayer)
        self.combo_video_player_app.set_active(index)

        self.update_interval_presets = [0, 10, 30, 60, 2*60, 6*60, 12*60]
        adjustment_update_interval = self.hscale_update_interval.get_adjustment()
        adjustment_update_interval.upper = len(self.update_interval_presets)-1
        if self._config.auto_update_frequency in self.update_interval_presets:
            index = self.update_interval_presets.index(self._config.auto_update_frequency)
            self.hscale_update_interval.set_value(index)
        else:
            # Patch in the current "custom" value into the mix
            self.update_interval_presets.append(self._config.auto_update_frequency)
            self.update_interval_presets.sort()

            adjustment_update_interval.upper = len(self.update_interval_presets)-1
            index = self.update_interval_presets.index(self._config.auto_update_frequency)
            self.hscale_update_interval.set_value(index)

        self._config.connect_gtk_spinbutton('max_episodes_per_feed', self.spinbutton_episode_limit)

        self.auto_download_model = NewEpisodeActionList(self._config)
        self.combo_auto_download.set_model(self.auto_download_model)
        cellrenderer = gtk.CellRendererText()
        self.combo_auto_download.pack_start(cellrenderer, True)
        self.combo_auto_download.add_attribute(cellrenderer, 'text', NewEpisodeActionList.C_CAPTION)
        self.combo_auto_download.set_active(self.auto_download_model.get_index())

        if self._config.auto_remove_played_episodes:
            adjustment_expiration = self.hscale_expiration.get_adjustment()
            if self._config.episode_old_age > adjustment_expiration.get_upper():
                # Patch the adjustment to include the higher current value
                adjustment_expiration.upper = self._config.episode_old_age

            self.hscale_expiration.set_value(self._config.episode_old_age)
        else:
            self.hscale_expiration.set_value(0)

        self._config.connect_gtk_togglebutton('auto_remove_unplayed_episodes', self.checkbutton_expiration_unplayed)
        self._config.connect_gtk_togglebutton('auto_remove_unfinished_episodes', self.checkbutton_expiration_unfinished)

        # Have to do this before calling set_active on checkbutton_enable
        self._enable_mygpo = self._config.mygpo.enabled

        # Initialize the UI state with configuration settings
        self.checkbutton_enable.set_active(self._config.mygpo.enabled)
        self.entry_username.set_text(self._config.mygpo.username)
        self.entry_password.set_text(self._config.mygpo.password)
        self.entry_caption.set_text(self._config.mygpo.device.caption)

        # Disable mygpo sync while the dialog is open
        self._config.mygpo.enabled = False
        
        # Initialize Flattr settings
        self.set_flattr_preferences()

        # Configure the extensions manager GUI
        toggle_cell = gtk.CellRendererToggle()
        toggle_cell.connect('toggled', self.on_extensions_cell_toggled)
        toggle_column = gtk.TreeViewColumn('', toggle_cell, active=self.C_TOGGLE)
        toggle_column.set_clickable(True)
        self.treeviewExtensions.append_column(toggle_column)

        renderer = gtk.CellRendererText()
        renderer.set_property('ellipsize', pango.ELLIPSIZE_END)
        column = gtk.TreeViewColumn(_('Name'), renderer, markup=self.C_LABEL)
        column.set_clickable(False)
        column.set_resizable(True)
        column.set_expand(True)
        self.treeviewExtensions.append_column(column)

        self.extensions_model = gtk.ListStore(bool, str, object)

        for container in gpodder.user_extensions.get_extensions():
            label = '%s\n<small>%s</small>' % (
                    cgi.escape(container.metadata.title),
                    cgi.escape(container.metadata.description))
            self.extensions_model.append([container.enabled, label, container])

        self.extensions_model.set_sort_column_id(self.C_LABEL, gtk.SORT_ASCENDING)
        self.treeviewExtensions.set_model(self.extensions_model)
        self.treeviewExtensions.columns_autosize()
        
    def set_flattr_preferences(self):
        if not self._config.flattr.token:
            self.label_flattr.set_text('Please sign in with Flattr and Support Publishers')
            self.button_flattr_login.set_label('Sign in')
        else:
            flattr_user = self.flattr.get_auth_username()
            self.label_flattr.set_text('You are flattring as %s' % flattr_user)
            self.button_flattr_login.set_label('Sign out')
        
    def on_button_flattr_login(self, widget):
        if not self._config.flattr.token:
            gPodderFlattrSignIn(self.parent_window, _config=self._config, flattr=self.flattr)
        else:
            self._config.flattr.token = ''
        self.set_flattr_preferences()
        
    def on_check_autoflattr(self, widget):
        self._config.flattr.autoflattr = widget.get_active()

    def on_extensions_cell_toggled(self, cell, path):
        model = self.treeviewExtensions.get_model()
        it = model.get_iter(path)
        container = model.get_value(it, self.C_EXTENSION)

        enabled_extensions = list(self._config.extensions.enabled)
        new_enabled = not model.get_value(it, self.C_TOGGLE)

        if new_enabled and container.name not in enabled_extensions:
            enabled_extensions.append(container.name)
        elif not new_enabled and container.name in enabled_extensions:
            enabled_extensions.remove(container.name)

        self._config.extensions.enabled = enabled_extensions

        now_enabled = (container.name in self._config.extensions.enabled)

        if new_enabled == now_enabled:
            model.set_value(it, self.C_TOGGLE, new_enabled)
        elif container.error is not None:
            self.show_message(container.error.message,
                    _('Extension cannot be activated'), important=True)
            model.set_value(it, self.C_TOGGLE, False)

    def on_extensions_row_activated(self, treeview, path, view_column):
        model = treeview.get_model()
        container = model.get_value(model.get_iter(path), self.C_EXTENSION)

        # This is one ugly hack, but it displays the container's attributes
        # and the attributes of the metadata object of the container..
        info = '\n'.join('<b>%s:</b> %s' %
                tuple(map(cgi.escape, map(str, (key, value))))
                for key, value in sorted(container.__dict__.items() +
                    [('metadata.'+k, v)
                        for k, v in container.metadata.__dict__.items()]))

        self.show_message(info, _('Extension module info'), important=True)

    def on_dialog_destroy(self, widget):
        # Re-enable mygpo sync if the user has selected it
        self._config.mygpo.enabled = self._enable_mygpo
        # Make sure the device is successfully created/updated
        self.mygpo_client.create_device()
        # Flush settings for mygpo client now
        self.mygpo_client.flush(now=True)

    def on_button_close_clicked(self, widget):
        self.main_window.destroy()

    def on_button_advanced_clicked(self, widget):
        self.main_window.destroy()
        gPodderConfigEditor(self.parent_window, _config=self._config)

    def on_combo_audio_player_app_changed(self, widget):
        index = self.combo_audio_player_app.get_active()
        self._config.player = self.audio_player_model.get_command(index)

    def on_combo_video_player_app_changed(self, widget):
        index = self.combo_video_player_app.get_active()
        self._config.videoplayer = self.video_player_model.get_command(index)

    def on_button_audio_player_clicked(self, widget):
        result = self.show_text_edit_dialog(_('Configure audio player'), \
                _('Command:'), \
                self._config.player)

        if result:
            self._config.player = result
            index = self.audio_player_model.get_index(self._config.player)
            self.combo_audio_player_app.set_active(index)

    def on_button_video_player_clicked(self, widget):
        result = self.show_text_edit_dialog(_('Configure video player'), \
                _('Command:'), \
                self._config.videoplayer)

        if result:
            self._config.videoplayer = result
            index = self.video_player_model.get_index(self._config.videoplayer)
            self.combo_video_player_app.set_active(index)

    def format_update_interval_value(self, scale, value):
        value = int(value)
        if value == 0:
            return _('manually')
        elif value > 0 and len(self.update_interval_presets) > value:
            return util.format_seconds_to_hour_min_sec(self.update_interval_presets[value]*60)
        else:
            return str(value)

    def on_update_interval_value_changed(self, range):
        value = int(range.get_value())
        self._config.auto_update_feeds = (value > 0)
        self._config.auto_update_frequency = self.update_interval_presets[value]

    def on_combo_auto_download_changed(self, widget):
        index = self.combo_auto_download.get_active()
        self.auto_download_model.set_index(index)

    def format_expiration_value(self, scale, value):
        value = int(value)
        if value == 0:
            return _('manually')
        else:
            return N_('after %(count)d day', 'after %(count)d days', value) % {'count':value}

    def on_expiration_value_changed(self, range):
        value = int(range.get_value())

        if value == 0:
            self.checkbutton_expiration_unplayed.set_active(False)
            self._config.auto_remove_played_episodes = False
            self._config.auto_remove_unplayed_episodes = False
        else:
            self._config.auto_remove_played_episodes = True
            self._config.episode_old_age = value

        self.checkbutton_expiration_unplayed.set_sensitive(value > 0)
        self.checkbutton_expiration_unfinished.set_sensitive(value > 0)

    def on_enabled_toggled(self, widget):
        # Only update indirectly (see on_dialog_destroy)
        self._enable_mygpo = widget.get_active()

    def on_username_changed(self, widget):
        self._config.mygpo.username = widget.get_text()

    def on_password_changed(self, widget):
        self._config.mygpo.password = widget.get_text()

    def on_device_caption_changed(self, widget):
        self._config.mygpo.device.caption = widget.get_text()

    def on_button_overwrite_clicked(self, button):
        title = _('Replace subscription list on server')
        message = _('Remote podcasts that have not been added locally will be removed on the server. Continue?')
        if self.show_confirmation(message, title):
            def thread_proc():
                self._config.mygpo.enabled = True
                self.on_send_full_subscriptions()
                self._config.mygpo.enabled = False
            threading.Thread(target=thread_proc).start()

