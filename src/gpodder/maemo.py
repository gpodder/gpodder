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

import hildon


class Button(object):
    def __init__(self, title, value=None,
            arrangement=hildon.BUTTON_ARRANGEMENT_HORIZONTAL):
        self.title = title
        self.value = value
        self.arrangement = arrangement

    def create(self, name, gtkbuilderwidget):
        widget = hildon.Button(0, self.arrangement)
        if self.title:
            widget.set_title(self.title)
        if self.value:
            widget.set_value(self.value)
        signal_name = 'on_%s_clicked' % name

        if not hasattr(gtkbuilderwidget, signal_name):
            raise Exception('no method %s on %s' %
                    (gtkbuilderwidget, signal_name))

        if hasattr(gtkbuilderwidget, name):
            raise Exception('%s already has an attribute %s' %
                    (gtkbuilderwidget, name))

        handler = getattr(gtkbuilderwidget, signal_name)
        widget.connect('clicked', handler)
        setattr(gtkbuilderwidget, name, widget)

        return widget


def create_app_menu(gtkbuilderwidget):
    if not hasattr(gtkbuilderwidget, '_app_menu'):
        raise Exception('%s is missing the _app_menu attribute')

    app_menu = hildon.AppMenu()
    for name, widget in gtkbuilderwidget._app_menu:
        app_menu.append(widget.create(name, gtkbuilderwidget))
    gtkbuilderwidget.main_window.set_app_menu(app_menu)

