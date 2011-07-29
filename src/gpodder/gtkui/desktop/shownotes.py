# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
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
import gobject
import pango
import os
import cgi


import gpodder

_ = gpodder.gettext

import logging
logger = logging.getLogger(__name__)

from gpodder import util

from gpodder.gtkui.interface.shownotes import gPodderShownotesBase


SHOWNOTES_HTML_TEMPLATE = """
<html>
  <head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
  </head>
  <body>
    <span style="font-size: big; font-weight: bold;">%s</span>
    <br>
    <span style="font-size: small;">%s (%s)</span>
    <hr style="border: 1px #eeeeee solid;">
    <p>%s</p>
  </body>
</html>
"""

class gPodderShownotes(gPodderShownotesBase):
    def on_create_window(self):
        self.textview.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('#ffffff'))
        if self._config.enable_html_shownotes:
            try:
                import webkit
                webview_signals = gobject.signal_list_names(webkit.WebView)
                if 'navigation-policy-decision-requested' in webview_signals:
                    setattr(self, 'have_webkit', True)
                    setattr(self, 'htmlview', webkit.WebView())
                else:
                    logger.warn('Your WebKit is too old (gPodder bug 1001).')
                    setattr(self, 'have_webkit', False)

                def navigation_policy_decision(wv, fr, req, action, decision):
                    REASON_LINK_CLICKED, REASON_OTHER = 0, 5
                    if action.get_reason() == REASON_LINK_CLICKED:
                        util.open_website(req.get_uri())
                        decision.ignore()
                    elif action.get_reason() == REASON_OTHER:
                        decision.use()
                    else:
                        decision.ignore()

                self.htmlview.connect('navigation-policy-decision-requested', \
                        navigation_policy_decision)

                self.scrolled_window.remove(self.scrolled_window.get_child())
                self.scrolled_window.add(self.htmlview)
                self.textview = None
                self.htmlview.load_html_string('', '')
                self.htmlview.show()
            except ImportError:
                setattr(self, 'have_webkit', False)
        else:
            setattr(self, 'have_webkit', False)

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

        if self.have_webkit:
            self.htmlview.load_html_string('<html><head></head><body><em>%s</em></body></html>' % _('Loading shownotes...'), '')
        else:
            self.b = gtk.TextBuffer()
            self.textview.set_buffer(self.b)

    def on_display_text(self):
        # Now do the stuff that takes a bit longer...
        heading = self.episode.title
        subheading = _('from %s') % (self.episode.channel.title)
        description = self.episode.description

        if self.have_webkit:
            global SHOWNOTES_HTML_TEMPLATE

            # Get the description - if it looks like plaintext, replace the
            # newline characters with line breaks for the HTML view
            description = self.episode.description_html

            args = (
                    cgi.escape(heading),
                    cgi.escape(subheading),
                    self.episode.get_play_info_string(),
                    description,
            )
            url = os.path.dirname(self.episode.channel.url)
            self.htmlview.load_html_string(SHOWNOTES_HTML_TEMPLATE % args, url)
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
        if self.have_webkit:
            self.htmlview.load_html_string('', '')
        else:
            self.textview.get_buffer().set_text('')

    def on_episode_status_changed(self):
        if self.task:
            self.download_progress.show()
            self.btnCancel.set_property('visible', self.task.status not in \
                    (self.task.DONE, self.task.CANCELLED, self.task.FAILED))
            self.btnDownload.set_property('visible', self.task.status in
                    (self.task.CANCELLED, self.task.FAILED, self.task.PAUSED))
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


    def on_download_status_progress(self):
        # We receive this from the main window every time the progress
        # for our episode has changed (but only when this window is visible)
        if self.task:
            self.download_progress.set_fraction(self.task.progress)
            self.download_progress.set_text('%s: %d%% (%s/s)' % ( \
                    self.task.STATUS_MESSAGE[self.task.status], \
                    100.*self.task.progress, \
                    util.format_filesize(self.task.speed)))

