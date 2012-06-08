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
import gtk.gdk
import os.path

import gpodder

_ = gpodder.gettext

from gpodder.gtkui import draw


IMAGE_FLATTR = os.path.join(gpodder.images_folder, 'button-flattr.png')
IMAGE_FLATTR_GREY = os.path.join(gpodder.images_folder, 'button-flattr-grey.png')
IMAGE_FLATTRED = os.path.join(gpodder.images_folder, 'button-flattred.png')
ICON_FLATTR = os.path.join(gpodder.images_folder, 'flattr_icon_color.png')
ICON_FLATTR_GREY = os.path.join(gpodder.images_folder, 'flattr_icon_grey.png')


def set_flattr_button(cls, url, token, widget):
    flattr_possible = False
    if url:
        flattrs, flattred = cls.get_thing_info(url)
    
        if flattred is None or not token:
            flattr_badge = IMAGE_FLATTR_GREY
            tooltip_text = _('Please sign in')
        elif flattred:
            flattr_badge = IMAGE_FLATTRED
            tooltip_text = _('Already flattred')
        else:
            flattr_badge = IMAGE_FLATTR
            flattr_possible = True
            tooltip_text = _('Flattr this')
        
        draw.draw_flattr_button(widget, flattr_badge, flattrs)
        tooltips = gtk.Tooltips()
        tooltips.set_tip(widget, tooltip_text, tip_private=None)
    
    return flattr_possible


def get_flattr_icon(token):
    icon = ICON_FLATTR_GREY
    if token:
        icon = ICON_FLATTR
    
    return gtk.gdk.pixbuf_new_from_file(icon)

