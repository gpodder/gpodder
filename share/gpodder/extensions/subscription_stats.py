# -*- coding: utf-8 -*-
# Show publishing statistics for subscriptions.
# Released under the same license terms as gPodder itself.

import time

import gpodder

import gi  # isort:skip
gi.require_version('Gtk', '3.0')  # isort:skip
from gi.repository import Gtk, Pango  # isort:skip

_ = gpodder.gettext

__title__ = _('Subscription Statistics')
__description__ = _('Show publishing statistics for subscriptions.')
__only_for__ = 'gtk'
__authors__ = 'Brand Huntsman <http://qzx.com/mail/>'


class gPodderExtension:
    def __init__(self, container):
        self.container = container

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            self.gpodder = ui_object

    def on_create_menu(self):
        # extras menu
        return [(_("Subscription Statistics"), self.open_dialog)]

    def add_page(self, notebook, type, channels):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        store = Gtk.ListStore(str, str)
        for average, name, paused in channels:
            store.append([
                ('%.1f' % round(average, 1)) if average > 0 else '?',
                name if not paused else (_('%s (paused)') % name)
            ])

        tree = Gtk.TreeView(model=store)
        scrolled.add(tree)

        dayscell = Gtk.CellRendererText()
        dayscell.set_property('xalign', 1)
        dayscell.set_property('alignment', Pango.Alignment.RIGHT)
        dayscolumn = Gtk.TreeViewColumn(_('Days'))
        dayscolumn.pack_start(dayscell, True)
        dayscolumn.add_attribute(dayscell, 'text', 0)
        tree.append_column(dayscolumn)

        channelcell = Gtk.CellRendererText()
        channelcell.set_property('xalign', 0)
        channelcell.set_property('alignment', Pango.Alignment.LEFT)
        channelcolumn = Gtk.TreeViewColumn(_('Podcast'))
        channelcolumn.pack_start(channelcell, True)
        channelcolumn.add_attribute(channelcell, 'text', 1)
        tree.append_column(channelcolumn)

        notebook.append_page(scrolled, Gtk.Label('%d %s' % (len(channels), type)))

    def open_dialog(self):
        db = self.gpodder.db

        # get all channels
        channels = []
        with db.lock:
            cur = db.cursor()
            cur.execute('SELECT id, title, pause_subscription FROM %s' % db.TABLE_PODCAST)
            while True:
                row = cur.fetchone()
                if row is None:
                    break
                channels.append(row)
            cur.close()

        # get average time between episodes per channel
        now = int(time.time())
        nr_paused = 0
        daily = []
        weekly = []
        monthly = []
        yearly = []
        for channel_id, channel_name, paused in channels:
            if paused:
                nr_paused += 1

            total = 0
            nr_episodes = 0
            prev = now
            with db.lock:
                cur = db.cursor()
                cur.execute('SELECT published FROM %s WHERE podcast_id = %d ORDER BY published DESC LIMIT 25'
                    % (db.TABLE_EPISODE, channel_id))
                while True:
                    row = cur.fetchone()
                    if row is None:
                        break
                    total += (prev - row[0])
                    nr_episodes += 1
                    prev = row[0]
                cur.close()

            average = (total / nr_episodes) / 86400 if nr_episodes > 0 else 0

            if average == 0:
                yearly.append([average, channel_name, paused])
            elif average <= 2:
                daily.append([average, channel_name, paused])
            elif average <= 14:
                weekly.append([average, channel_name, paused])
            elif average <= 61:
                monthly.append([average, channel_name, paused])
            else:
                yearly.append([average, channel_name, paused])

        # sort by averages
        daily.sort(key=lambda e: e[0])
        weekly.sort(key=lambda e: e[0])
        monthly.sort(key=lambda e: e[0])
        yearly.sort(key=lambda e: e[0])

        # open dialog
        dlg = Gtk.Dialog(_('Subscription Statistics'), self.gpodder.main_window)
        dlg.set_size_request(400, 400)
        dlg.set_resizable(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        label = Gtk.Label(_('%s subscriptions (%d paused)') % (len(channels), nr_paused))
        box.add(label)

        notebook = Gtk.Notebook()
        notebook.set_vexpand(True)
        self.add_page(notebook, _('daily'), daily)
        self.add_page(notebook, _('weekly'), weekly)
        self.add_page(notebook, _('monthly'), monthly)
        self.add_page(notebook, _('yearly'), yearly)
        box.add(notebook)

        label = Gtk.Label(_('Average days between the last 25 episodes.'))
        label.set_line_wrap(True)
        box.add(label)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        button = Gtk.Button(stock=Gtk.STOCK_CLOSE)
        button.connect('clicked', lambda w: dlg.destroy())
        hbox.pack_end(button, False, False, 0)
        box.add(hbox)

        dlg.vbox.pack_start(box, True, True, 0)
        dlg.vbox.show_all()
        dlg.show()
