# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2024 The gPodder Team
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
#  gpodder.gtkui.chapters - Display chapter information
#
import html
import logging

import requests
from gi.repository import GdkPixbuf, GLib, Gtk

import gpodder
from gpodder import util

logger = logging.getLogger(__name__)
_ = gpodder.gettext


class Chapters:

    def __init__(self, episode, on_jump_to_position):
        self.box = Gtk.ScrolledWindow(visible=True,
                min_content_width=400, min_content_height=500,
                margin_top=20, margin_bottom=20, margin_left=20, margin_right=20)
        self.on_jump_to_position = on_jump_to_position
        self.update(episode)

    def update(self, episode):
        """
            display episode
            FIXME: it's currently possible to open many episode windows and the window
            is not reused. But maybe we want a single
        """
        self.episode = episode
        chapters = None
        if episode and episode.chapters:
            chapters = episode.parsed_chapters
        grid = Gtk.Grid(visible=True,
            column_homogeneous=False, column_spacing=5, row_spacing=10)
        self.box.add(grid)
        if not chapters:
            return
        # just a few example images since I don't find a good example feed
        dummy_images = [
            "https://hackaday.com/wp-content/uploads/2024/08/mange-thumb.png?w=600&h=600",
            "https://hackaday.com/wp-content/uploads/2024/08/salsa-one-600.jpg?w=600&h=600",
            "https://hackaday.com/wp-content/uploads/2016/01/darkarts-thumb.jpg?w=600&h=600",
            "https://hackaday.com/wp-content/uploads/2016/05/microphone-thumb.jpg?w=600&h=600",
            "https://hackaday.com/wp-content/uploads/2024/08/Screenshot-2024-08-15-141222-e1723753801959.png?w=600&h=600",
            "https://hackaday.com/wp-content/uploads/2024/08/bqagw8jbta751_thumbnail.png?w=600&h=600",
        ]
        align_hours = max(c["start"] for c in chapters) > 3600
        # to display chapter duration:
        # for c, nc in zip(chapters, chapters[1:] + [{"start": episode.total_time}]):
        for i, c in enumerate(chapters):
            if i < len(dummy_images):
                c["image"] = dummy_images[i]
                c["href"] = "https://hackaday.com/2019/04/18/all-you-need-to-know-about-i2s/"
            if c.get("image"):
                try:
                    # FIXME: image relative to feed url?
                    data = util.urlopen(c["image"], timeout=5, stream=True)
                    # FIXME: No cache + no separate thread to display loading...
                    pbl = GdkPixbuf.PixbufLoader()
                    for chunk in data.iter_content(chunk_size=None):
                        pbl.write_bytes(GLib.Bytes(chunk))
                    pbl.close()
                    pixbuf = pbl.get_pixbuf()
                    w, h = pixbuf.get_width(), pixbuf.get_height()
                    dw, dh = None, None
                    if w > 64 or h > 64:
                        if w > h:
                            dw = 64
                            dh = h * (64 / w)
                        else:
                            dh = 64
                            dw = w * (64 / h)
                    if dh:
                        pixbuf = pixbuf.scale_simple(dw, dh, GdkPixbuf.InterpType.BILINEAR)
                    img = Gtk.Image.new_from_pixbuf(pixbuf)
                    btn = Gtk.Button(visible=True, relief=Gtk.ReliefStyle.NONE)
                    btn.set_image(img)
                    btn.connect("clicked", self.on_image_clicked, c["image"])
                    img = btn
                except requests.exceptions.RequestException as e:
                    logger.warning("Unable to load image %s: %r", c["image"], e)
                    img = Gtk.Image.new_from_icon_name("action-unavailable-symbolic",
                        Gtk.IconSize.DIALOG)
                img.set_visible(True)
                grid.attach(img, 0, i * 2, 1, 2)

            start_str = util.format_time(c["start"], always_include_hours=align_hours)
            lbl = Gtk.Label(visible=True, xalign=1)
            lbl.set_markup("""<a href="%(position)i">%(timestamp)s</a>""" % {"position": c["start"], "timestamp": start_str})
            lbl.connect("activate-link", self.on_timestamp_click)
            grid.attach(lbl, 1, i * 2, 1, 1)
            lbl = Gtk.Label(visible=True, xalign=0)
            lbl.set_markup(_("<b>%(title)s</b>" % {
                "title": html.escape(c["title"]),
            }))
            grid.attach(lbl, 2, i * 2, 7, 1)
            if c.get("href"):
                lbl = Gtk.Label(visible=True, xalign=1)
                lbl.set_markup("""<a href="%(href)s">%(href)s</a>""" % {"href": html.escape(c["href"])})
                grid.attach(lbl, 1, i * 2 + 1, 8, 1)

    def on_image_clicked(self, _image, url=None):
        util.open_website(url)

    def on_timestamp_click(self, _lbl, target):
        logger.debug("TS clicked %s", target)
        if self.on_jump_to_position is not None:
            fn = self.episode.local_filename(create=False, check_only=True)
            if fn:
                self.on_jump_to_position(fn, int(target))
