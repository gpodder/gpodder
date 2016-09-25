# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2016 Thomas Perl and the gPodder Team
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
#  draw.py -- Draw routines for gPodder-specific graphics
#  Thomas Perl <thp@perli.net>, 2007-11-25
#

import gpodder

from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GLib

import StringIO
import math
import re


class TextExtents(object):
    def __init__(self, ctx, text):
        tuple = ctx.text_extents(text)
        (self.x_bearing, self.y_bearing, self.width, self.height, self.x_advance, self.y_advance) = tuple

EPISODE_LIST_ICON_SIZE = 16

RRECT_LEFT_SIDE = 1
RRECT_RIGHT_SIDE = 2

def draw_rounded_rectangle(ctx, x, y, w, h, r=10, left_side_width = None, sides_to_draw=0, close=False):
    assert left_side_width is not None

    x = int(x)
    offset = 0
    if close: offset = 0.5

    if sides_to_draw & RRECT_LEFT_SIDE:
        ctx.move_to(x+int(left_side_width)-offset, y+h)
        ctx.line_to(x+r, y+h)
        ctx.curve_to(x, y+h, x, y+h, x, y+h-r)
        ctx.line_to(x, y+r)
        ctx.curve_to(x, y, x, y, x+r, y)
        ctx.line_to(x+int(left_side_width)-offset, y)
        if close:
            ctx.line_to(x+int(left_side_width)-offset, y+h)

    if sides_to_draw & RRECT_RIGHT_SIDE:
        ctx.move_to(x+int(left_side_width)+offset, y)
        ctx.line_to(x+w-r, y)
        ctx.curve_to(x+w, y, x+w, y, x+w, y+r)
        ctx.line_to(x+w, y+h-r)
        ctx.curve_to(x+w, y+h, x+w, y+h, x+w-r, y+h)
        ctx.line_to(x+int(left_side_width)+offset, y+h)
        if close:
            ctx.line_to(x+int(left_side_width)+offset, y)


def rounded_rectangle(ctx, x, y, width, height, radius=4.):
    """Simple rounded rectangle algorithmn

    http://www.cairographics.org/samples/rounded_rectangle/
    """
    degrees = math.pi / 180.
    ctx.new_sub_path()
    if width > radius:
        ctx.arc(x + width - radius, y + radius, radius, -90. * degrees, 0)
        ctx.arc(x + width - radius, y + height - radius, radius, 0, 90. * degrees)
        ctx.arc(x + radius, y + height - radius, radius, 90. * degrees, 180. * degrees)
        ctx.arc(x + radius, y + radius, radius, 180. * degrees, 270. * degrees)
    ctx.close_path()


def draw_text_box_centered(ctx, widget, w_width, w_height, text, font_desc=None, add_progress=None):
    return
    style = widget.rc_get_style()
    text_color = style.text[Gtk.StateType.PRELIGHT]
    red, green, blue = text_color.red, text_color.green, text_color.blue
    text_color = [float(x)/65535. for x in (red, green, blue)]
    text_color.append(.5)

    if font_desc is None:
        font_desc = style.font_desc
        font_desc.set_size(14*Pango.SCALE)

    pango_context = widget.create_pango_context()
    layout = Pango.Layout(pango_context)
    layout.set_font_description(font_desc)
    layout.set_text(text)
    width, height = layout.get_pixel_size()

    ctx.move_to(w_width/2-width/2, w_height/2-height/2)
    ctx.set_source_rgba(*text_color)
    ctx.show_layout(layout)

    # Draw an optional progress bar below the text (same width)
    if add_progress is not None:
        bar_height = 10
        ctx.set_source_rgba(*text_color)
        ctx.set_line_width(1.)
        rounded_rectangle(ctx, w_width/2-width/2-.5, w_height/2+height-.5, width+1, bar_height+1)
        ctx.stroke()
        rounded_rectangle(ctx, w_width/2-width/2, w_height/2+height, int(width*add_progress)+.5, bar_height)
        ctx.fill()

def draw_cake(percentage, text=None, emblem=None, size=None):
    return
    # Download percentage bar icon - it turns out the cake is a lie (d'oh!)
    # ..but the inital idea was to have a cake-style indicator, but that
    # didn't work as well as the progress bar, but the name stuck..

    if size is None:
        size = EPISODE_LIST_ICON_SIZE

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = PangoCairo.CairoContext(cairo.Context(surface))

    widget = Gtk.ProgressBar()
    style = widget.rc_get_style()
    bgc = style.bg[Gtk.StateType.NORMAL]
    fgc = style.bg[Gtk.StateType.SELECTED]
    txc = style.text[Gtk.StateType.NORMAL]

    border = 1.5
    height = int(size*.4)
    width = size - 2*border
    y = (size - height) / 2 + .5
    x = border

    # Background
    ctx.rectangle(x, y, width, height)
    ctx.set_source_rgb(bgc.red_float, bgc.green_float, bgc.blue_float)
    ctx.fill()

    # Filling
    if percentage > 0:
        fill_width = max(1, min(width-2, (width-2)*percentage+.5))
        ctx.rectangle(x+1, y+1, fill_width, height-2)
        ctx.set_source_rgb(fgc.red_float, fgc.green_float, fgc.blue_float)
        ctx.fill()

    # Border
    ctx.rectangle(x, y, width, height)
    ctx.set_source_rgb(txc.red_float, txc.green_float, txc.blue_float)
    ctx.set_line_width(1)
    ctx.stroke()

    del ctx
    return surface


def draw_cake_pixbuf(percentage, text=None, emblem=None):
    return cairo_surface_to_pixbuf(draw_cake(percentage, text, emblem))


def cairo_surface_to_pixbuf(s):
    """
    Converts a Cairo surface to a Gtk Pixbuf by
    encoding it as PNG and using the PixbufLoader.
    """
    sio = StringIO.StringIO()
    try:
        s.write_to_png(sio)
    except:
        # Write an empty PNG file to the StringIO, so
        # in case of an error we have "something" to
        # load. This happens in PyCairo < 1.1.6, see:
        # http://webcvs.cairographics.org/pycairo/NEWS?view=markup
        # Thanks to Chris Arnold for reporting this bug
        sio.write('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAAZiS0dEAP8A\n/wD/oL2nkwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9cMEQkqIyxn3RkAAAAZdEVYdENv\nbW1lbnQAQ3JlYXRlZCB3aXRoIEdJTVBXgQ4XAAAADUlEQVQI12NgYGBgAAAABQABXvMqOgAAAABJ\nRU5ErkJggg==\n'.decode('base64'))

    pbl = GdkPixbuf.PixbufLoader()
    pbl.write(sio.getvalue())
    pbl.close()

    pixbuf = pbl.get_pixbuf()
    return pixbuf


def progressbar_pixbuf(width, height, percentage):
    return
    COLOR_BG = (.4, .4, .4, .4)
    COLOR_FG = (.2, .9, .2, 1.)
    COLOR_FG_HIGH = (1., 1., 1., .5)
    COLOR_BORDER = (0., 0., 0., 1.)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)

    padding = int(float(width)/8.0)
    bar_width = 2*padding
    bar_height = height - 2*padding
    bar_height_fill = bar_height*percentage

    # Background
    ctx.rectangle(padding, padding, bar_width, bar_height)
    ctx.set_source_rgba(*COLOR_BG)
    ctx.fill()

    # Foreground
    ctx.rectangle(padding, padding+bar_height-bar_height_fill, bar_width, bar_height_fill)
    ctx.set_source_rgba(*COLOR_FG)
    ctx.fill()
    ctx.rectangle(padding+bar_width/3, padding+bar_height-bar_height_fill, bar_width/4, bar_height_fill)
    ctx.set_source_rgba(*COLOR_FG_HIGH)
    ctx.fill()

    # Border
    ctx.rectangle(padding-.5, padding-.5, bar_width+1, bar_height+1)
    ctx.set_source_rgba(*COLOR_BORDER)
    ctx.set_line_width(1.)
    ctx.stroke()

    return cairo_surface_to_pixbuf(surface)
