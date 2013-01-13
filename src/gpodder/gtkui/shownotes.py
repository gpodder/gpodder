# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2012 Thomas Perl and the gPodder Team
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


try:
    import webkit
    webview_signals = gobject.signal_list_names(webkit.WebView)
    if 'navigation-policy-decision-requested' in webview_signals:
        have_webkit = True
    else:
        logger.warn('Your WebKit is too old (gPodder bug 1001).')
        have_webkit = False
except ImportError:
    have_webkit = False


class gPodderShownotes:
    def __init__(self, scrolled_window):
        self.scrolled_window = scrolled_window
        self.scrolled_window.add(self.init())
        self.scrolled_window.show_all()

    def set_episode(self, episode):
        if episode is None:
            self.clear()
            self.scrolled_window.hide()
        else:
            heading = episode.title
            subheading = _('from %s') % (episode.channel.title)
            self.update(heading, subheading, episode)
            self.scrolled_window.show()


class gPodderShownotesText(gPodderShownotes):
    def init(self):
        self.text_view = gtk.TextView()
        self.text_view.set_wrap_mode(gtk.WRAP_WORD_CHAR)
        self.text_view.set_border_width(10)
        self.text_buffer = gtk.TextBuffer()
        self.text_buffer.create_tag('heading', scale=pango.SCALE_LARGE, weight=pango.WEIGHT_BOLD)
        self.text_buffer.create_tag('subheading', scale=pango.SCALE_SMALL)
        self.text_view.set_buffer(self.text_buffer)
        self.text_view.modify_bg(gtk.STATE_NORMAL,
                gtk.gdk.color_parse('#ffffff'))
        return self.text_view

    def clear(self):
        self.text_buffer.set_text('')

    def update(self, heading, subheading, episode):
        self.text_buffer.set_text('')
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(), heading, 'heading')
        self.text_buffer.insert_at_cursor('\n')
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(), subheading, 'subheading')
        self.text_buffer.insert_at_cursor('\n\n')
        self.text_buffer.insert(self.text_buffer.get_end_iter(), util.remove_html_tags(episode.description))
        self.text_buffer.place_cursor(self.text_buffer.get_start_iter())


class gPodderShownotesHTML(gPodderShownotes):
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

    def init(self):
        self.html_view = webkit.WebView()
        self.html_view.connect('navigation-policy-decision-requested',
                self._navigation_policy_decision)
        self.html_view.load_html_string('', '')
        return self.html_view

    def _navigation_policy_decision(self, wv, fr, req, action, decision):
        REASON_LINK_CLICKED, REASON_OTHER = 0, 5
        if action.get_reason() == REASON_LINK_CLICKED:
            util.open_website(req.get_uri())
            decision.ignore()
        elif action.get_reason() == REASON_OTHER:
            decision.use()
        else:
            decision.ignore()

    def clear(self):
        self.html_view.load_html_string('', '')

    def update(self, heading, subheading, episode):
        html = self.SHOWNOTES_HTML_TEMPLATE % (
                cgi.escape(heading),
                cgi.escape(subheading),
                episode.get_play_info_string(),
                episode.description_html,
        )
        url = os.path.dirname(episode.channel.url)
        self.html_view.load_html_string(html, url)

