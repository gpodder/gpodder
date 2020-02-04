# -*- coding: utf-8 -*-
# Disable automatic downloads based on episode title.
# Released under the same license terms as gPodder itself.

import re

from gi.repository import Gtk

import gpodder

_ = gpodder.gettext

__title__ = _('Filter Episodes')
__description__ = _('Disable automatic downloads based on episode title.')
__only_for__ = 'gtk'
__authors__ = 'Brand Huntsman <http://qzx.com/mail/>'

DefaultConfig = {
    'filters': []
}


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
        #    self.allow_frame           = allow frame widget
        #    self.allow_entry           = allow text widget
        #    self.allow_checkbox_re     = allow RE checkbox widget
        #    self.allow_checkbox_ic     = allow IC checkbox widget
        #    self.block_checkbox        = block checkbox widget
        #    self.block_entry           = block text widget
        #    self.block_checkbox_re     = block RE checkbox widget
        #    self.block_checkbox_ic     = block IC checkbox widget

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
        allow = self.key('allow')
        block = self.key('block')

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        # allow widgets
        self.allow_frame = Gtk.Frame()
        self.allow_frame.set_label(_('Allow'))
        if self.f is None:
            self.allow_frame.set_sensitive(False)
        box.add(self.allow_frame)
        frame_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.allow_frame.add(frame_vbox)
        # checkbox and text entry
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_border_width(5)
        frame_vbox.add(hbox)
        checkbox = Gtk.CheckButton()
        checkbox.set_active(allow is not False)
        checkbox.connect('toggled', self.toggle_allow)
        hbox.pack_start(checkbox, False, False, 3)
        self.allow_entry = Gtk.Entry()
        if allow is not False:
            self.allow_entry.set_text(allow)
        else:
            self.allow_entry.set_sensitive(False)
            self.allow_entry.set_editable(False)
        self.allow_entry.connect('changed', self.change_allow)
        hbox.pack_start(self.allow_entry, True, True, 5)
        # lower hbox
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_border_width(5)
        frame_vbox.add(hbox)
        # regular expression checkbox
        self.allow_checkbox_re = Gtk.CheckButton(_('Regular Expression'))
        if allow is False:
            self.allow_checkbox_re.set_sensitive(False)
        else:
            self.allow_checkbox_re.set_active(self.key('allow_re') is not False)
        self.allow_checkbox_re.connect('toggled', self.toggle_allow_re)
        hbox.pack_end(self.allow_checkbox_re, False, False, 10)
        # ignore case checkbox
        self.allow_checkbox_ic = Gtk.CheckButton(_('Ignore Case'))
        if allow is False:
            self.allow_checkbox_ic.set_sensitive(False)
        else:
            self.allow_checkbox_ic.set_active(self.key('allow_ic') is not False)
        self.allow_checkbox_ic.connect('toggled', self.toggle_allow_ic)
        hbox.pack_end(self.allow_checkbox_ic, False, False, 10)

        # block widgets
        frame = Gtk.Frame()
        frame.set_label(_('Block'))
        box.add(frame)
        frame_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        frame.add(frame_vbox)
        # checkbox and text entry
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_border_width(5)
        frame_vbox.add(hbox)
        self.block_checkbox = Gtk.CheckButton()
        self.block_checkbox.set_active(block is not False)
        self.block_checkbox.set_sensitive(allow is False)
        self.block_checkbox.connect('toggled', self.toggle_block)
        hbox.pack_start(self.block_checkbox, False, False, 3)
        self.block_entry = Gtk.Entry()
        if block is not False:
            self.block_entry.set_text(block)
        else:
            self.block_entry.set_sensitive(False)
            self.block_entry.set_editable(False)
        self.block_entry.connect('changed', self.change_block)
        hbox.pack_start(self.block_entry, True, True, 5)
        # lower hbox
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_border_width(5)
        frame_vbox.add(hbox)
        # regular expression checkbox
        self.block_checkbox_re = Gtk.CheckButton(_('Regular Expression'))
        if block is False:
            self.block_checkbox_re.set_sensitive(False)
        else:
            self.block_checkbox_re.set_active(self.key('block_re') is not False)
        self.block_checkbox_re.connect('toggled', self.toggle_block_re)
        hbox.pack_end(self.block_checkbox_re, False, False, 10)
        # ignore case checkbox
        self.block_checkbox_ic = Gtk.CheckButton(_('Ignore Case'))
        if block is False:
            self.block_checkbox_ic.set_sensitive(False)
        else:
            self.block_checkbox_ic.set_active(self.key('block_ic') is not False)
        self.block_checkbox_ic.connect('toggled', self.toggle_block_ic)
        hbox.pack_end(self.block_checkbox_ic, False, False, 10)

        # help
        label = Gtk.Label(_(
            'Clicking the block checkbox and leaving it empty will disable auto-download for all episodes in this channel.'
            '  The patterns match partial text in episode title, and an empty pattern matches any title.'
            '  The allow pattern unblocks blocked episodes (to block all then unblock some).'))
        label.set_line_wrap(True)
        box.add(label)

        # re-filter
        button = Gtk.Button(_('Filter episodes now (undoes any episodes you marked as old)'))
        button.connect('clicked', self.refilter_podcast)
        box.add(button)

        box.show_all()
        return box

    def toggle_allow(self, widget):
        self.toggle(widget.get_active(), 'allow', self.allow_entry, self.allow_checkbox_re, self.allow_checkbox_ic)

    def toggle_block(self, widget):
        self.toggle(widget.get_active(), 'block', self.block_entry, self.block_checkbox_re, self.block_checkbox_ic)

    def change_allow(self, widget):
        self.change(self.allow_entry, 'allow')

    def change_block(self, widget):
        self.change(self.block_entry, 'block')

    def toggle_allow_re(self, widget):
        self.toggle_re(widget.get_active(), 'allow_re')

    def toggle_block_re(self, widget):
        self.toggle_re(widget.get_active(), 'block_re')

    def toggle_allow_ic(self, widget):
        self.toggle_ic(widget.get_active(), 'allow_ic')

    def toggle_block_ic(self, widget):
        self.toggle_ic(widget.get_active(), 'block_ic')

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

    # update filter when toggling allow/block checkbox
    def toggle(self, enabled, field, entry, checkbox_re, checkbox_ic):
        if enabled:
            if self.f is None:
                self.f = {'url': self.url}
                self.filters.append(self.f)
            self.f[field] = ''

            # enable text and RE/IC checkboxes
            entry.set_sensitive(True)
            entry.set_editable(True)
            checkbox_re.set_sensitive(True)
            checkbox_ic.set_sensitive(True)
        else:
            # clear and disable text and RE/IC checkboxes
            entry.set_sensitive(False)
            entry.set_text('')
            entry.set_editable(False)
            checkbox_re.set_active(False)
            checkbox_re.set_sensitive(False)
            checkbox_ic.set_active(False)
            checkbox_ic.set_sensitive(False)

            if self.f is not None:
                self.f.pop(field + '_ic', None)
                self.f.pop(field + '_re', None)
                self.f.pop(field, None)
                if len(self.f.keys()) == 1:
                    self.filters.remove(self.f)
                    self.f = None

        if field == 'allow':
            # disable block checkbox when allow is checked
            self.block_checkbox.set_sensitive(self.f is None or self.key('allow') is False)
        if field == 'block':
            # enable all allow widgets only when block is checked
            self.allow_frame.set_sensitive(self.f is not None)

        # save config
        self.core.config.schedule_save()

    # update filter when toggling allow/block RE checkbox
    def toggle_re(self, enabled, field):
        if self.f is not None:
            if enabled:
                self.f[field] = True
            else:
                self.f.pop(field, None)

            # save config
            self.core.config.schedule_save()

    # update filter when toggling allow/block IC checkbox
    def toggle_ic(self, enabled, field):
        if self.f is not None:
            if enabled:
                self.f[field] = True
            else:
                self.f.pop(field, None)

            # save config
            self.core.config.schedule_save()

    # update filter when changing allow/block text
    def change(self, entry, field):
        if self.f is not None:
            self.f[field] = entry.get_text()

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
            allow = f.get('allow', False)
            block = f.get('block', False)
            allow_ic = True if allow is not False and f.get('allow_ic', False) else False
            block_ic = True if block is not False and f.get('block_ic', False) else False
            allow_re = re.compile(allow, re.IGNORECASE if allow_ic else False) if allow is not False and f.get('allow_re', False) else False
            block_re = re.compile(block, re.IGNORECASE if block_ic else False) if block is not False and f.get('block_re', False) else False
        else:
            allow = False
            block = False

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
