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


class gPodderShownotes(BuilderWidget):
    finger_friendly_widgets = ['btnPlay', 'btnDownload', 'btnCancel', 'btnClose', 'textview']
    
    def new(self):
        setattr(self, 'episode', None)
        setattr(self, 'download_callback', None)
        setattr(self, 'play_callback', None)
        self.gPodderShownotes.connect('delete-event', self.on_delete_event)
        self._config.connect_gtk_window(self.gPodderShownotes, 'episode_window', True)
        self.textview.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('#ffffff'))
        if self._config.enable_html_shownotes and \
                not gpodder.interface == gpodder.MAEMO:
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
        self.gPodderShownotes.connect('key-press-event', self.on_key_press)

    def on_key_press(self, widget, event):
        if not hasattr(self.scrolled_window, 'get_vscrollbar'):
            return
        vsb = self.scrolled_window.get_vscrollbar()
        vadj = vsb.get_adjustment()
        step = vadj.step_increment
        if event.keyval in (gtk.keysyms.J, gtk.keysyms.j):
            vsb.set_value(vsb.get_value() + step)
        elif event.keyval in (gtk.keysyms.K, gtk.keysyms.k):
            vsb.set_value(vsb.get_value() - step)

    def show(self, episode, download_callback, play_callback):
        self.download_progress.set_fraction(0)
        self.download_progress.set_text(_('Please wait...'))
        self.episode = episode
        self.download_callback = download_callback
        self.play_callback = play_callback

        self.gPodderShownotes.set_title(self.episode.title)

        if self.have_gtkhtml2:
            import gtkhtml2
            d = gtkhtml2.Document()
            d.open_stream('text/html')
            d.write_stream('<html><head></head><body><em>%s</em></body></html>' % _('Loading shownotes...'))
            d.close_stream()
            self.htmlview.set_document(d)
        else:
            b = gtk.TextBuffer()
            self.textview.set_buffer(b)

        self.hide_show_widgets()
        self.gPodderShownotes.show()

        # Make sure the window comes up right now:
        while gtk.events_pending():
            gtk.main_iteration(False)

        # Now do the stuff that takes a bit longer...
        heading = self.episode.title
        subheading = 'from %s' % (self.episode.channel.title)
        description = self.episode.description
        footer = []

        if self.have_gtkhtml2:
            import gtkhtml2
            d.connect('link-clicked', lambda d, url: util.open_website(url))
            def request_url(document, url, stream):
                def opendata(url, stream):
                    fp = urllib2.urlopen(url)
                    data = fp.read(1024*10)
                    while data != '':
                        stream.write(data)
                        data = fp.read(1024*10)
                    stream.close()
                threading.Thread(target=opendata, args=[url, stream]).start()
            d.connect('request-url', request_url)
            d.clear()
            d.open_stream('text/html')
            d.write_stream('<html><head><meta http-equiv="content-type" content="text/html; charset=utf-8"/></head><body>')
            d.write_stream('<span style="font-size: big; font-weight: bold;">%s</span><br><span style="font-size: small;">%s</span><hr style="border: 1px #eeeeee solid;"><p>' % (saxutils.escape(heading), saxutils.escape(subheading)))
            d.write_stream(self.episode.description)
            if len(footer):
                d.write_stream('<hr style="border: 1px #eeeeee solid;">')
                d.write_stream('<span style="font-size: small;">%s</span>' % ('<br>'.join(((saxutils.escape(f) for f in footer))),))
            d.write_stream('</p></body></html>')
            d.close_stream()
        else:
            b.create_tag('heading', scale=pango.SCALE_LARGE, weight=pango.WEIGHT_BOLD)
            b.create_tag('subheading', scale=pango.SCALE_SMALL)
            b.create_tag('footer', scale=pango.SCALE_SMALL)

            b.insert_with_tags_by_name(b.get_end_iter(), heading, 'heading')
            b.insert_at_cursor('\n')
            b.insert_with_tags_by_name(b.get_end_iter(), subheading, 'subheading')
            b.insert_at_cursor('\n\n')
            b.insert(b.get_end_iter(), util.remove_html_tags(description))
            if len(footer):
                 b.insert_at_cursor('\n\n')
                 b.insert_with_tags_by_name(b.get_end_iter(), '\n'.join(footer), 'footer')
            b.place_cursor(b.get_start_iter())

    def on_cancel(self, widget):
        self.download_status_model.cancel_by_url(self.episode.url)

    def on_delete_event(self, widget, event):
        # Avoid destroying the dialog, simply hide
        self.on_close(widget)
        return True

    def on_close(self, widget):
        self.episode = None
        if self.have_gtkhtml2:
            import gtkhtml2
            self.htmlview.set_document(gtkhtml2.Document())
        else:
            self.textview.get_buffer().set_text('')
        self.gPodderShownotes.hide()

    def download_status_changed(self, episode_urls):
        # Reload the episode from the database, so a newly-set local_filename
        # as a result of a download gets updated in the episode object
        self.episode.reload_from_db()
        self.hide_show_widgets()

    def download_status_progress(self, progress, speed):
        # We receive this from the main window every time the progress
        # for our episode has changed (but only when this window is visible)
        self.download_progress.set_fraction(progress)
        self.download_progress.set_text('Downloading: %d%% (%s/s)' % (100.*progress, util.format_filesize(speed)))

    def hide_show_widgets(self):
        is_downloading = self.episode_is_downloading(self.episode)
        if is_downloading:
            self.download_progress.show_all()
            self.btnCancel.show_all()
            self.btnPlay.hide_all()
            self.btnDownload.hide_all()
        else:
            self.download_progress.hide_all()
            self.btnCancel.hide_all()
            if self.episode.was_downloaded(and_exists=True):
                if self.episode.file_type() in ('audio', 'video'):
                    self.btnPlay.set_label(gtk.STOCK_MEDIA_PLAY)
                else:
                    self.btnPlay.set_label(gtk.STOCK_OPEN)
                self.btnPlay.set_use_stock(True)
                self.btnPlay.show_all()
                self.btnDownload.hide_all()
            else:
                self.btnPlay.hide_all()
                self.btnDownload.show_all()

    def on_download(self, widget):
        if self.download_callback:
            self.download_callback()

    def on_playback(self, widget):
        if self.play_callback:
            self.play_callback()
        self.on_close(widget)

