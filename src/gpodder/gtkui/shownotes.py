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
import datetime
import html
import logging
from urllib.parse import urlparse

import gpodder
from gpodder import util
from gpodder.gtkui.draw import (draw_text_box_centered, get_background_color,
                                get_foreground_color)

# from gpodder.gtkui.draw import investigate_widget_colors

import gi  # isort:skip
gi.require_version('Gdk', '3.0')  # isort:skip
gi.require_version('Gtk', '3.0')  # isort:skip
from gi.repository import Gdk, Gio, GLib, Gtk, Pango  # isort:skip


_ = gpodder.gettext

logger = logging.getLogger(__name__)

has_webkit2 = False
try:
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
        self.details_fmt = _('%(date)s | %(size)s | %(duration)s')

        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_shadow_type(Gtk.ShadowType.IN)
        self.scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.add(self.init())

        self.status = Gtk.Label.new()
        self.status.set_halign(Gtk.Align.START)
        self.status.set_valign(Gtk.Align.END)
        self.status.set_property('ellipsize', Pango.EllipsizeMode.END)
        self.set_status(None)
        self.status_bg = None
        self.color_set = False
        self.background_color = None
        self.foreground_color = None
        self.link_color = None
        self.visited_color = None

        self.overlay = Gtk.Overlay()
        self.overlay.add(self.scrolled_window)
        # need an EventBox for an opaque background behind the label
        box = Gtk.EventBox()
        self.status_bg = box
        box.add(self.status)
        box.set_hexpand(False)
        box.set_vexpand(False)
        box.set_valign(Gtk.Align.END)
        box.set_halign(Gtk.Align.START)
        self.overlay.add_overlay(box)
        self.overlay.set_overlay_pass_through(box, True)

        self.main_component = self.overlay
        self.main_component.show_all()

        self.da_message = Gtk.DrawingArea()
        self.da_message.set_property('expand', True)
        self.da_message.connect('draw', self.on_shownotes_message_expose_event)
        self.shownotes_pane.add(self.da_message)
        self.shownotes_pane.add(self.main_component)

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
                self.update(episode)
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
        background = get_background_color()
        if background is None:
            background = Gdk.RGBA(1, 1, 1, 1)
        ctx.set_source_rgba(background.red, background.green, background.blue, 1)
        x1, y1, x2, y2 = ctx.clip_extents()
        ctx.rectangle(x1, y1, x2 - x1, y2 - y1)
        ctx.fill()

        width, height = drawingarea.get_allocated_width(), drawingarea.get_allocated_height(),
        text = _('Please select an episode')
        draw_text_box_centered(ctx, drawingarea, width, height, text, None, None)
        return False

    def set_status(self, text):
        self.status.set_label(text or " ")

    def define_colors(self):
        if not self.color_set:
            self.color_set = True
            # investigate_widget_colors([
            #     ([(Gtk.Window, 'background', '')], self.status.get_toplevel()),
            #     ([(Gtk.Window, 'background', ''), (Gtk.Label, '', '')], self.status),
            #     ([(Gtk.Window, 'background', ''), (Gtk.TextView, 'view', '')], self.text_view),
            #     ([(Gtk.Window, 'background', ''), (Gtk.TextView, 'view', 'text')], self.text_view),
            # ])
            dummy_tv = Gtk.TextView()
            self.background_color = get_background_color(Gtk.StateFlags.NORMAL,
                widget=dummy_tv) or Gdk.RGBA()
            self.foreground_color = get_foreground_color(Gtk.StateFlags.NORMAL,
                widget=dummy_tv) or Gdk.RGBA(0, 0, 0)
            self.link_color = get_foreground_color(state=Gtk.StateFlags.LINK,
                widget=dummy_tv) or Gdk.RGBA(0, 0, 0)
            self.visited_color = get_foreground_color(state=Gtk.StateFlags.VISITED,
                widget=dummy_tv) or self.link_color
            del dummy_tv

            self.status_bg.override_background_color(Gtk.StateFlags.NORMAL, self.background_color)
            if hasattr(self, "text_buffer"):
                self.text_buffer.create_tag('hyperlink',
                    foreground=self.link_color.to_string(),
                    underline=Pango.Underline.SINGLE)


class gPodderShownotesText(gPodderShownotes):
    def init(self):
        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_border_width(10)
        self.text_view.set_editable(False)
        self.text_buffer = Gtk.TextBuffer()
        self.text_buffer.create_tag('heading', scale=1.2, weight=Pango.Weight.BOLD)
        self.text_buffer.create_tag('subheading', scale=1.0)
        self.text_buffer.create_tag('details', scale=0.9)
        self.text_view.set_buffer(self.text_buffer)
        self.text_view.set_property('expand', True)
        self.text_view.connect('button-release-event', self.on_button_release)
        self.text_view.connect('key-press-event', self.on_key_press)
        self.text_view.connect('motion-notify-event', self.on_hover_hyperlink)
        self.populate_popup_id = None
        return self.text_view

    def update(self, episode):
        self.scrolled_window.get_vadjustment().set_value(0)

        heading = episode.title
        subheading = _('from %s') % (episode.channel.title)
        details = self.details_fmt % {
            'date': '{} {}'.format(datetime.datetime.fromtimestamp(episode.published).strftime('%H:%M'),
                util.format_date(episode.published)),
            'size': util.format_filesize(episode.file_size, digits=1)
            if episode.file_size > 0 else "-",
            'duration': episode.get_play_info_string()}
        self.define_colors()
        hyperlinks = [(0, None)]
        self.text_buffer.set_text('')
        if episode.link:
            hyperlinks.append((self.text_buffer.get_char_count(), episode.link))
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(), heading, 'heading')
        if episode.link:
            hyperlinks.append((self.text_buffer.get_char_count(), None))
        self.text_buffer.insert_at_cursor('\n')
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(), subheading, 'subheading')
        self.text_buffer.insert_at_cursor('\n')
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(), details, 'details')
        self.text_buffer.insert_at_cursor('\n\n')
        for target, text in util.extract_hyperlinked_text(episode.html_description()):
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

        if self.populate_popup_id is not None:
            self.text_view.disconnect(self.populate_popup_id)
        self.populate_popup_id = self.text_view.connect('populate-popup', self.on_populate_popup)
        self.episode = episode

    def on_populate_popup(self, textview, context_menu):
        # TODO: Remove items from context menu that are always insensitive in a read-only buffer

        if self.episode.link:
            # TODO: It is currently not possible to copy links in description.
            # Detect if context menu was opened on a hyperlink and add
            # "Open Link" and "Copy Link Address" menu items.
            # See https://github.com/gpodder/gpodder/issues/1097

            item = Gtk.SeparatorMenuItem()
            item.show()
            context_menu.append(item)
            # label links can be opened from context menu or by clicking them, do the same here
            item = Gtk.MenuItem(label=_('Open Episode Title Link'))
            item.connect('activate', lambda i: util.open_website(self.episode.link))
            item.show()
            context_menu.append(item)
            # hack to allow copying episode.link
            item = Gtk.MenuItem(label=_('Copy Episode Title Link Address'))
            item.connect('activate', lambda i: util.copy_text_to_clipboard(self.episode.link))
            item.show()
            context_menu.append(item)

    def on_button_release(self, widget, event):
        if event.button == 1:
            self.activate_links()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Return:
            self.activate_links()
            return True

        return False

    def hyperlink_at_pos(self, pos):
        """
        :param int pos: offset in text buffer
        :return str: hyperlink target at pos if any or None
        """
        return next((url for start, end, url in self.hyperlinks if start < pos < end), None)

    def activate_links(self):
        if self.text_buffer.get_selection_bounds() == ():
            pos = self.text_buffer.props.cursor_position
            target = self.hyperlink_at_pos(pos)
            if target is not None:
                util.open_website(target)

    def on_hover_hyperlink(self, textview, e):
        x, y = textview.window_to_buffer_coords(Gtk.TextWindowType.TEXT, e.x, e.y)
        w = self.text_view.get_window(Gtk.TextWindowType.TEXT)
        success, it = textview.get_iter_at_location(x, y)
        if success:
            pos = it.get_offset()
            target = self.hyperlink_at_pos(pos)
            if target:
                self.set_status(target)
                w.set_cursor(Gdk.Cursor.new_from_name(w.get_display(), 'pointer'))
                return
        self.set_status('')
        w.set_cursor(None)


class gPodderShownotesHTML(gPodderShownotes):
    def init(self):
        self.episode = None
        self._base_uri = None
        # basic restrictions
        self.stylesheet = None
        self.manager = WebKit2.UserContentManager()
        self.html_view = WebKit2.WebView.new_with_user_content_manager(self.manager)
        settings = self.html_view.get_settings()
        settings.set_enable_java(False)
        settings.set_enable_plugins(False)
        settings.set_enable_javascript(False)
        # uncomment to show web inspector
        # settings.set_enable_developer_extras(True)
        self.html_view.set_property('expand', True)
        self.html_view.connect('mouse-target-changed', self.on_mouse_over)
        self.html_view.connect('context-menu', self.on_context_menu)
        self.html_view.connect('decide-policy', self.on_decide_policy)
        self.html_view.connect('authenticate', self.on_authenticate)

        return self.html_view

    def update(self, episode):
        self.scrolled_window.get_vadjustment().set_value(0)

        self.define_colors()

        if episode.has_website_link():
            self._base_uri = episode.link
        else:
            self._base_uri = episode.channel.url

        # for incomplete base URI (e.g. http://919.noagendanotes.com)
        baseURI = urlparse(self._base_uri)
        if baseURI.path == '':
            self._base_uri += '/'
        self._loaded = False

        stylesheet = self.get_stylesheet()
        if stylesheet:
            self.manager.add_style_sheet(stylesheet)
        heading = '<h3>%s</h3>' % html.escape(episode.title)
        subheading = _('from %s') % html.escape(episode.channel.title)
        details = '<small>%s</small>' % html.escape(self.details_fmt % {
            'date': '{} {}'.format(datetime.datetime.fromtimestamp(episode.published).strftime('%H:%M'),
                util.format_date(episode.published)),
            'size': util.format_filesize(episode.file_size, digits=1)
            if episode.file_size > 0 else "-",
            'duration': episode.get_play_info_string()})
        header_html = _('<div id="gpodder-title">\n%(heading)s\n<p>%(subheading)s</p>\n<p>%(details)s</p></div>\n') \
            % dict(heading=heading, subheading=subheading, details=details)
        # uncomment to prevent background override in html shownotes
        # self.manager.remove_all_style_sheets ()
        logger.debug("base uri: %s (chan:%s)", self._base_uri, episode.channel.url)
        self.html_view.load_html(header_html + episode.html_description(), self._base_uri)
        # uncomment to show web inspector
        # self.html_view.get_inspector().show()
        self.episode = episode

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
                # Avoid opening the page inside the WebView and open in the browser instead
                decision.ignore()
                util.open_website(req.get_uri())
            return False
        else:
            decision.use()
            return False

    def on_open_in_browser(self, action, var):
        util.open_website(var.get_string())

    def on_authenticate(self, view, request):
        if request.is_retry():
            return False
        if not self.episode or not self.episode.channel.auth_username:
            return False
        chan = self.episode.channel
        u = urlparse(chan.url)
        host = u.hostname
        if u.port:
            port = u.port
        elif u.scheme == 'https':
            port = 443
        else:
            port = 80
        logger.debug("on_authenticate(chan=%s:%s req=%s:%s (scheme=%s))",
                     host, port, request.get_host(), request.get_port(),
                     request.get_scheme())
        if host == request.get_host() and port == request.get_port() \
                and request.get_scheme() == WebKit2.AuthenticationScheme.HTTP_BASIC:
            persistence = WebKit2.CredentialPersistence.FOR_SESSION
            request.authenticate(WebKit2.Credential(chan.auth_username,
                                                    chan.auth_password,
                                                    persistence))
            return True
        else:
            return False

    def create_open_item(self, name, label, url):
        action = Gio.SimpleAction.new(name, GLib.VariantType.new('s'))
        action.connect('activate', self.on_open_in_browser)
        var = GLib.Variant.new_string(url)
        return WebKit2.ContextMenuItem.new_from_gaction(action, label, var)

    def get_stylesheet(self):
        if self.stylesheet is None:
            style = ("html { background: %s; color: %s;}"
                     " a { color: %s; }"
                     " a:visited { color: %s; }"
                     " #gpodder-title h3, #gpodder-title p { margin: 0}"
                     " #gpodder-title {margin-block-end: 1em;}") % \
                     (self.background_color.to_string(), self.foreground_color.to_string(),
                      self.link_color.to_string(), self.visited_color.to_string())
            self.stylesheet = WebKit2.UserStyleSheet(style, 0, 1, None, None)
        return self.stylesheet
