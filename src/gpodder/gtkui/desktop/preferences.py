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

import gpodder

_ = gpodder.gettext

from gpodder.gtkui.interface.common import BuilderWidget
from gpodder.gtkui.interface.configeditor import gPodderConfigEditor

class gPodderPreferences(BuilderWidget):
    def new(self):
        if not hasattr( self, 'callback_finished'):
            self.callback_finished = None

        self._config.connect_gtk_editable( 'player', self.openApp)
        self._config.connect_gtk_editable('videoplayer', self.openVideoApp)
        self._config.connect_gtk_editable( 'custom_sync_name', self.entryCustomSyncName)
        self._config.connect_gtk_togglebutton( 'custom_sync_name_enabled', self.cbCustomSyncName)
        self._config.connect_gtk_togglebutton( 'update_on_startup', self.updateonstartup)
        self._config.connect_gtk_togglebutton( 'only_sync_not_played', self.only_sync_not_played)
        self._config.connect_gtk_togglebutton( 'fssync_channel_subfolders', self.cbChannelSubfolder)
        self._config.connect_gtk_togglebutton( 'on_sync_mark_played', self.on_sync_mark_played)
        self._config.connect_gtk_togglebutton( 'on_sync_delete', self.on_sync_delete)
        self._config.connect_gtk_spinbutton('episode_old_age', self.episode_old_age)
        self._config.connect_gtk_togglebutton('auto_remove_old_episodes', self.auto_remove_old_episodes)
        self._config.connect_gtk_togglebutton('auto_update_feeds', self.auto_update_feeds)
        self._config.connect_gtk_spinbutton('auto_update_frequency', self.auto_update_frequency)
        self._config.connect_gtk_togglebutton('display_tray_icon', self.display_tray_icon)
        self._config.connect_gtk_togglebutton('minimize_to_tray', self.minimize_to_tray)
        self._config.connect_gtk_togglebutton('on_quit_systray', self.on_quit_systray)
        self._config.connect_gtk_togglebutton('enable_notifications', self.enable_notifications)
        self._config.connect_gtk_togglebutton('start_iconified', self.start_iconified)
        self._config.connect_gtk_togglebutton('ipod_delete_played_from_db', self.ipod_delete_played_from_db)
        self._config.connect_gtk_togglebutton('mp3_player_delete_played', self.delete_episodes_marked_played)
        self._config.connect_gtk_togglebutton('disable_pre_sync_conversion', self.player_supports_ogg)
        
        self.enable_notifications.set_sensitive(self.display_tray_icon.get_active())
        self.minimize_to_tray.set_sensitive(self.display_tray_icon.get_active())
        self.on_quit_systray.set_sensitive(self.display_tray_icon.get_active())
        
        self.entryCustomSyncName.set_sensitive( self.cbCustomSyncName.get_active())

        self.iPodMountpoint.set_label( self._config.ipod_mount)
        self.filesystemMountpoint.set_label( self._config.mp3_player_folder)
        self.chooserDownloadTo.set_current_folder(self._config.download_dir)

        self.on_sync_delete.set_sensitive(not self.delete_episodes_marked_played.get_active())
        self.on_sync_mark_played.set_sensitive(not self.delete_episodes_marked_played.get_active())
        
        # device type
        self.comboboxDeviceType.set_active( 0)
        if self._config.device_type == 'ipod':
            self.comboboxDeviceType.set_active( 1)
        elif self._config.device_type == 'filesystem':
            self.comboboxDeviceType.set_active( 2)
        elif self._config.device_type == 'mtp':
            self.comboboxDeviceType.set_active( 3)

        # setup cell renderers
        cellrenderer = gtk.CellRendererPixbuf()
        self.comboAudioPlayerApp.pack_start(cellrenderer, False)
        self.comboAudioPlayerApp.add_attribute(cellrenderer, 'pixbuf', 2)
        cellrenderer = gtk.CellRendererText()
        self.comboAudioPlayerApp.pack_start(cellrenderer, True)
        self.comboAudioPlayerApp.add_attribute(cellrenderer, 'markup', 0)

        cellrenderer = gtk.CellRendererPixbuf()
        self.comboVideoPlayerApp.pack_start(cellrenderer, False)
        self.comboVideoPlayerApp.add_attribute(cellrenderer, 'pixbuf', 2)
        cellrenderer = gtk.CellRendererText()
        self.comboVideoPlayerApp.pack_start(cellrenderer, True)
        self.comboVideoPlayerApp.add_attribute(cellrenderer, 'markup', 0)

        if not hasattr(self, 'user_apps_reader'):
            self.user_apps_reader = UserAppsReader(['audio', 'video'])

        self.comboAudioPlayerApp.set_row_separator_func(self.is_row_separator)
        self.comboVideoPlayerApp.set_row_separator_func(self.is_row_separator)

        self.user_apps_reader.read()

        self.comboAudioPlayerApp.set_model(self.user_apps_reader.get_applications_as_model('audio'))
        index = self.find_active_audio_app()
        self.comboAudioPlayerApp.set_active(index)
        self.comboVideoPlayerApp.set_model(self.user_apps_reader.get_applications_as_model('video'))
        index = self.find_active_video_app()
        self.comboVideoPlayerApp.set_active(index)

        # auto download option
        self.comboboxAutoDownload.set_active( 0)
        if self._config.auto_download == 'minimized':
            self.comboboxAutoDownload.set_active( 1)
        elif self._config.auto_download == 'always':
            self.comboboxAutoDownload.set_active( 2)

    def is_row_separator(self, model, iter):
        return model.get_value(iter, 0) == ''

    def update_mountpoint( self, ipod):
        if ipod is None or ipod.mount_point is None:
            self.iPodMountpoint.set_label( '')
        else:
            self.iPodMountpoint.set_label( ipod.mount_point)

    def find_active_audio_app(self):
        index_custom = -1
        model = self.comboAudioPlayerApp.get_model()
        iter = model.get_iter_first()
        index = 0
        while iter is not None:
            command = model.get_value(iter, 1)
            if command == self.openApp.get_text():
                return index
            if index_custom < 0 and command == '':
                index_custom = index
            iter = model.iter_next(iter)
            index += 1
        # return index of custom command or first item
        return max(0, index_custom)

    def find_active_video_app( self):
        index_custom = -1
        model = self.comboVideoPlayerApp.get_model()
        iter = model.get_iter_first()
        index = 0
        while iter is not None:
            command = model.get_value(iter, 1)
            if command == self.openVideoApp.get_text():
                return index
            if index_custom < 0 and command == '':
                index_custom = index
            iter = model.iter_next(iter)
            index += 1
        # return index of custom command or first item
        return max(0, index_custom)
    
    def on_auto_update_feeds_toggled( self, widget, *args):
        self.auto_update_frequency.set_sensitive(widget.get_active())
        
    def on_display_tray_icon_toggled( self, widget, *args):
        self.enable_notifications.set_sensitive(widget.get_active())    
        self.minimize_to_tray.set_sensitive(widget.get_active())    
        self.on_quit_systray.set_sensitive(widget.get_active())
        
    def on_cbCustomSyncName_toggled( self, widget, *args):
        self.entryCustomSyncName.set_sensitive( widget.get_active())

    def on_only_sync_not_played_toggled( self, widget, *args):
        self.delete_episodes_marked_played.set_sensitive( widget.get_active())
        if not widget.get_active():
            self.delete_episodes_marked_played.set_active(False)

    def on_delete_episodes_marked_played_toggled( self, widget, *args):
        if widget.get_active() and self.only_sync_not_played.get_active():
            self.on_sync_leave.set_active(True)
        self.on_sync_delete.set_sensitive(not widget.get_active())
        self.on_sync_mark_played.set_sensitive(not widget.get_active())

    def on_btnCustomSyncNameHelp_clicked( self, widget):
        examples = [
                '<i>{episode.title}</i> -&gt; <b>Interview with RMS</b>',
                '<i>{episode.filename}</i> -&gt; <b>70908-interview-rms</b>',
                '<i>{episode.published}</i> -&gt; <b>20070908</b> (for 08.09.2007)',
                '<i>{episode.pubtime}</i> -&gt; <b>1344</b> (for 13:44)',
                '<i>{podcast.title}</i> -&gt; <b>The Interview Podcast</b>'
        ]

        info = [
                _('You can specify a custom format string for the file names on your MP3 player here.'),
                _('The format string will be used to generate a file name on your device. The file extension (e.g. ".mp3") will be added automatically.'),
                '\n'.join( [ '   %s' % s for s in examples ])
        ]

        self.show_message('\n\n'.join(info), _('Custom format strings'), important=True)

    def on_gPodderPreferences_destroy(self, widget, *args):
        self.on_btnOK_clicked( widget, *args)

    def on_btnConfigEditor_clicked(self, widget, *args):
        gPodderConfigEditor(self.gPodderPreferences, _config=self._config)
        self.on_btnOK_clicked(widget, *args)

    def on_comboAudioPlayerApp_changed(self, widget, *args):
        # find out which one
        iter = self.comboAudioPlayerApp.get_active_iter()
        model = self.comboAudioPlayerApp.get_model()
        command = model.get_value( iter, 1)
        if command == '':
            if self.openApp.get_text() == 'default':
                self.openApp.set_text('')
            self.openApp.set_sensitive( True)
            self.openApp.show()
            self.labelCustomCommand.show()
        else:
            self.openApp.set_text( command)
            self.openApp.set_sensitive( False)
            self.openApp.hide()
            self.labelCustomCommand.hide()

    def on_comboVideoPlayerApp_changed(self, widget, *args):
        # find out which one
        iter = self.comboVideoPlayerApp.get_active_iter()
        model = self.comboVideoPlayerApp.get_model()
        command = model.get_value(iter, 1)
        if command == '':
            if self.openVideoApp.get_text() == 'default':
                self.openVideoApp.set_text('')
            self.openVideoApp.set_sensitive(True)
            self.openVideoApp.show()
            self.labelCustomVideoCommand.show()
        else:
            self.openVideoApp.set_text(command)
            self.openVideoApp.set_sensitive(False)
            self.openVideoApp.hide()
            self.labelCustomVideoCommand.hide()

    def on_cbEnvironmentVariables_toggled(self, widget, *args):
         sens = not self.cbEnvironmentVariables.get_active()
         self.httpProxy.set_sensitive( sens)

    def on_comboboxDeviceType_changed(self, widget, *args):
        active_item = self.comboboxDeviceType.get_active()

        # None
        sync_widgets = ( self.only_sync_not_played, self.labelSyncOptions,
                         self.imageSyncOptions, self. separatorSyncOptions,
                         self.on_sync_mark_played, self.on_sync_delete,
                         self.on_sync_leave, self.label_after_sync,
                         self.delete_episodes_marked_played,
                         self.player_supports_ogg )

        for widget in sync_widgets:
            if active_item == 0:
                widget.hide_all()
            else:
                widget.show_all()

        # iPod
        ipod_widgets = (self.ipodLabel, self.btn_iPodMountpoint,
                        self.ipod_delete_played_from_db)

        for widget in ipod_widgets:
            if active_item == 1:
                widget.show_all()
            else:
                widget.hide_all()

        # filesystem-based MP3 player
        fs_widgets = ( self.filesystemLabel, self.btn_filesystemMountpoint,
                       self.cbChannelSubfolder, self.cbCustomSyncName,
                       self.entryCustomSyncName, self.btnCustomSyncNameHelp,
                       self.player_supports_ogg )

        for widget in fs_widgets:
            if active_item == 2:
                widget.show_all()
            else:
                widget.hide_all()

    def on_btn_iPodMountpoint_clicked(self, widget, *args):
        fs = gtk.FileChooserDialog( title = _('Select iPod mountpoint'), action = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
        fs.add_button( gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        fs.add_button( gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        fs.set_current_folder(self.iPodMountpoint.get_label())
        if fs.run() == gtk.RESPONSE_OK:
            self.iPodMountpoint.set_label( fs.get_filename())
        fs.destroy()

    def on_btn_FilesystemMountpoint_clicked(self, widget, *args):
        fs = gtk.FileChooserDialog( title = _('Select folder for MP3 player'), action = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
        fs.add_button( gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        fs.add_button( gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        fs.set_current_folder(self.filesystemMountpoint.get_label())
        if fs.run() == gtk.RESPONSE_OK:
            self.filesystemMountpoint.set_label( fs.get_filename())
        fs.destroy()

    def on_btnOK_clicked(self, widget, *args):
        self._config.ipod_mount = self.iPodMountpoint.get_label()
        self._config.mp3_player_folder = self.filesystemMountpoint.get_label()

        # FIXME: set self._config.download_dir to self.chooserDownloadTo.get_filename() and move download folder!

        device_type = self.comboboxDeviceType.get_active()
        if device_type == 0:
            self._config.device_type = 'none'
        elif device_type == 1:
            self._config.device_type = 'ipod'
        elif device_type == 2:
            self._config.device_type = 'filesystem'
        elif device_type == 3:
            self._config.device_type = 'mtp'

        auto_download = self.comboboxAutoDownload.get_active()
        if auto_download == 0:
            self._config.auto_download = 'never'
        elif auto_download == 1:
            self._config.auto_download = 'minimized'
        elif auto_download == 2:
            self._config.auto_download = 'always'
        self.gPodderPreferences.destroy()
        if self.callback_finished:
            self.callback_finished()

