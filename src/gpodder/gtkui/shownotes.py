# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2016 Thomas Perl and the gPodder Team
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

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango

import html
import logging

import gpodder

from gpodder import util
from gpodder.gtkui.draw import draw_text_box_centered

_ = gpodder.gettext

logger = logging.getLogger(__name__)

has_webkit2 = False
try:
    import gi
    gi.require_version('WebKit2', '4.0')
    from gi.repository import WebKit2
    has_webkit2 = True
except (ImportError, ValueError):
    logger.info('No WebKit2 gobject bindings, so no HTML shownotes')


def get_shownotes(enable_html, pane):
    if enable_html and has_webkit2:
        return gPodderShownotesHTML(pane)
    else:
        return gPodderShownotesText(pane)


class gPodderShownotes:
    def __init__(self, shownotes_pane):
        self.shownotes_pane = shownotes_pane

        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_shadow_type(Gtk.ShadowType.IN)
        self.scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.add(self.init())
        self.scrolled_window.show_all()

        self.da_message = Gtk.DrawingArea()
        self.da_message.set_property('expand', True)
        self.da_message.connect('draw', self.on_shownotes_message_expose_event)
        self.shownotes_pane.add(self.da_message)
        self.shownotes_pane.add(self.scrolled_window)

        self.set_complain_about_selection(True)
        self.hide_pane()

    # Either show the shownotes *or* a message, 'Please select an episode'
    def set_complain_about_selection(self, message=True):
        if message:
            self.scrolled_window.hide()
            self.da_message.show()
        else:
            self.da_message.hide()
            self.scrolled_window.show()

    def set_episodes(self, selected_episodes):
        if self.pane_is_visible:
            if len(selected_episodes) == 1:
                episode = selected_episodes[0]
                heading = episode.title
                subheading = _('from %s') % (episode.channel.title)
                self.update(heading, subheading, episode)
                self.set_complain_about_selection(False)
            else:
                self.set_complain_about_selection(True)

    def show_pane(self, selected_episodes):
        self.pane_is_visible = True
        self.set_episodes(selected_episodes)
        self.shownotes_pane.show()

    def hide_pane(self):
        self.pane_is_visible = False
        self.shownotes_pane.hide()

    def toggle_pane_visibility(self, selected_episodes):
        if self.pane_is_visible:
            self.hide_pane()
        else:
            self.show_pane(selected_episodes)

    def on_shownotes_message_expose_event(self, drawingarea, ctx):
        # paint the background white
        ctx.set_source_rgba(1, 1, 1)
        x1, y1, x2, y2 = ctx.clip_extents()
        ctx.rectangle(x1, y1, x2 - x1, y2 - y1)
        ctx.fill()

        width, height = drawingarea.get_allocated_width(), drawingarea.get_allocated_height(),
        text = _('Please select an episode')
        draw_text_box_centered(ctx, drawingarea, width, height, text, None, None)
        return False


class gPodderShownotesText(gPodderShownotes):
    def init(self):
        self.text_view = Gtk.TextView()
        self.text_view.set_property('expand', True)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_border_width(10)
        self.text_view.set_editable(False)
        self.text_view.connect('button-release-event', self.on_button_release)
        self.text_view.connect('key-press-event', self.on_key_press)
        self.text_buffer = Gtk.TextBuffer()
        self.text_buffer.create_tag('heading', scale=2, weight=Pango.Weight.BOLD)
        self.text_buffer.create_tag('subheading', scale=1.5)
        self.text_buffer.create_tag('hyperlink', foreground="#0000FF", underline=Pango.Underline.SINGLE)
        self.text_view.set_buffer(self.text_buffer)
        return self.text_view

    def update(self, heading, subheading, episode):
        hyperlinks = [(0, None)]
        self.text_buffer.set_text('')
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(), heading, 'heading')
        self.text_buffer.insert_at_cursor('\n')
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(), subheading, 'subheading')
        self.text_buffer.insert_at_cursor('\n\n')
        for target, text in util.extract_hyperlinked_text(episode.description):
            hyperlinks.append((self.text_buffer.get_char_count(), target))
            if target:
                self.text_buffer.insert_with_tags_by_name(
                    self.text_buffer.get_end_iter(), text, 'hyperlink')
            else:
                self.text_buffer.insert(
                    self.text_buffer.get_end_iter(), text)
        hyperlinks.append((self.text_buffer.get_char_count(), None))
        self.hyperlinks = [(start, end, url) for (start, url), (end, _) in zip(hyperlinks, hyperlinks[1:]) if url]
        self.text_buffer.place_cursor(self.text_buffer.get_start_iter())

    def on_button_release(self, widget, event):
        if event.button == 1:
            self.activate_links()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Return:
            self.activate_links()
            return True

        return False

    def activate_links(self):
        if self.text_buffer.get_selection_bounds() == ():
            pos = self.text_buffer.props.cursor_position
            target = next((url for start, end, url in self.hyperlinks if start < pos < end), None)
            if target is not None:
                util.open_website(target)


class gPodderShownotesHTML(gPodderShownotes):
    def init(self):
        self.html_view = WebKit2.WebView()
        self.html_view.set_property('expand', True)
        self.html_view.connect('mouse-target-changed', self.on_mouse_over)
        self.html_view.connect('context-menu', self.on_context_menu)
        self.html_view.connect('decide-policy', self.on_decide_policy)
        self.header = Gtk.Label.new()
        self.header.set_halign(Gtk.Align.START)
        self.header.set_valign(Gtk.Align.START)
        self.header.set_property('margin', 10)
        self.header.set_selectable(True)
        self.status = Gtk.Label.new()
        self.status.set_halign(Gtk.Align.START)
        self.status.set_valign(Gtk.Align.END)
        self.set_status(None)
        grid = Gtk.Grid()
        grid.attach(self.header, 0, 0, 1, 1)
        grid.attach(self.html_view, 0, 1, 1, 1)
        grid.attach(self.status, 0, 2, 1, 1)
        return grid

    def update(self, heading, subheading, episode):
        tmpl = '<span size="x-large" font_weight="bold">%s</span>\n' \
              + '<span size="medium">%s</span>'
        self.header.set_markup(tmpl % (html.escape(heading), html.escape(subheading)))
        if episode.has_website_link:
            self._base_uri = episode.link
        else:
            self._base_uri = episode.channel.url
        self._loaded = False

        description_html = episode.description_html
        if description_html:
            self.html_view.load_html(description_html, self._base_uri)
        else:
            self.html_view.load_plain_text(episode.description)

    def on_mouse_over(self, webview, hit_test_result, modifiers):
        if hit_test_result.context_is_link():
            self.set_status(hit_test_result.get_link_uri())
        else:
            self.set_status(None)

    def on_context_menu(self, webview, context_menu, event, hit_test_result):
        whitelist_actions = [
            WebKit2.ContextMenuAction.NO_ACTION,
            WebKit2.ContextMenuAction.STOP,
            WebKit2.ContextMenuAction.RELOAD,
            WebKit2.ContextMenuAction.COPY,
            WebKit2.ContextMenuAction.CUT,
            WebKit2.ContextMenuAction.PASTE,
            WebKit2.ContextMenuAction.DELETE,
            WebKit2.ContextMenuAction.SELECT_ALL,
            WebKit2.ContextMenuAction.INPUT_METHODS,
            WebKit2.ContextMenuAction.COPY_VIDEO_LINK_TO_CLIPBOARD,
            WebKit2.ContextMenuAction.COPY_AUDIO_LINK_TO_CLIPBOARD,
            WebKit2.ContextMenuAction.COPY_LINK_TO_CLIPBOARD,
            WebKit2.ContextMenuAction.COPY_IMAGE_TO_CLIPBOARD,
            WebKit2.ContextMenuAction.COPY_IMAGE_URL_TO_CLIPBOARD
        ]
        items = context_menu.get_items()
        for item in items:
            if item.get_stock_action() not in whitelist_actions:
                context_menu.remove(item)
        if hit_test_result.get_context() == WebKit2.HitTestResultContext.DOCUMENT:
            item = self.create_open_item(
                'shownotes-in-browser',
                _('Open shownotes in web browser'),
                self._base_uri)
            context_menu.insert(item, -1)
        elif hit_test_result.context_is_link():
            item = self.create_open_item(
                'link-in-browser',
                _('Open link in web browser'),
                hit_test_result.get_link_uri())
            context_menu.insert(item, -1)
        return False

    def on_decide_policy(self, webview, decision, decision_type):
        if decision_type == WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION:
            decision.ignore()
            return False
        elif decision_type == WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
            req = decision.get_request()
            # about:blank is for plain text shownotes
            if req.get_uri() in (self._base_uri, 'about:blank'):
                decision.use()
            else:
                logger.debug("refusing to go to %s", req.get_uri())
                decision.ignore()
            return False
        else:
            decision.use()
            return False

    def on_open_in_browser(self, action):
        util.open_website(action.url)

    def create_open_item(self, name, label, url):
        action = Gtk.Action.new(name, label, None, Gtk.STOCK_OPEN)
        action.url = url
        action.connect('activate', self.on_open_in_browser)
        return WebKit2.ContextMenuItem.new(action)

    def set_status(self, text):
        self.status.set_label(text or " ")
