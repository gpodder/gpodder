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

import html
import logging
import os
import sys
import xml.etree.ElementTree as ET

try:
    import dbus
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop
except ImportError:
    print("Error: 'dbus' module not found. Either dbus-python or fake-dbus is required",
          file=sys.stderr)
    sys.exit(1)

import gpodder
from gpodder import core, util
from gpodder.model import check_root_folder_path

from .config import UIConfig
from .desktop.preferences import gPodderPreferences
from .main import gPodder
from .model import Model

import gi  # isort:skip
gi.require_version('Gtk', '3.0')  # isort:skip
from gi.repository import GdkPixbuf, Gio, GLib, Gtk  # isort:skip


logger = logging.getLogger(__name__)

_ = gpodder.gettext
N_ = gpodder.ngettext


def parse_app_menu_for_accels(filename):
    """Grab (accelerator, action) bindings from menus.ui.

    See #815 Ctrl-Q doesn't quit for justification.
    Unfortunately it's not available from the Gio.MenuModel we get from the Gtk.Builder,
    so we get it ourself.
    """
    res = []
    menu_tree = ET.parse(filename)
    assert menu_tree.getroot().tag == 'interface'
    for menu in menu_tree.getroot():
        assert menu.tag == 'menu'
        if menu.attrib.get('id') == 'app-menu':
            for itm in menu.iter('item'):
                action = None
                accel = None
                for att in itm.findall('attribute'):
                    if att.get('name') == 'action':
                        action = att.text.strip()
                    elif att.get('name') == 'accel':
                        accel = att.text.strip()
                if action and accel:
                    res.append((accel, action))
    return res


class gPodderApplication(Gtk.Application):

    def __init__(self, options):
        Gtk.Application.__init__(self, application_id='org.gpodder.gpodder',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None
        self.options = options
        self.gdbus_connection = None
        self.connect('window-removed', self.on_window_removed)
        self.connect('notify::is-registered', self.on_notify_is_registered)

    def create_actions(self):
        action = Gio.SimpleAction.new('about', None)
        action.connect('activate', self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new('quit', None)
        action.connect('activate', self.on_quit)
        self.add_action(action)

        action = Gio.SimpleAction.new('help', None)
        action.connect('activate', self.on_help_activate)
        self.add_action(action)

        action = Gio.SimpleAction.new('logs', None)
        action.connect('activate', self.on_logs_activate)
        self.add_action(action)

        action = Gio.SimpleAction.new('preferences', None)
        action.connect('activate', self.on_itemPreferences_activate)
        self.add_action(action)

        action = Gio.SimpleAction.new('gotoMygpo', None)
        action.connect('activate', self.on_goto_mygpo)
        self.add_action(action)

        action = Gio.SimpleAction.new('checkForUpdates', None)
        action.connect('activate', self.on_check_for_updates_activate)
        self.add_action(action)

        action = Gio.SimpleAction.new('menu', None)
        action.connect('activate', self.on_menu)
        self.add_action(action)

        action = Gio.SimpleAction.new('subscribe_to_url', GLib.VariantType.new('s'))
        action.connect('activate', self.on_subscribe_to_url_activate)
        self.add_action(action)

    def do_startup(self):
        Gtk.Application.do_startup(self)

        self.create_actions()

        builder = Gtk.Builder()
        builder.set_translation_domain(gpodder.textdomain)
        self.builder = builder

        menu_filename = None
        for ui_folder in gpodder.ui_folders:
            filename = os.path.join(ui_folder, 'gtk/menus.ui')
            if os.path.exists(filename):
                builder.add_from_file(filename)
                menu_filename = filename
                break

        menubar = builder.get_object('menubar')
        if menubar is None:
            logger.error('Cannot find gtk/menus.ui in %r, exiting' % gpodder.ui_folders)
            sys.exit(1)

        self.menu_extras = builder.get_object('menuExtras')
        self.menu_view_columns = builder.get_object('menuViewColumns')
        self.set_menubar(menubar)

        # If $XDG_CURRENT_DESKTOP is set then it contains a colon-separated list of strings.
        # https://specifications.freedesktop.org/desktop-entry-spec/desktop-entry-spec-latest.html
        # See https://askubuntu.com/a/227669 for a list of values in different environments
        xdg_current_desktops = os.environ.get('XDG_CURRENT_DESKTOP', '').split(':')
        # See https://developer.gnome.org/gtk3/stable/gtk-running.html
        # GTK_CSD=0 is used to disable client side decorations
        csd_disabled = os.environ.get('GTK_CSD') == '0'

        self.want_headerbar = ('GNOME' in xdg_current_desktops) and not gpodder.ui.osx and not csd_disabled

        self.app_menu = builder.get_object('app-menu')
        if self.want_headerbar:
            # Use GtkHeaderBar for client-side decorations on recent GNOME 3 versions
            self.header_bar_menu_button = Gtk.Button.new_from_icon_name('open-menu-symbolic', Gtk.IconSize.SMALL_TOOLBAR)
            self.header_bar_menu_button.set_action_name('app.menu')

            self.header_bar_refresh_button = Gtk.Button.new_from_icon_name('view-refresh-symbolic', Gtk.IconSize.SMALL_TOOLBAR)
            self.header_bar_refresh_button.set_action_name('win.updateChannel')

            self.menu_popover = Gtk.Popover.new_from_model(self.header_bar_menu_button, self.app_menu)
            self.menu_popover.set_position(Gtk.PositionType.BOTTOM)

            for (accel, action) in parse_app_menu_for_accels(menu_filename):
                self.add_accelerator(accel, action, None)

        else:
            self.set_app_menu(self.app_menu)

        Gtk.Window.set_default_icon_name('gpodder')

        # FIXME: we want to get rid of dbus dependency
        try:
            dbus_main_loop = DBusGMainLoop(set_as_default=True)
            gpodder.dbus_session_bus = dbus.SessionBus(dbus_main_loop)

        except dbus.exceptions.DBusException as dbe:
            logger.warning('Cannot get "on the bus".', exc_info=True)
            dlg = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                   Gtk.ButtonsType.CLOSE, _('Cannot start gPodder'))
            dlg.format_secondary_markup(_('D-Bus error: %s') % (str(dbe),))
            dlg.set_title('gPodder')
            dlg.run()
            dlg.destroy()
            sys.exit(0)

        # Using GDBus
        try:
            self.loop = GLib.MainLoop()
            self.owner_id = Gio.bus_own_name(
                # Specify connection to the session bus:
                Gio.BusType.SESSION,
                # Set the well-known name:
                gpodder.dbus_bus_name,
                # Provide any flags
                # (for example, to allow replacement):
                Gio.BusNameOwnerFlags.DO_NOT_QUEUE,
                # Provide handler 1 (bus_acquired):
                self.on_bus_acquired,
                # Provide handler 2 (name_acquired):
                None,
                # Provide handler 3 (name_lost):
                None,
            )
        except Exception as e:
            logger.warning("Name Already clamed: %r", e, exc_info=True)
        util.idle_add(self.check_root_folder_path_gui)

    def do_activate(self):
        # We only allow a single window and raise any existing ones
        if not self.window:
            # Windows are associated with the application
            # when the last one is closed the application shuts down
            self.window = gPodder(self, core.Core(UIConfig, model_class=Model), self.options)

            if gpodder.ui.osx:
                from . import macosx

                # Handle "subscribe to podcast" events from firefox
                macosx.register_handlers(self.window)

            # Set dark mode from color_scheme config key, or from Settings portal
            # if it exists and color_scheme is 'system'.
            if getattr(gpodder.dbus_session_bus, 'fake', False):
                self.have_settings_portal = False
                self._set_default_color_scheme('light')
                self.set_dark_mode(self.window.config.ui.gtk.color_scheme == 'dark')
            else:
                self.read_portal_color_scheme()
                gpodder.dbus_session_bus.add_signal_receiver(
                    self.on_portal_setting_changed, "SettingChanged", None,
                    "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop")

        self.window.gPodder.present()

    def _set_default_color_scheme(self, default):
        """Set the default value for color_scheme based on GTK settings.

        If gtk_application_prefer_dark_theme is set to 1 (a non-default value),
        the user has set it in GTK settings.ini and we set color_scheme to match
        this preference. Otherwise we set the key to the given default, which
        should be 'system' in case Settings portal is found, or 'light' if it's not.
        """
        if self.window.config.ui.gtk.color_scheme is None:
            settings = Gtk.Settings.get_default()
            self.window.config.ui.gtk.color_scheme = (
                'dark' if settings.props.gtk_application_prefer_dark_theme == 1
                else default)

    def set_dark_mode(self, dark):
        settings = Gtk.Settings.get_default()
        settings.props.gtk_application_prefer_dark_theme = 1 if dark else 0

    def read_portal_color_scheme(self):
        gpodder.dbus_session_bus.call_async(
            "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop",
            "org.freedesktop.portal.Settings", "ReadOne", "ss",
            ("org.freedesktop.appearance", "color-scheme"),
            self.on_portal_settings_read, self.on_portal_settings_read_error)

    def on_portal_settings_read(self, value):
        self.have_settings_portal = True
        self._set_default_color_scheme('system')
        if self.window.config.ui.gtk.color_scheme == 'system':
            self.set_dark_mode(value == 1)
        else:
            self.set_dark_mode(self.window.config.ui.gtk.color_scheme == 'dark')

    def on_portal_settings_read_error(self, value):
        self.have_settings_portal = False
        self._set_default_color_scheme('light')
        self.set_dark_mode(self.window.config.ui.gtk.color_scheme == 'dark')

    def on_portal_setting_changed(self, namespace, key, value):
        if (namespace == 'org.freedesktop.appearance'
                and key == 'color-scheme'):
            dark = (value == 1)
            if self.window.config.ui.gtk.color_scheme == 'system':
                logger.debug(
                    f"'color-scheme' changed to {value}, setting dark mode to {dark}")
                self.set_dark_mode(dark)

    def on_notify_is_registered(self, params, _data):
        if self.get_is_registered() and self.get_is_remote():
            logger.info('Activating existing instance via D-Bus.')
            if self.options.subscribe:
                logger.info("Subscribing to %s" % self.options.subscribe)
                self.activate_action('subscribe_to_url', GLib.Variant('s', self.options.subscribe))
                Gio.bus_get_sync(Gio.BusType.SESSION, None).flush_sync(None)

    def on_menu(self, action, param):
        self.menu_popover.popup()

    def on_about(self, action, param):
        dlg = Gtk.Dialog(_('About gPodder'), self.window.gPodder,
                Gtk.DialogFlags.MODAL)
        dlg.add_button(_('_Close'), Gtk.ResponseType.OK).show()
        dlg.set_resizable(True)

        bg = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin=16)
        pb = GdkPixbuf.Pixbuf.new_from_file_at_size(gpodder.icon_file, 160, 160)
        bg.pack_start(Gtk.Image.new_from_pixbuf(pb), False, False, 0)
        label = Gtk.Label(justify=Gtk.Justification.CENTER)
        label.set_selectable(True)
        label.set_markup('\n'.join(x.strip() for x in """
        <b>gPodder {version} ({date})</b>

        {copyright}

        {license}

        <a href="{url}">{tr_website}</a> · <a href="{bugs_url}">{tr_bugtracker}</a>
        """.format(version=gpodder.__version__,
                   date=gpodder.__date__,
                   copyright=gpodder.__copyright__,
                   license=gpodder.__license__,
                   bugs_url='https://github.com/gpodder/gpodder/issues',
                   url=html.escape(gpodder.__url__),
                   tr_website=_('Website'),
                   tr_bugtracker=_('Bug Tracker')).strip().split('\n')))
        label.connect('activate-link', lambda label, url: util.open_website(url))

        bg.pack_start(label, False, False, 0)
        bg.pack_start(Gtk.Label(), False, False, 0)

        dlg.vbox.pack_start(bg, False, False, 0)
        dlg.connect('response', lambda dlg, response: dlg.destroy())

        dlg.vbox.show_all()

        dlg.run()

    def on_quit(self, *args):
        self.window.on_gPodder_delete_event()

    def on_window_removed(self, *args):
        if self.owner_id:
            Gio.bus_unown_name(self.owner_id)
            self.owner_id = None
        self.quit()

    def on_help_activate(self, action, param):
        util.open_website('https://gpodder.github.io/docs/')

    def on_logs_activate(self, action, param):
        util.gui_open(os.path.join(gpodder.home, 'Logs'), gui=self.window)

    def on_itemPreferences_activate(self, action, param=None):
        gPodderPreferences(self.window.gPodder,
                _config=self.window.config,
                user_apps_reader=self.window.user_apps_reader,
                parent_window=self.window.main_window,
                mygpo_client=self.window.mygpo_client,
                on_send_full_subscriptions=self.window.on_send_full_subscriptions,
                on_itemExportChannels_activate=self.window.on_itemExportChannels_activate,
                on_extension_enabled=self.on_extension_enabled,
                on_extension_disabled=self.on_extension_disabled,
                have_settings_portal=self.have_settings_portal)

    def on_goto_mygpo(self, action, param):
        self.window.mygpo_client.open_website()

    def on_check_for_updates_activate(self, action, param):
        if os.path.exists(gpodder.no_update_check_file):
            self.window.check_for_distro_updates()
        else:
            self.window.check_for_updates(silent=False)

    def on_subscribe_to_url_activate(self, action, param):
        self.window.subscribe_to_url(param.get_string())

    def on_extension_enabled(self, extension):
        self.window.on_extension_enabled(extension)

    def on_extension_disabled(self, extension):
        self.window.on_extension_disabled(extension)

    def on_bus_acquired(self, conn, name):
        self.gdbus_connection = conn
        if self.window:
            self.window.on_bus_acquired(conn)

    @staticmethod
    def check_root_folder_path_gui():
        msg = check_root_folder_path()
        if msg:
            dlg = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.WARNING,
                Gtk.ButtonsType.CLOSE, msg)
            dlg.set_title(_('Path to gPodder home is too long'))
            dlg.run()
            dlg.destroy()


def main(options=None):
    GLib.set_application_name('gPodder')

    gp = gPodderApplication(options)
    gp.run()
    sys.exit(0)
