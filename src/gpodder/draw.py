# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (C) 2005-2007 Thomas Perl <thp at perli.net>
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

def draw_rounded_rectangle(ctx, x, y, w, h, r=10, left_side_width = None, sides_to_draw=0):
    if left_side_width is None:
        left_side_width = w/2

    if sides_to_draw & RRECT_LEFT_SIDE:
        ctx.move_to(x+left_side_width, y+h)
        ctx.line_to(x+r, y+h)
        ctx.curve_to(x, y+h, x, y+h, x, y+h-r)
        ctx.line_to(x, y+r)
        ctx.curve_to(x, y, x, y, x+r, y)
        ctx.line_to(x+left_side_width, y)

    if sides_to_draw & RRECT_RIGHT_SIDE:
        ctx.move_to(x+left_side_width, y)
        ctx.line_to(x+w-r, y)
        ctx.curve_to(x+w, y, x+w, y, x+w, y+r)
        ctx.line_to(x+w, y+h-r)
        ctx.curve_to(x+w, y+h, x+w, y+h, x+w-r, y+h)
        ctx.line_to(x+left_side_width, y+h)


def set_gtk_color(ctx, col, opacity=1.0, invert=False):
    # Convert color values 0..65535 -> 0.0..1.0
    (r, g, b) = map(lambda c: c/65535.0, (col.red, col.green, col.blue))
    if invert == True:
        (r, g, b) = (1.0-r, 1.0-g, 1.0-b)
    ctx.set_source_rgba( r, g, b, opacity)


def draw_text_pill(left_text, right_text, x=0, y=0, border=3, radius=11):
    # Create temporary context to calculate the text size
    ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))

    # Use GTK+ style of a normal Button
    widget = gtk.ProgressBar()
    style = widget.rc_get_style()

    bg_color = style.bg[gtk.STATE_SELECTED]
    text_color = style.text[gtk.STATE_SELECTED]

    font_desc = style.font_desc
    font_size = float(font_desc.get_size())/float(pango.SCALE)
    font_name = font_desc.get_family()

    ctx.set_font_size(font_size)
    ctx.select_font_face(font_name, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)

    left_text_e = TextExtents(ctx, left_text)
    right_text_e = TextExtents(ctx, right_text)
    text_height = max(left_text_e.height, right_text_e.height)
    
    image_height = int(y+text_height+border*2)
    image_width = int(x+left_text_e.width+right_text_e.width+border*4)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, image_width, image_height)

    ctx = cairo.Context(surface)
    ctx.set_font_size(font_size)
    ctx.select_font_face(font_name, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)

    if left_text == '0':
        left_text = None
    if right_text == '0':
        right_text = None

    left_side_width = left_text_e.width + border*2
    right_side_width = right_text_e.width + border*2

    rect_width = left_side_width + right_side_width
    rect_height = text_height + border*2
    if left_text is not None:
        draw_rounded_rectangle(ctx,x,y,rect_width,rect_height,radius, left_side_width, RRECT_LEFT_SIDE)
        set_gtk_color(ctx, bg_color, 0.5)
        ctx.fill()

        ctx.move_to(x+1+border-left_text_e.x_bearing, y+1+border+text_height)
        set_gtk_color(ctx, text_color, invert=True)
        ctx.show_text(left_text)
        ctx.move_to(x+border-left_text_e.x_bearing, y+border+text_height)
        set_gtk_color(ctx, text_color)
        ctx.show_text(left_text)

    if right_text is not None:
        draw_rounded_rectangle(ctx, x, y, rect_width, rect_height, radius, left_side_width, RRECT_RIGHT_SIDE)
        set_gtk_color(ctx, bg_color)
        ctx.fill()

        ctx.move_to(x+1+border*3+left_text_e.width-right_text_e.x_bearing, y+1+border+text_height)
        set_gtk_color(ctx, text_color, invert=True)
        ctx.show_text(right_text)
        ctx.move_to(x+border*3+left_text_e.width-right_text_e.x_bearing, y+border+text_height)
        set_gtk_color(ctx, text_color)
        ctx.show_text(right_text)

    return surface


def draw_pill_pixbuf(left_text, right_text):
    s = draw_text_pill(left_text, right_text)
    sio = StringIO.StringIO()
    s.write_to_png(sio)

    pbl = gtk.gdk.PixbufLoader()
    pbl.write(sio.getvalue())
    pbl.close()

    pixbuf = pbl.get_pixbuf()
    return pixbuf

