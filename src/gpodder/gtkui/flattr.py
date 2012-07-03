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


def set_flattr_button(cls, url, token, widget_image, widget_button):    
    if not url:
        widget_image.hide()
        widget_button.hide()
        return False
        
    flattr_possible = False
    flattrs, flattred = cls.get_thing_info(url)

    if flattred is None or not token:
        badge = IMAGE_FLATTR_GREY
        button_text = _('Sign in')
        tooltip_text = _('Please sign in')
    elif flattred:
        badge = IMAGE_FLATTRED
        button_text = _('Flattred')
        tooltip_text = _('Already flattred')
    else:
        badge = IMAGE_FLATTR
        button_text = _('Flattr this')           
        flattr_possible = True
        tooltip_text = _('Flattr this')

    widget_button.set_label(button_text)
    widget_button.set_sensitive(flattr_possible)
    widget_button.show()
    
    draw.draw_flattr_button(widget_image, badge, flattrs)
    tooltips = gtk.Tooltips()
    tooltips.set_tip(widget_image, tooltip_text, tip_private=None)
    widget_image.show()

    return flattr_possible

