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


#
#  draw.py -- Draw routines for gPodder-specific graphics
#  Thomas Perl <thp@perli.net>, 2007-11-25
#

import gpodder

import gtk
import pango
import pangocairo
import cairo
import StringIO
import math


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
    style = widget.rc_get_style()
    text_color = style.text[gtk.STATE_PRELIGHT]
    red, green, blue = text_color.red, text_color.green, text_color.blue
    text_color = [float(x)/65535. for x in (red, green, blue)]
    text_color.append(.5)

    if font_desc is None:
        font_desc = style.font_desc
        font_desc.set_size(14*pango.SCALE)

    pango_context = widget.create_pango_context()
    layout = pango.Layout(pango_context)
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
    # Download percentage bar icon - it turns out the cake is a lie (d'oh!)
    # ..but the inital idea was to have a cake-style indicator, but that
    # didn't work as well as the progress bar, but the name stuck..

    if size is None:
        size = EPISODE_LIST_ICON_SIZE

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = pangocairo.CairoContext(cairo.Context(surface))

    widget = gtk.ProgressBar()
    style = widget.rc_get_style()
    bgc = style.bg[gtk.STATE_NORMAL]
    fgc = style.bg[gtk.STATE_SELECTED]
    txc = style.text[gtk.STATE_NORMAL]

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

def draw_text_pill(left_text, right_text, x=0, y=0, border=2, radius=14, font_desc=None):
    # Create temporary context to calculate the text size
    ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))

    # Use GTK+ style of a normal Button
    widget = gtk.Label()
    style = widget.rc_get_style()

    # Padding (in px) at the right edge of the image (for Ubuntu; bug 1533)
    padding_right = 7

    x_border = border*2

    if font_desc is None:
        font_desc = style.font_desc
        font_desc.set_weight(pango.WEIGHT_BOLD)

    pango_context = widget.create_pango_context()
    layout_left = pango.Layout(pango_context)
    layout_left.set_font_description(font_desc)
    layout_left.set_text(left_text)
    layout_right = pango.Layout(pango_context)
    layout_right.set_font_description(font_desc)
    layout_right.set_text(right_text)

    width_left, height_left = layout_left.get_pixel_size()
    width_right, height_right = layout_right.get_pixel_size()

    text_height = max(height_left, height_right)

    image_height = int(y+text_height+border*2)
    image_width = int(x+width_left+width_right+x_border*4+padding_right)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, image_width, image_height)

    ctx = pangocairo.CairoContext(cairo.Context(surface))

    # Clip so as to not draw on the right padding (for Ubuntu; bug 1533)
    ctx.rectangle(0, 0, image_width - padding_right, image_height)
    ctx.clip()

    if left_text == '0':
        left_text = None
    if right_text == '0':
        right_text = None

    left_side_width = width_left + x_border*2
    right_side_width = width_right + x_border*2

    rect_width = left_side_width + right_side_width
    rect_height = text_height + border*2
    if left_text is not None:
        draw_rounded_rectangle(ctx,x,y,rect_width,rect_height,radius, left_side_width, RRECT_LEFT_SIDE, right_text is None)
        linear = cairo.LinearGradient(x, y, x+left_side_width/2, y+rect_height/2)
        linear.add_color_stop_rgba(0, .8, .8, .8, .5)
        linear.add_color_stop_rgba(.4, .8, .8, .8, .7)
        linear.add_color_stop_rgba(.6, .8, .8, .8, .6)
        linear.add_color_stop_rgba(.9, .8, .8, .8, .8)
        linear.add_color_stop_rgba(1, .8, .8, .8, .9)
        ctx.set_source(linear)
        ctx.fill()
        xpos, ypos, width_left, height = x+1, y+1, left_side_width, rect_height-2
        if right_text is None:
            width_left -= 2
        draw_rounded_rectangle(ctx, xpos, ypos, rect_width, height, radius, width_left, RRECT_LEFT_SIDE, right_text is None)
        ctx.set_source_rgba(1., 1., 1., .3)
        ctx.set_line_width(1)
        ctx.stroke()
        draw_rounded_rectangle(ctx,x,y,rect_width,rect_height,radius, left_side_width, RRECT_LEFT_SIDE, right_text is None)
        ctx.set_source_rgba(.2, .2, .2, .6)
        ctx.set_line_width(1)
        ctx.stroke()

        ctx.move_to(x+x_border, y+1+border)
        ctx.set_source_rgba( 0, 0, 0, 1)
        ctx.show_layout(layout_left)
        ctx.move_to(x-1+x_border, y+border)
        ctx.set_source_rgba( 1, 1, 1, 1)
        ctx.show_layout(layout_left)

    if right_text is not None:
        draw_rounded_rectangle(ctx, x, y, rect_width, rect_height, radius, left_side_width, RRECT_RIGHT_SIDE, left_text is None)
        linear = cairo.LinearGradient(x+left_side_width, y, x+left_side_width+right_side_width/2, y+rect_height)
        linear.add_color_stop_rgba(0, .2, .2, .2, .9)
        linear.add_color_stop_rgba(.4, .2, .2, .2, .8)
        linear.add_color_stop_rgba(.6, .2, .2, .2, .6)
        linear.add_color_stop_rgba(.9, .2, .2, .2, .7)
        linear.add_color_stop_rgba(1, .2, .2, .2, .5)
        ctx.set_source(linear)
        ctx.fill()
        xpos, ypos, width, height = x, y+1, rect_width-1, rect_height-2
        if left_text is None:
            xpos, width = x+1, rect_width-2
        draw_rounded_rectangle(ctx, xpos, ypos, width, height, radius, left_side_width, RRECT_RIGHT_SIDE, left_text is None)
        ctx.set_source_rgba(1., 1., 1., .3)
        ctx.set_line_width(1)
        ctx.stroke()
        draw_rounded_rectangle(ctx, x, y, rect_width, rect_height, radius, left_side_width, RRECT_RIGHT_SIDE, left_text is None)
        ctx.set_source_rgba(.1, .1, .1, .6)
        ctx.set_line_width(1)
        ctx.stroke()

        ctx.move_to(x+left_side_width+x_border, y+1+border)
        ctx.set_source_rgba( 0, 0, 0, 1)
        ctx.show_layout(layout_right)
        ctx.move_to(x-1+left_side_width+x_border, y+border)
        ctx.set_source_rgba( 1, 1, 1, 1)
        ctx.show_layout(layout_right)

    return surface


def draw_cake_pixbuf(percentage, text=None, emblem=None):
    return cairo_surface_to_pixbuf(draw_cake(percentage, text, emblem))

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


def draw_flattr_button(widget, flattr_image, flattrs_count):
    """
    Adds the flattrs count to the flattr button
    """
    if isinstance(flattrs_count, int):
        flattrs_count = str(flattrs_count)

    pixbuf = gtk.gdk.pixbuf_new_from_file(flattr_image)
    iwidth, iheight = pixbuf.get_width(), pixbuf.get_height()
    pixmap, mask = pixbuf.render_pixmap_and_mask()

    # get default-font
    style = widget.rc_get_style()
    font_desc = style.font_desc
    #font_desc.set_size(12*pango.SCALE)
    font_desc.set_size(9*pango.SCALE)

    # set font and text
    layout = widget.create_pango_layout(flattrs_count)
    layout.set_font_description(font_desc)
    fwidth, fheight = layout.get_pixel_size()

    x = 95 - abs(fwidth / 2) # 95 is the center of the bubble
    y = abs(iheight / 2) - abs(fheight / 2)

    cm = pixmap.get_colormap()
    red = cm.alloc_color('black')
    gc = pixmap.new_gc(foreground=red)
    pixmap.draw_layout(gc, x, y, layout)
    widget.set_from_pixmap(pixmap, mask)


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

