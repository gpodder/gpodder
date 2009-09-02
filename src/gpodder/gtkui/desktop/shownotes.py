# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
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
import pango
import urllib2
import threading

from xml.sax import saxutils

import gpodder

_ = gpodder.gettext

from gpodder import util

from gpodder.gtkui.interface.common import BuilderWidget
from gpodder.gtkui.interface.shownotes import gPodderShownotesBase

class gPodderShownotes(gPodderShownotesBase):
    def on_create_window(self):
        self.textview.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('#ffffff'))
        if self._config.enable_html_shownotes:
            try:
                import gtkhtml2
                setattr(self, 'have_gtkhtml2', True)
                # Generate a HTML view and remove the textview
                setattr(self, 'htmlview', gtkhtml2.View())
                self.scrolled_window.remove(self.scrolled_window.get_child())
                self.scrolled_window.add(self.htmlview)
                self.textview = None
                self.htmlview.set_document(gtkhtml2.Document())
                self.htmlview.show()
            except ImportError:
                setattr(self, 'have_gtkhtml2', False)
        else:
            setattr(self, 'have_gtkhtml2', False)

    def on_scroll_down(self):
        if not hasattr(self.scrolled_window, 'get_vscrollbar'):
            return
        vsb = self.scrolled_window.get_vscrollbar()
        vadj = vsb.get_adjustment()
        step = vadj.step_increment
        vsb.set_value(vsb.get_value() + step)

    def on_scroll_up(self):
        if not hasattr(self.scrolled_window, 'get_vscrollbar'):
            return
        vsb = self.scrolled_window.get_vscrollbar()
        vadj = vsb.get_adjustment()
        step = vadj.step_increment
        vsb.set_value(vsb.get_value() - step)

    def on_show_window(self):
        self.download_progress.set_fraction(0)
        self.download_progress.set_text(_('Please wait...'))
        self.main_window.set_title(self.episode.title)

        if self.have_gtkhtml2:
            import gtkhtml2
            self.d = gtkhtml2.Document()
            self.d.open_stream('text/html')
            self.d.write_stream('<html><head></head><body><em>%s</em></body></html>' % _('Loading shownotes...'))
            self.d.close_stream()
            self.htmlview.set_document(self.d)
        else:
            self.b = gtk.TextBuffer()
            self.textview.set_buffer(self.b)

    def on_display_text(self):
        # Now do the stuff that takes a bit longer...
        heading = self.episode.title
        subheading = 'from %s' % (self.episode.channel.title)
        description = self.episode.description

        if self.have_gtkhtml2:
            import gtkhtml2
            self.d.connect('link-clicked', lambda doc, url: util.open_website(url))
            def request_url(document, url, stream):
                def opendata(url, stream):
                    fp = urllib2.urlopen(url)
                    data = fp.read(1024*10)
                    while data != '':
                        stream.write(data)
                        data = fp.read(1024*10)
                    stream.close()
                threading.Thread(target=opendata, args=[url, stream]).start()
            self.d.connect('request-url', request_url)
            self.d.clear()
            self.d.open_stream('text/html')
            self.d.write_stream('<html><head><meta http-equiv="content-type" content="text/html; charset=utf-8"/></head><body>')
            self.d.write_stream('<span style="font-size: big; font-weight: bold;">%s</span><br><span style="font-size: small;">%s</span><hr style="border: 1px #eeeeee solid;"><p>' % (saxutils.escape(heading), saxutils.escape(subheading)))
            self.d.write_stream(self.episode.description)
            self.d.write_stream('</p></body></html>')
            self.d.close_stream()
        else:
            self.b.create_tag('heading', scale=pango.SCALE_LARGE, weight=pango.WEIGHT_BOLD)
            self.b.create_tag('subheading', scale=pango.SCALE_SMALL)

            self.b.insert_with_tags_by_name(self.b.get_end_iter(), heading, 'heading')
            self.b.insert_at_cursor('\n')
            self.b.insert_with_tags_by_name(self.b.get_end_iter(), subheading, 'subheading')
            self.b.insert_at_cursor('\n\n')
            self.b.insert(self.b.get_end_iter(), util.remove_html_tags(description))
            self.b.place_cursor(self.b.get_start_iter())

    def on_hide_window(self):
        self.episode = None
        if self.have_gtkhtml2:
            import gtkhtml2
            self.htmlview.set_document(gtkhtml2.Document())
        else:
            self.textview.get_buffer().set_text('')

    def on_episode_status_changed(self):
        self.hide_show_widgets()

    def on_download_status_progress(self):
        # We receive this from the main window every time the progress
        # for our episode has changed (but only when this window is visible)
        if self.task:
            self.download_progress.set_fraction(self.task.progress)
            self.download_progress.set_text('%s: %d%% (%s/s)' % ( \
                    self.task.STATUS_MESSAGE[self.task.status], \
                    100.*self.task.progress, \
                    util.format_filesize(self.task.speed)))

    def hide_show_widgets(self):
        if self.task:
            self.download_progress.show()
            self.btnCancel.set_property('visible', self.task.status not in \
                    (self.task.DONE, self.task.CANCELLED, self.task.FAILED))
            self.btnDownload.set_property('visible', \
                    not self.btnCancel.get_property('visible'))
            self.btnPlay.set_property('visible', \
                    self.task.status == self.task.DONE)
        else:
            self.download_progress.hide()
            self.btnCancel.hide()
            if self.episode.was_downloaded(and_exists=True):
                if self.episode.file_type() in ('audio', 'video'):
                    self.btnPlay.set_label(gtk.STOCK_MEDIA_PLAY)
                else:
                    self.btnPlay.set_label(gtk.STOCK_OPEN)
                self.btnPlay.set_use_stock(True)
                self.btnPlay.show_all()
                self.btnDownload.hide()
            else:
                self.btnPlay.show()
                self.btnDownload.show()

