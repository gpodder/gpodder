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
#  draw.py -- Draw routines for gPodder-specific graphics
#  Thomas Perl <thp@perli.net>, 2007-11-25
#

import io
import math

import cairo

import gi  # isort:skip
gi.require_version('Gdk', '3.0')  # isort:skip
gi.require_version('Gtk', '3.0')  # isort:skip
gi.require_version('PangoCairo', '1.0')  # isort:skip
from gi.repository import Gdk, GdkPixbuf, Gtk, Pango, PangoCairo  # isort:skip


class TextExtents(object):
    def __init__(self, ctx, text):
        tuple = ctx.text_extents(text)
        (self.x_bearing, self.y_bearing, self.width, self.height, self.x_advance, self.y_advance) = tuple


EPISODE_LIST_ICON_SIZE = 16

RRECT_LEFT_SIDE = 1
RRECT_RIGHT_SIDE = 2


def draw_rounded_rectangle(ctx, x, y, w, h, r=10, left_side_width=None,
                           sides_to_draw=0, close=False):
    assert left_side_width is not None

    x = int(x)
    offset = 0
    if close: offset = 0.5

    if sides_to_draw & RRECT_LEFT_SIDE:
        ctx.move_to(x + int(left_side_width) - offset, y + h)
        ctx.line_to(x + r, y + h)
        ctx.curve_to(x, y + h, x, y + h, x, y + h - r)
        ctx.line_to(x, y + r)
        ctx.curve_to(x, y, x, y, x + r, y)
        ctx.line_to(x + int(left_side_width) - offset, y)
        if close:
            ctx.line_to(x + int(left_side_width) - offset, y + h)

    if sides_to_draw & RRECT_RIGHT_SIDE:
        ctx.move_to(x + int(left_side_width) + offset, y)
        ctx.line_to(x + w - r, y)
        ctx.curve_to(x + w, y, x + w, y, x + w, y + r)
        ctx.line_to(x + w, y + h - r)
        ctx.curve_to(x + w, y + h, x + w, y + h, x + w - r, y + h)
        ctx.line_to(x + int(left_side_width) + offset, y + h)
        if close:
            ctx.line_to(x + int(left_side_width) + offset, y)


def rounded_rectangle(ctx, x, y, width, height, radius=4.):
    """Simple rounded rectangle algorithm

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
    style_context = widget.get_style_context()
    text_color = style_context.get_color(Gtk.StateFlags.PRELIGHT)

    if font_desc is None:
        font_desc = style_context.get_font(Gtk.StateFlags.NORMAL)
        font_desc.set_size(14 * Pango.SCALE)

    pango_context = widget.create_pango_context()
    layout = Pango.Layout(pango_context)
    layout.set_font_description(font_desc)
    layout.set_text(text, -1)
    width, height = layout.get_pixel_size()

    ctx.move_to(w_width / 2 - width / 2, w_height / 2 - height / 2)
    ctx.set_source_rgba(text_color.red, text_color.green, text_color.blue, 0.5)
    PangoCairo.show_layout(ctx, layout)

    # Draw an optional progress bar below the text (same width)
    if add_progress is not None:
        bar_height = 10
        ctx.set_source_rgba(*text_color)
        ctx.set_line_width(1.)
        rounded_rectangle(ctx,
                          w_width / 2 - width / 2 - .5,
                          w_height / 2 + height - .5, width + 1, bar_height + 1)
        ctx.stroke()
        rounded_rectangle(ctx,
                          w_width / 2 - width / 2,
                          w_height / 2 + height, int(width * add_progress) + .5, bar_height)
        ctx.fill()


def draw_cake(percentage, text=None, emblem=None, size=None):
    # Download percentage bar icon - it turns out the cake is a lie (d'oh!)
    # ..but the initial idea was to have a cake-style indicator, but that
    # didn't work as well as the progress bar, but the name stuck..

    if size is None:
        size = EPISODE_LIST_ICON_SIZE

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surface)

    bgc = get_background_color(Gtk.StateFlags.ACTIVE)
    fgc = get_background_color(Gtk.StateFlags.SELECTED)
    txc = get_foreground_color(Gtk.StateFlags.NORMAL)

    border = 1.5
    height = int(size * .4)
    width = size - 2 * border
    y = (size - height) / 2 + .5
    x = border

    # Background
    ctx.rectangle(x, y, width, height)
    ctx.set_source_rgb(bgc.red, bgc.green, bgc.blue)
    ctx.fill()

    # Filling
    if percentage > 0:
        fill_width = max(1, min(width - 2, (width - 2) * percentage + .5))
        ctx.rectangle(x + 1, y + 1, fill_width, height - 2)
        ctx.set_source_rgb(0.289, 0.5625, 0.84765625)
        ctx.fill()

    # Border
    ctx.rectangle(x, y, width, height)
    ctx.set_source_rgb(txc.red, txc.green, txc.blue)
    ctx.set_line_width(1)
    ctx.stroke()

    del ctx
    return surface


def draw_text_pill(left_text, right_text, x=0, y=0, border=2, radius=14,
                   widget=None, scale=1):

    # Padding (in px) at the right edge of the image (for Ubuntu; bug 1533)
    padding_right = 7

    x_border = border * 2

    if widget is None:
        # Use GTK+ style of a normal Button
        widget = Gtk.Label()

    style_context = widget.get_style_context()
    font_desc = style_context.get_font(Gtk.StateFlags.NORMAL)
    font_desc.set_weight(Pango.Weight.BOLD)

    pango_context = widget.create_pango_context()
    layout_left = Pango.Layout(pango_context)
    layout_left.set_font_description(font_desc)
    layout_left.set_text(left_text, -1)
    layout_right = Pango.Layout(pango_context)
    layout_right.set_font_description(font_desc)
    layout_right.set_text(right_text, -1)

    width_left, height_left = layout_left.get_pixel_size()
    width_right, height_right = layout_right.get_pixel_size()

    text_height = max(height_left, height_right)

    left_side_width = width_left + x_border * 2
    right_side_width = width_right + x_border * 2

    image_height = int(scale * (y + text_height + border * 2))
    image_width = int(scale * (x + left_side_width + right_side_width
                               + padding_right))

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, image_width, image_height)
    surface.set_device_scale(scale, scale)

    ctx = cairo.Context(surface)

    # Clip so as to not draw on the right padding (for Ubuntu; bug 1533)
    ctx.rectangle(0, 0, image_width - padding_right, image_height)
    ctx.clip()

    if left_text == '0':
        left_text = None
    if right_text == '0':
        right_text = None

    rect_width = left_side_width + right_side_width
    rect_height = text_height + border * 2
    if left_text is not None:
        draw_rounded_rectangle(ctx, x, y, rect_width, rect_height, radius,
                               left_side_width, RRECT_LEFT_SIDE, right_text is None)
        linear = cairo.LinearGradient(x, y, x + left_side_width / 2, y + rect_height / 2)
        linear.add_color_stop_rgba(0, .8, .8, .8, .5)
        linear.add_color_stop_rgba(.4, .8, .8, .8, .7)
        linear.add_color_stop_rgba(.6, .8, .8, .8, .6)
        linear.add_color_stop_rgba(.9, .8, .8, .8, .8)
        linear.add_color_stop_rgba(1, .8, .8, .8, .9)
        ctx.set_source(linear)
        ctx.fill()
        xpos, ypos, width_left, height = x + 1, y + 1, left_side_width, rect_height - 2
        if right_text is None:
            width_left -= 2
        draw_rounded_rectangle(ctx, xpos, ypos, rect_width, height, radius, width_left, RRECT_LEFT_SIDE, right_text is None)
        ctx.set_source_rgba(1., 1., 1., .3)
        ctx.set_line_width(1)
        ctx.stroke()
        draw_rounded_rectangle(ctx, x, y, rect_width, rect_height, radius,
                               left_side_width, RRECT_LEFT_SIDE, right_text is None)
        ctx.set_source_rgba(.2, .2, .2, .6)
        ctx.set_line_width(1)
        ctx.stroke()

        ctx.move_to(x + x_border, y + 1 + border)
        ctx.set_source_rgba(0, 0, 0, 1)
        PangoCairo.show_layout(ctx, layout_left)
        ctx.move_to(x - 1 + x_border, y + border)
        ctx.set_source_rgba(1, 1, 1, 1)
        PangoCairo.show_layout(ctx, layout_left)

    if right_text is not None:
        draw_rounded_rectangle(ctx, x, y, rect_width, rect_height, radius, left_side_width, RRECT_RIGHT_SIDE, left_text is None)
        linear = cairo.LinearGradient(
            x + left_side_width,
            y,
            x + left_side_width + right_side_width / 2,
            y + rect_height)
        linear.add_color_stop_rgba(0, .2, .2, .2, .9)
        linear.add_color_stop_rgba(.4, .2, .2, .2, .8)
        linear.add_color_stop_rgba(.6, .2, .2, .2, .6)
        linear.add_color_stop_rgba(.9, .2, .2, .2, .7)
        linear.add_color_stop_rgba(1, .2, .2, .2, .5)
        ctx.set_source(linear)
        ctx.fill()
        xpos, ypos, width, height = x, y + 1, rect_width - 1, rect_height - 2
        if left_text is None:
            xpos, width = x + 1, rect_width - 2
        draw_rounded_rectangle(ctx, xpos, ypos, width, height, radius, left_side_width, RRECT_RIGHT_SIDE, left_text is None)
        ctx.set_source_rgba(1., 1., 1., .3)
        ctx.set_line_width(1)
        ctx.stroke()
        draw_rounded_rectangle(ctx, x, y, rect_width, rect_height, radius, left_side_width, RRECT_RIGHT_SIDE, left_text is None)
        ctx.set_source_rgba(.1, .1, .1, .6)
        ctx.set_line_width(1)
        ctx.stroke()

        ctx.move_to(x + left_side_width + x_border, y + 1 + border)
        ctx.set_source_rgba(0, 0, 0, 1)
        PangoCairo.show_layout(ctx, layout_right)
        ctx.move_to(x - 1 + left_side_width + x_border, y + border)
        ctx.set_source_rgba(1, 1, 1, 1)
        PangoCairo.show_layout(ctx, layout_right)

    return surface


def draw_cake_pixbuf(percentage, text=None, emblem=None, size=None):
    return cairo_surface_to_pixbuf(draw_cake(percentage, text, emblem, size=size))


def draw_pill_pixbuf(left_text, right_text, widget=None, scale=1):
    return cairo_surface_to_pixbuf(draw_text_pill(left_text, right_text,
                                                  widget=widget, scale=scale))


def cake_size_from_widget(widget=None):
    if widget is None:
        # Use GTK+ style of a normal Button
        widget = Gtk.Label()
    style_context = widget.get_style_context()
    font_desc = style_context.get_font(Gtk.StateFlags.NORMAL)
    pango_context = widget.create_pango_context()
    layout = Pango.Layout(pango_context)
    layout.set_font_description(font_desc)
    layout.set_text("1", -1)
    # use text height as size
    return layout.get_pixel_size()[1]


def cairo_surface_to_pixbuf(s):
    """
    Converts a Cairo surface to a Gtk Pixbuf by
    encoding it as PNG and using the PixbufLoader.
    """
    bio = io.BytesIO()
    try:
        s.write_to_png(bio)
    except:
        # Write an empty PNG file to the StringIO, so
        # in case of an error we have "something" to
        # load. This happens in PyCairo < 1.1.6, see:
        # http://webcvs.cairographics.org/pycairo/NEWS?view=markup
        # Thanks to Chris Arnold for reporting this bug
        bio.write('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4'
                  'c6QAAAAZiS0dEAP8A\n/wD/oL2nkwAAAAlwSFlzAAALEwAACxMBAJqcGAAA'
                  'AAd0SU1FB9cMEQkqIyxn3RkAAAAZdEVYdENv\nbW1lbnQAQ3JlYXRlZCB3a'
                  'XRoIEdJTVBXgQ4XAAAADUlEQVQI12NgYGBgAAAABQABXvMqOgAAAABJ\nRU'
                  '5ErkJggg==\n'.decode('base64'))

    pbl = GdkPixbuf.PixbufLoader()
    pbl.write(bio.getvalue())
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

    padding = int(width / 8.0)
    bar_width = 2 * padding
    bar_height = height - 2 * padding
    bar_height_fill = bar_height * percentage

    # Background
    ctx.rectangle(padding, padding, bar_width, bar_height)
    ctx.set_source_rgba(*COLOR_BG)
    ctx.fill()

    # Foreground
    ctx.rectangle(padding, padding + bar_height - bar_height_fill, bar_width, bar_height_fill)
    ctx.set_source_rgba(*COLOR_FG)
    ctx.fill()
    ctx.rectangle(padding + bar_width / 3,
                  padding + bar_height - bar_height_fill,
                  bar_width / 4,
                  bar_height_fill)
    ctx.set_source_rgba(*COLOR_FG_HIGH)
    ctx.fill()

    # Border
    ctx.rectangle(padding - .5, padding - .5, bar_width + 1, bar_height + 1)
    ctx.set_source_rgba(* COLOR_BORDER)
    ctx.set_line_width(1.)
    ctx.stroke()

    return cairo_surface_to_pixbuf(surface)


def get_background_color(state=Gtk.StateFlags.NORMAL, widget=Gtk.TreeView()):
    """
    @param state state flag (e.g. Gtk.StateFlags.SELECTED to get selected background)
    @param widget specific widget to get info from.
           defaults to TreeView which has all one usually wants.
    @return background color from theme for widget or from its parents if transparent.
    """
    p = widget
    color = Gdk.RGBA(0, 0, 0, 0)
    while p is not None and color.alpha == 0:
        style_context = p.get_style_context()
        color = style_context.get_background_color(state)
        p = p.get_parent()
    return color


def get_foreground_color(state=Gtk.StateFlags.NORMAL, widget=Gtk.TreeView()):
    """
    @param state state flag (e.g. Gtk.StateFlags.SELECTED to get selected text color)
    @param widget specific widget to get info from
           defaults to TreeView which has all one usually wants.
    @return text color from theme for widget or its parents if transparent
    """
    p = widget
    color = Gdk.RGBA(0, 0, 0, 0)
    while p is not None and color.alpha == 0:
        style_context = p.get_style_context()
        color = style_context.get_color(state)
        p = p.get_parent()
    return color


def investigate_widget_colors(type_classes_and_widgets):
    """
    investigate using Gtk.StyleContext to get widget style properties
    I tried to compare gettings values from static and live widgets.
    To sum up, better use the live widget, because you'll get the correct path, classes, regions automatically.
    See "CSS Nodes" in widget documentation for classes and sub-nodes (=regions).
    WidgetPath and Region are replaced by CSSNodes in gtk4.
    Not sure it's legitimate usage, though: I got different results from one run to another.
    Run `GTK_DEBUG=interactive ./bin/gpodder` for gtk widget inspection
    """
    def investigate_stylecontext(style_ctx, label):
        style_ctx.save()
        for statename, state in [
                ('normal', Gtk.StateFlags.NORMAL),
                ('active', Gtk.StateFlags.ACTIVE),
                ('link', Gtk.StateFlags.LINK),
                ('visited', Gtk.StateFlags.VISITED)]:
            f.write("<dt>%s %s</dt><dd>\n" % (label, statename))
            colors = {
                'get_color': style_ctx.get_color(state),
                'get_background_color': style_ctx.get_background_color(state),
                'color': style_ctx.get_property('color', state),
                'background-color': style_ctx.get_property('background-color', state),
                'outline-color': style_ctx.get_property('outline-color', state),
            }
            f.write("<p>PREVIEW: <span style='background-color: %s; color: %s'>get_color + get_background_color</span>"
                  % (colors['get_background_color'].to_string(),
                     colors['get_color'].to_string()))
            f.write("<span style='background-color: %s; color: %s; border solid 2px %s;'>color + background-color properties</span></p>\n"
                  % (colors['background-color'].to_string(),
                     colors['color'].to_string(),
                     colors['outline-color'].to_string()))
            f.write("<p>VALUES: ")
            for p, v in colors.items():
                f.write("%s=<span style='background-color: %s;'>%s</span>" % (p, v.to_string(), v.to_string()))
            f.write("</p></dd>\n")
        style_ctx.restore()

    with open('/tmp/colors.html', 'w') as f:
        f.write("""<html>
                  <style type='text/css'>
                  body {color: red; background: yellow;}
                  span { display: inline-block; margin-right: 1ch; }
                  dd { margin-bottom: 1em; }
                  td { vertical-align: top; }
                  </style>
                  <table>""")
        for type_and_class, w in type_classes_and_widgets:
            f.write("<tr><td><dl>\n")
            # Create an empty style context
            style_ctx = Gtk.StyleContext()
            # Create an empty widget path
            widget_path = Gtk.WidgetPath()
            # Specify the widget class type you want to get colors from
            for t, c, r in type_and_class:
                widget_path.append_type(t)
                if c:
                    widget_path.iter_add_class(widget_path.length() - 1, c)
                if r:
                    widget_path.iter_add_region(widget_path.length() - 1, r, 0)
            style_ctx.set_path(widget_path)

            investigate_stylecontext(
                style_ctx,
                'STATIC {}'.format(' '.join('{}.{}({})'.format(t.__name__, c, r) for t, c, r in type_and_class)))

            f.write("</dl></td><td><dl>\n")

            investigate_stylecontext(w.get_style_context(), 'LIVE {}'.format(type(w).__name__))

        f.write("</dl></td></tr>\n")
        f.write("</table></html>\n")


def draw_iconcell_scale(column, cell, model, iter, scale):
    """
    Draw cell's pixbuf to a surface with proper scaling for high resolution
    displays. To be used as gtk.TreeViewColumn.set_cell_data_func.

    :param column: gtk.TreeViewColumn (ignored)
    :param cell: gtk.CellRenderer
    :param model: gtk.TreeModel (ignored)
    :param iter: gtk.TreeIter (ignored)
    :param scale: factor of the target display (e.g. 1 or 2)
    """
    pixbuf = cell.props.pixbuf
    if not pixbuf:
        return

    width = pixbuf.get_width()
    height = pixbuf.get_height()
    scale_inv = 1 / scale

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    surface.set_device_scale(scale, scale)

    cr = cairo.Context(surface)
    cr.scale(scale_inv, scale_inv)
    Gdk.cairo_set_source_pixbuf(cr, cell.props.pixbuf, 0, 0)
    cr.paint()

    cell.props.surface = surface
