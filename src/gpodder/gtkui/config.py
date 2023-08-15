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


#
#  gpodder.gtkui.config -- Config object with GTK+ support (2009-08-24)
#

import logging

import gi  # isort:skip
gi.require_version('Gdk', '3.0')  # isort:skip
gi.require_version('Gtk', '3.0')  # isort:skip
from gi.repository import Gdk, Gtk, Pango

import gpodder
from gpodder import config, util

logger = logging.getLogger(__name__)

_ = gpodder.gettext


class ConfigModel(Gtk.ListStore):
    C_NAME, C_TYPE_TEXT, C_VALUE_TEXT, C_TYPE, C_EDITABLE, C_FONT_STYLE, \
            C_IS_BOOLEAN, C_BOOLEAN_VALUE = list(range(8))

    def __init__(self, config):
        Gtk.ListStore.__init__(self, str, str, str, object, bool, int, bool, bool)

        self._config = config
        self._fill_model()

        self._config.add_observer(self._on_update)

    def _type_as_string(self, type):
        if type == int:
            return _('Integer')
        elif type == float:
            return _('Float')
        elif type == bool:
            return _('Boolean')
        else:
            return _('String')

    def _fill_model(self):
        self.clear()
        for key in sorted(self._config.all_keys()):
            # Ignore Gtk window state data (position, size, ...)
            if key.startswith('ui.gtk.state.'):
                continue

            value = self._config._lookup(key)
            fieldtype = type(value)

            style = Pango.Style.NORMAL
            # if value == default:
            #     style = Pango.Style.NORMAL
            # else:
            #     style = Pango.Style.ITALIC

            self.append((key, self._type_as_string(fieldtype),
                    config.config_value_to_string(value),
                    fieldtype, fieldtype is not bool, style,
                    fieldtype is bool, bool(value)))

    def _on_update(self, name, old_value, new_value):
        for row in self:
            if row[self.C_NAME] == name:
                style = Pango.Style.NORMAL
                # if new_value == self._config.Settings[name]:
                #     style = Pango.Style.NORMAL
                # else:
                #     style = Pango.Style.ITALIC
                new_value_text = config.config_value_to_string(new_value)
                self.set(row.iter,
                        self.C_VALUE_TEXT, new_value_text,
                        self.C_BOOLEAN_VALUE, bool(new_value),
                        self.C_FONT_STYLE, style)
                break

    def stop_observing(self):
        self._config.remove_observer(self._on_update)


class UIConfig(config.Config):
    def __init__(self, filename='gpodder.conf'):
        config.Config.__init__(self, filename)
        self.__ignore_window_events = False

    def connect_gtk_editable(self, name, editable):
        editable.delete_text(0, -1)
        editable.insert_text(str(getattr(self, name)))

        def _editable_changed(editable):
            setattr(self, name, editable.get_chars(0, -1))
        editable.connect('changed', _editable_changed)

    def connect_gtk_spinbutton(self, name, spinbutton, forced_upper=None):
        """
        bind a Gtk.SpinButton to a configuration entry.

        It's now possible to specify an upper value (forced_upper).
        It's not done automatically (always look for name + '_max') because it's
        used only once. If it becomes commonplace, better make it automatic.

        :param str name: configuration key (e.g. 'limit.downloads.concurrent')
        :param Gtk.SpinButton spinbutton: button to bind to config
        :param float forced_upper: forced upper limit on spinbutton.
                                   Overrides value in .ui to be consistent with code
        """
        current_value = getattr(self, name)

        adjustment = spinbutton.get_adjustment()
        if forced_upper is not None:
            adjustment.set_upper(forced_upper)
        if current_value > adjustment.get_upper():
            adjustment.set_upper(current_value)

        spinbutton.set_value(current_value)

        def _spinbutton_changed(spinbutton):
            setattr(self, name, spinbutton.get_value())
        spinbutton.connect('value-changed', _spinbutton_changed)

    def connect_gtk_paned(self, name, paned):
        paned.set_position(getattr(self, name))
        paned_child = paned.get_child1()

        def _child_size_allocate(x, y):
            setattr(self, name, paned.get_position())
        paned_child.connect('size-allocate', _child_size_allocate)

    def connect_gtk_togglebutton(self, name, togglebutton):
        togglebutton.set_active(getattr(self, name))

        def _togglebutton_toggled(togglebutton):
            setattr(self, name, togglebutton.get_active())
        togglebutton.connect('toggled', _togglebutton_toggled)

    def connect_gtk_window(self, window, config_prefix, show_window=False):
        cfg = getattr(self.ui.gtk.state, config_prefix)

        if gpodder.ui.win32:
            window.set_gravity(Gdk.Gravity.STATIC)

        if -1 not in (cfg.x, cfg.y, cfg.width, cfg.height):
            # get screen resolution
            screen = Gdk.Screen.get_default()
            screen_width = 0
            screen_height = 0
            for i in range(0, screen.get_n_monitors()):
                monitor = screen.get_monitor_geometry(i)
                screen_width += monitor.width
                screen_height += monitor.height
            logger.debug('Screen %d x %d' % (screen_width, screen_height))
            # reset window position if more than 50% is off-screen
            half_width = cfg.width / 2
            half_height = cfg.height / 2
            if (cfg.x + cfg.width - half_width) < 0 or (cfg.y + cfg.height - half_height) < 0 \
                    or cfg.x > (screen_width - half_width) or cfg.y > (screen_height - half_height):
                logger.warning('"%s" window was off-screen at (%d, %d), resetting to default position' % (config_prefix, cfg.x, cfg.y))
                cfg.x = -1
                cfg.y = -1

        if cfg.width != -1 and cfg.height != -1:
            window.resize(cfg.width, cfg.height)

        # Not all platforms can natively restore position, gPodder must handle it.
        # https://github.com/gpodder/gpodder/pull/933#issuecomment-818039693
        if cfg.x == -1 or cfg.y == -1:
            window.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        else:
            window.move(cfg.x, cfg.y)
            # From Gtk docs: most window managers ignore requests for initial window
            # positions (instead using a user-defined placement algorithm) and honor
            # requests after the window has already been shown.
            # Move it a second time after the window has been shown.
            # The first move reduces chance of window jumping,
            # and gives the window manager a position to unmaximize to.
            if not cfg.maximized:
                util.idle_add(window.move, cfg.x, cfg.y)

        # Ignore events while we're connecting to the window
        self.__ignore_window_events = True

        # Get window state, correct size comes from window.get_size(),
        # see https://developer.gnome.org/SaveWindowState/
        def _receive_configure_event(widget, event):
            if not self.__ignore_window_events:
                # TODO: The maximize event might arrive after the configure event.
                # This causes the maximized size to be saved, and restoring the
                # window will not save its smaller size. Delaying the save with
                # idle_add() is not enough time for the state event to arrive.
                if not bool(event.window.get_state() & Gdk.WindowState.MAXIMIZED):
                    x_pos, y_pos = widget.get_position()
                    width_size, height_size = widget.get_size()
                    cfg.x = x_pos
                    cfg.y = y_pos
                    cfg.width = width_size
                    cfg.height = height_size

        window.connect('configure-event', _receive_configure_event)

        def _receive_window_state(widget, event):
            new_value = bool(event.new_window_state & Gdk.WindowState.MAXIMIZED)
            cfg.maximized = new_value

        window.connect('window-state-event', _receive_window_state)

        # After the window has been set up, we enable events again
        def _enable_window_events():
            self.__ignore_window_events = False
        util.idle_add(_enable_window_events)

        if show_window:
            window.show()
        if cfg.maximized:
            window.maximize()
