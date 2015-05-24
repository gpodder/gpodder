# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2015 Thomas Perl and the gPodder Team
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


def set_flattr_button(flattr, payment_url, widget_image, widget_button):
    if not flattr.api_reachable() or not payment_url:
        widget_image.hide()
        widget_button.hide()
        return False
    elif not flattr.has_token():
        badge = IMAGE_FLATTR_GREY
        button_text = _('Sign in')
        return False

    flattrs, flattred = flattr.get_thing_info(payment_url)
    can_flattr_this = False

    if flattred:
        badge = IMAGE_FLATTRED
        button_text = _('Flattred')
    else:
        badge = IMAGE_FLATTR
        button_text = _('Flattr this')
        can_flattr_this = True

    widget_button.set_label(button_text)
    widget_button.set_sensitive(can_flattr_this)
    widget_button.show()

    draw.draw_flattr_button(widget_image, badge, flattrs)
    widget_image.show()

    return can_flattr_this

