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
#  gpodder.gtkui.playbar - A play bar showing play position
#
import logging

from gi.repository import Gtk, Pango

import gpodder
from gpodder.player import MediaPlayerDBusReceiver

logger = logging.getLogger(__name__)
_ = gpodder.gettext


class Playbar:
    NO_PLAYBACK = _("No playback")
    TR_STATUS = {
        MediaPlayerDBusReceiver.SIGNAL_STARTED: _("Playing"),
        MediaPlayerDBusReceiver.SIGNAL_STOPPED: _("Stopped"),
        MediaPlayerDBusReceiver.SIGNAL_EXITED: NO_PLAYBACK,
    }
    STEP_INCREMENT = 30
    STEP_DECREMENT = 15
    PAGE_INCREMENT = 120
    PAGE_DECREMENT = 60
    END_MARGIN = 5

    def __init__(self, on_playbar_clicked):
        self.box = Gtk.Box(self, orientation=Gtk.Orientation.VERTICAL, visible=True)
        self.playbar = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, draw_value=False, visible=True, sensitive=False)
        self.playbar.set_range(0, 100)
        self.playbar.set_value(0)
        self.playbar.connect("change-value", self.on_change_value)
        self.label = Gtk.Label(self.NO_PLAYBACK, visible=True, ellipsize=Pango.EllipsizeMode.END)
        self.box.add(self.playbar)
        self.box.add(self.label)
        self.episode_id = None
        self.file_uri = None
        self.on_playbar_clicked = on_playbar_clicked

    def on_episode_playback(self, episode, _start, position, total, file_uri, event):
        """ called from d-bus notifications: adjust playbar accordingly """
        logger.debug("on_episode_playback %s %s %s %s", event, episode.title, position, total)
        exited = event == MediaPlayerDBusReceiver.SIGNAL_EXITED
        status = self.TR_STATUS[event]
        if exited:
            self.episode_id = None
            self.file_uri = None
            self.label.set_text(status)
            self.playbar.set_value(0)
            self.playbar.set_range(0, 100)
            self.playbar.set_sensitive(False)
            self.playbar.clear_marks()
            self.chapter_pairs = None
            return
        self.playbar.set_sensitive(True)
        self.playbar.set_range(0, total)
        if episode.id != self.episode_id:
            self.episode_id = episode.id
            self.file_uri = file_uri
            self.playbar.clear_marks()
            self.chapter_pairs = None
            if episode.chapters:
                chapters = episode.parsed_chapters
                if chapters:
                    self.chapter_pairs = list(zip(chapters, chapters[1:] + [{"start": episode.total_time}]))
                    for c, nc in self.chapter_pairs:
                        self.playbar.add_mark(c["start"], Gtk.PositionType.BOTTOM, None)
            else:
                self.chapter_pairs = None
        chapter = None
        if self.chapter_pairs:
            for c, nc in self.chapter_pairs:
                if c["start"] <= position and nc["start"] >= position:
                    chapter = c
        if chapter:
            self.label.set_text(
                _("%(status)s %(title)s -- %(chapter)s")
                % {"status": status, "title": episode.title, "chapter": chapter["title"]})
            self.label.set_tooltip_text(
                _("%(title)s -- %(chapter)s")
                % {"title": episode.title, "chapter": chapter["title"]})
        else:
            self.label.set_text(_("%(status)s %(title)s") % {"status": status, "title": episode.title})
            self.label.set_tooltip_text(_("%(title)s") % {"title": episode.title})
        self.playbar.set_value(position)

    def on_change_value(self, playbar, scroll, value):
        """ user-initiated change: will trigger player jump """
        new_value = None
        if scroll == Gtk.ScrollType.JUMP:
            new_value = int(value)
        elif scroll == Gtk.ScrollType.START:
            new_value = 0
        elif scroll == Gtk.ScrollType.END:
            # don't see the point of going to the end, open to discussion
            new_value = int(max(0, playbar.get_adjustment().get_upper() - self.END_MARGIN))
        elif scroll == Gtk.ScrollType.STEP_BACKWARD:
            new_value = int(max(0, value - self.STEP_DECREMENT))
        elif scroll == Gtk.ScrollType.STEP_FORWARD:
            new_value = int(min(playbar.get_adjustment().get_upper() - self.END_MARGIN, value + self.STEP_INCREMENT))
        elif scroll == Gtk.ScrollType.PAGE_BACKWARD:
            if self.chapter_pairs:
                for c, nc in self.chapter_pairs:
                    if c["start"] <= value and nc["start"] >= value:
                        new_value = c["start"]
                        break
            if new_value is None:
                new_value = int(max(0, value - self.PAGE_DECREMENT))
        elif scroll == Gtk.ScrollType.PAGE_FORWARD:
            if self.chapter_pairs:
                for c, nc in self.chapter_pairs:
                    if c["start"] <= value and nc["start"] > value:
                        new_value = nc["start"]
                        break
            if new_value is None:
                new_value = int(min(playbar.get_adjustment().get_upper() - self.END_MARGIN, value + self.PAGE_INCREMENT))
        if new_value is None:
            logger.debug("couldn't compute jump")
        else:
            logger.debug("jump to %s", new_value)
            playbar.set_value(new_value)
            if self.on_playbar_clicked:
                self.on_playbar_clicked(self.file_uri, new_value)
        return True
