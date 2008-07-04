# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2008 Thomas Perl and the gPodder Team
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


import gtk
import pango
import cairo
import StringIO


class TextExtents(object):
    def __init__(self, ctx, text):
        tuple = ctx.text_extents(text)
        (self.x_bearing, self.y_bearing, self.width, self.height, self.x_advance, self.y_advance) = tuple


RRECT_LEFT_SIDE = 1
RRECT_RIGHT_SIDE = 2

def draw_rounded_rectangle(ctx, x, y, w, h, r=10, left_side_width = None, sides_to_draw=0, close=False):
    if left_side_width is None:
        left_side_width = flw/2
    
    x = int(x)
    offset = .5 if close else 0

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


def draw_text_pill(left_text, right_text, x=0, y=0, border=4, radius=14):
    # Create temporary context to calculate the text size
    ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))

    # Use GTK+ style of a normal Button
    widget = gtk.ProgressBar()
    style = widget.rc_get_style()

    x_border = int(border*1.2)

    font_desc = style.font_desc
    font_size = float(1.15*font_desc.get_size())/float(pango.SCALE)
    font_name = font_desc.get_family()

    ctx.set_font_size(font_size)
    ctx.select_font_face(font_name, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)

    left_text_e = TextExtents(ctx, left_text)
    right_text_e = TextExtents(ctx, right_text)
    text_height = max(left_text_e.height, right_text_e.height)

    image_height = int(y+text_height+border*2)
    image_width = int(x+left_text_e.width+right_text_e.width+x_border*4)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, image_width, image_height)

    ctx = cairo.Context(surface)
    ctx.set_font_size(font_size)
    ctx.select_font_face(font_name, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)

    if left_text == '0':
        left_text = None
    if right_text == '0':
        right_text = None

    left_side_width = left_text_e.width + x_border*2
    right_side_width = right_text_e.width + x_border*2

    rect_width = left_side_width + right_side_width
    rect_height = text_height + border*2
    if left_text is not None:
        draw_rounded_rectangle(ctx,x,y,rect_width,rect_height,radius, left_side_width, RRECT_LEFT_SIDE, right_text is None)
        linear = cairo.LinearGradient(x, y, x+left_side_width/2, y+rect_height/2)
        linear.add_color_stop_rgba(0, .7, .7, .7, .5)
        linear.add_color_stop_rgba(1, .4, .4, .4, .5)
        ctx.set_source(linear)
        ctx.fill_preserve()
        ctx.set_source_rgba(0, 0, 0, .4)
        ctx.set_line_width(1)
        ctx.stroke()

        ctx.move_to(x+1+x_border-left_text_e.x_bearing, y+1+border+text_height)
        ctx.set_source_rgba( 0, 0, 0, 1)
        ctx.show_text(left_text)
        ctx.move_to(x+x_border-left_text_e.x_bearing, y+border+text_height)
        ctx.set_source_rgba( 1, 1, 1, 1)
        ctx.show_text(left_text)

    if right_text is not None:
        draw_rounded_rectangle(ctx, x, y, rect_width, rect_height, radius, left_side_width, RRECT_RIGHT_SIDE, left_text is None)
        linear = cairo.LinearGradient(x+left_side_width, y, x+left_side_width+right_side_width/2, y+rect_height)
        linear.add_color_stop_rgba(0, 0, 0, 0, .9)
        linear.add_color_stop_rgba(1, 0, 0, 0, .5)
        ctx.set_source(linear)
        ctx.fill_preserve()
        ctx.set_source_rgba(0, 0, 0, .7)
        ctx.set_line_width(1)
        ctx.stroke()

        ctx.move_to(x+1+x_border*3+left_text_e.width-right_text_e.x_bearing, y+1+border+text_height)
        ctx.set_source_rgba( 0, 0, 0, 1)
        ctx.show_text(right_text)
        ctx.move_to(x+x_border*3+left_text_e.width-right_text_e.x_bearing, y+border+text_height)
        ctx.set_source_rgba( 1, 1, 1, 1)
        ctx.show_text(right_text)

    return surface


def draw_pill_pixbuf(left_text, right_text):
    return cairo_surface_to_pixbuf(draw_text_pill(left_text, right_text))


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

    pbl = gtk.gdk.PixbufLoader()
    pbl.write(sio.getvalue())
    pbl.close()

    pixbuf = pbl.get_pixbuf()
    return pixbuf


def progressbar_pixbuf(width, height, percentage):
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

