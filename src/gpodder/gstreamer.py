# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2010 Thomas Perl and the gPodder Team
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

try:
    import gobject
    import pygst
    pygst.require('0.10')
    import gst
    from gst.extend.discoverer import Discoverer
    have_gst = True
except:
    have_gst = False

class GstFile:
    def __init__(self):
        self.mainloop = gobject.MainLoop()
        self.result = None

    def run(self, filename):
        gobject.idle_add(self.on_idle, filename)
        self.mainloop.run()
        return self.result / gst.MSECOND

    def on_idle(self, filename):
        d = Discoverer(filename)
        d.connect('discovered', self.on_data)
        d.discover()
        return False

    def on_data(self, discoverer, ismedia):
        if discoverer.is_video:
            self.result = discoverer.videolength
        elif discoverer.is_audio:
            self.result = discoverer.audiolength
        gobject.idle_add(self.mainloop.quit)

def get_track_length(filename):
    """
    Returns track length in microseconds.

    Prefers video streams to audio streams. If no supported streams were found,
    returns None.
    """
    if not have_gst:
        return None
    return GstFile().run(filename)

__all__ = ['get_track_length']

# vim: set ts=4 sts=4 sw=4 et:
