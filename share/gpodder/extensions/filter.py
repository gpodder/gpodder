# -*- coding: utf-8 -*-
# Disable automatic downloads based on episode title.
# Released under the same license terms as gPodder itself.

import re

import gpodder

import gi  # isort:skip
gi.require_version('Gtk', '3.0')  # isort:skip
from gi.repository import Gtk  # isort:skip

_ = gpodder.gettext

__title__ = _('Filter Episodes')
__description__ = _('Disable automatic downloads based on episode title.')
__only_for__ = 'gtk, cli'
__authors__ = 'Brand Huntsman <http://qzx.com/mail/>'
__doc__ = 'https://gpodder.github.io/docs/extensions/filter.html'

DefaultConfig = {
    'filters': []
}


class BlockExceptFrame:
    """
    Utility class to manage a Block or Except frame, with sub-widgets:
     - Creation as well as internal UI change is handled;
     - Changes to the other widget and to the model have to be handled outside.
    It's less optimized than mapping each widget to a different signal handler,
    but makes shorter code.
    """
    def __init__(self, value, enable_re, enable_ic, on_change_cb):
        self.on_change_cb = on_change_cb
        self.frame = Gtk.Frame()
        frame_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.frame.add(frame_vbox)
        # checkbox and text entry
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_border_width(5)
        frame_vbox.add(hbox)
        self.checkbox = Gtk.CheckButton()
        self.checkbox.set_active(value is not False)
        hbox.pack_start(self.checkbox, False, False, 3)
        self.entry = Gtk.Entry()
        hbox.pack_start(self.entry, True, True, 5)
        # lower hbox
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_border_width(5)
        frame_vbox.add(hbox)
        # regular expression checkbox
        self.checkbox_re = Gtk.CheckButton(_('Regular Expression'))
        hbox.pack_end(self.checkbox_re, False, False, 10)
        # ignore case checkbox
        self.checkbox_ic = Gtk.CheckButton(_('Ignore Case'))
        hbox.pack_end(self.checkbox_ic, False, False, 10)

        if value is False:
            self.entry.set_sensitive(False)
            self.entry.set_editable(False)
            self.checkbox_re.set_sensitive(False)
            self.checkbox_ic.set_sensitive(False)
        else:
            self.entry.set_text(value)
            self.checkbox_re.set_active(enable_re)
            self.checkbox_ic.set_active(enable_ic)

        self.checkbox.connect('toggled', self.toggle_active)
        self.entry.connect('changed', self.emit_change)
        self.checkbox_re.connect('toggled', self.emit_change)
        self.checkbox_ic.connect('toggled', self.emit_change)

    def toggle_active(self, widget):
        enabled = widget.get_active()
        if enabled:
            # enable text and RE/IC checkboxes
            self.entry.set_sensitive(True)
            self.entry.set_editable(True)
            self.checkbox_re.set_sensitive(True)
            self.checkbox_ic.set_sensitive(True)
        else:
            # clear and disable text and RE/IC checkboxes
            self.entry.set_sensitive(False)
            self.entry.set_text('')
            self.entry.set_editable(False)
            self.checkbox_re.set_active(False)
            self.checkbox_re.set_sensitive(False)
            self.checkbox_ic.set_active(False)
            self.checkbox_ic.set_sensitive(False)
        self.emit_change(widget)

    def emit_change(self, widget):
        del widget
        if self.on_change_cb:
            self.on_change_cb(active=self.checkbox.get_active(),
                              text=self.entry.get_text(),
                              regexp=self.checkbox_re.get_active(),
                              ignore_case=self.checkbox_ic.get_active())


class gPodderExtension:
    def __init__(self, container):
        self.core = container.manager.core  # gpodder core
        self.filters = container.config.filters  # all filters

        # the following are only valid when podcast channel settings dialog is open
        #    self.gpodder               = gPodder
        #    self.ui_object             = gPodderChannel
        #    self.channel               = PodcastChannel
        #    self.url                   = current filter url
        #    self.f                     = current filter
        #    self.block_widget          = block BlockExceptFrame
        #    self.allow_widget          = allow BlockExceptFrame

    def on_ui_object_available(self, name, ui_object):
        if name == 'channel-gtk':
            # to close channel settings dialog after re-filtering
            self.ui_object = ui_object
        elif name == 'gpodder-gtk':
            # to update episode list after re-filtering
            self.gpodder = ui_object

    # add filter tab to podcast channel settings dialog
    def on_channel_settings(self, channel):
        return [(_('Filter'), self.show_channel_settings_tab)]

    def show_channel_settings_tab(self, channel):
        self.channel = channel
        self.url = channel.url
        self.f = self.find_filter(self.url)
        block = self.key('block')
        allow = self.key('allow')

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        # note about Cancel
        note = Gtk.Label(use_markup=True, wrap=True, label=_(
            '<b>Note:</b> The Cancel button does <b>not</b> return the '
            'filter settings to the values they had before. '
            'The changes are saved immediately after they are made.'))
        box.add(note)

        # block widgets
        self.block_widget = BlockExceptFrame(value=block,
                                             enable_re=self.key('block_re') is not False,
                                             enable_ic=self.key('block_ic') is not False,
                                             on_change_cb=self.on_block_changed)
        self.block_widget.frame.set_label(_('Block'))
        box.add(self.block_widget.frame)
        self.block_widget.checkbox.set_sensitive(allow is False)

        # allow widgets
        self.allow_widget = BlockExceptFrame(value=allow,
                                             enable_re=self.key('allow_re') is not False,
                                             enable_ic=self.key('allow_ic') is not False,
                                             on_change_cb=self.on_allow_changed)
        self.allow_widget.frame.set_label(_('Except'))
        box.add(self.allow_widget.frame)
        if self.f is None:
            self.allow_widget.frame.set_sensitive(False)

        # help
        label = Gtk.Label(_(
            'Clicking the block checkbox and leaving it empty will disable auto-download for all episodes in this channel.'
            '  The patterns match partial text in episode title, and an empty pattern matches any title.'
            '  The except pattern unblocks blocked episodes (to block all then unblock some).'))
        label.set_line_wrap(True)
        box.add(label)

        # re-filter
        separator = Gtk.HSeparator()
        box.add(separator)
        button = Gtk.Button(_('Filter episodes now'))
        button.connect('clicked', self.refilter_podcast)
        box.add(button)

        label2 = Gtk.Label(_('Undoes any episodes you marked as old.'))
        box.add(label2)

        box.show_all()
        return box

    # return filter for a given podcast channel url
    def find_filter(self, url):
        for f in self.filters:
            if f['url'] == url:
                return f
        return None

    # return value for a given key in current filter
    def key(self, key):
        if self.f is None:
            return False
        return self.f.get(key, False)

    def on_block_changed(self, active, text, regexp, ignore_case):
        self.on_changed('block', active, text, regexp, ignore_case)
        self.allow_widget.frame.set_sensitive(self.f is not None)

    def on_allow_changed(self, active, text, regexp, ignore_case):
        self.on_changed('allow', active, text, regexp, ignore_case)
        self.block_widget.checkbox.set_sensitive(self.f is None or self.key('allow') is False)

    # update filter when toggling block/allow checkbox
    def on_changed(self, field, enabled, text, regexp, ignore_case):
        if enabled:
            if self.f is None:
                self.f = {'url': self.url}
                self.filters.append(self.f)
                self.filters.sort(key=lambda e: e['url'])
            self.f[field] = text
            if regexp:
                self.f[field + '_re'] = True
            else:
                self.f.pop(field + '_re', None)
            if ignore_case:
                self.f[field + '_ic'] = True
            else:
                self.f.pop(field + '_ic', None)
        else:
            if self.f is not None:
                self.f.pop(field + '_ic', None)
                self.f.pop(field + '_re', None)
                self.f.pop(field, None)
                if len(self.f.keys()) == 1:
                    self.filters.remove(self.f)
                    self.f = None
        # save config
        self.core.config.schedule_save()

    # remove filter when podcast channel is removed
    def on_podcast_delete(self, podcast):
        f = self.find_filter(podcast.url)
        if f is not None:
            self.filters.remove(f)

            # save config
            self.core.config.schedule_save()

    # mark new episodes as old to disable automatic download when they match a block filter
    def on_podcast_updated(self, podcast):
        self.filter_podcast(podcast, False)

    # re-filter episodes after changing filters
    def refilter_podcast(self, widget):
        if self.filter_podcast(self.channel, True):
            self.channel.db.commit()
            self.gpodder.update_episode_list_model()
        self.ui_object.main_window.destroy()

    # compare filter pattern to episode title
    def compare(self, title, pattern, regexp, ignore_case):
        if regexp is not False:
            return regexp.search(title)
        elif ignore_case:
            return (pattern.casefold() in title.casefold())
        else:
            return (pattern in title)

    # filter episodes that aren't downloaded or deleted
    def filter_podcast(self, podcast, mark_new):
        f = self.find_filter(podcast.url)
        if f is not None:
            block = f.get('block', False)
            allow = f.get('allow', False)
            block_ic = True if block is not False and f.get('block_ic', False) else False
            allow_ic = True if allow is not False and f.get('allow_ic', False) else False
            block_re = re.compile(block, re.IGNORECASE if block_ic else False) if block is not False and f.get('block_re', False) else False
            allow_re = re.compile(allow, re.IGNORECASE if allow_ic else False) if allow is not False and f.get('allow_re', False) else False
        else:
            block = False
            allow = False

        changes = False
        for e in podcast.get_episodes(gpodder.STATE_NORMAL):
            if allow is not False and self.compare(e.title, allow, allow_re, allow_ic):
                # allow episode
                if mark_new and not e.is_new:
                    e.mark_new()
                    changes = True
                continue
            if block is not False and self.compare(e.title, block, block_re, block_ic):
                # block episode - mark as old to disable automatic download
                if e.is_new:
                    e.mark_old()
                    changes = True
                continue
            if mark_new and not e.is_new:
                e.mark_new()
                changes = True
        return changes
