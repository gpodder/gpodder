# -*- coding: utf-8 -*-
# Show publishing statistics for subscriptions.
# Released under the same license terms as gPodder itself.

import locale
import time
from time import localtime, strftime

import gpodder
from gpodder import config

import gi  # isort:skip
from gi.repository import Gtk  # isort:skip
gi.require_version('Gtk', '3.0')  # isort:skip

_ = gpodder.gettext

__title__ = _('Subscription Statistics')
__description__ = _('Show publishing statistics for subscriptions.')
__only_for__ = 'gtk'
__doc__ = 'https://gpodder.github.io/docs/extensions/subscription_stats.html'
__authors__ = 'Brand Huntsman <http://qzx.com/mail/> and \
               Nuno Dias <Nuno.Dias+gpodder@gmail.com>'


class gPodderExtension:
    def __init__(self, container):
        self.container = container

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            self.gpodder = ui_object

    def on_create_menu(self):
        # extras menu
        return [(_("Subscription Statistics"), self.open_dialog)]

    def add_page(self, notebook, category, channels):
        scrolled = Gtk.ScrolledWindow()

        store = Gtk.ListStore(str, float, str, str, int)
        for average, name, edate, paused in channels:
            last = strftime('%x', localtime(edate))
            store.append([
                locale.format_string('%.1f', round(average, 1)) if average > 0 else '?',
                average, ('❚❚ ' if paused else '') + name, last, edate,
            ])

        tree = Gtk.TreeView(model=store)
        scrolled.add(tree)

        lastcell = Gtk.CellRendererText()
        lastcolumn = Gtk.TreeViewColumn(_('Updated'))
        lastcolumn.set_sort_column_id(4)
        lastcolumn.pack_end(lastcell, True)
        lastcolumn.add_attribute(lastcell, 'text', 3)
        tree.append_column(lastcolumn)

        dayscell = Gtk.CellRendererText()
        dayscell.set_property('xalign', 1)
        dayscolumn = Gtk.TreeViewColumn(_('Days'))
        dayscolumn.set_sort_column_id(1)
        dayscolumn.pack_start(dayscell, True)
        dayscolumn.add_attribute(dayscell, 'text', 0)
        tree.append_column(dayscolumn)

        channelcell = Gtk.CellRendererText()
        channelcolumn = Gtk.TreeViewColumn(_('Podcast'))
        channelcolumn.set_sort_column_id(2)
        channelcolumn.pack_start(channelcell, True)
        channelcolumn.add_attribute(channelcell, 'text', 2)
        channelcolumn.set_expand(True)
        tree.append_column(channelcolumn)

        notebook.append_page(scrolled,
                             Gtk.Label('%d %s' % (len(channels), category)))

    def open_dialog(self):
        db = self.gpodder.db

        # get all channels
        channels = []
        with db.lock:
            cur = db.cursor()
            cur.execute(
                        'SELECT id, title, pause_subscription FROM %s'
                        % db.TABLE_PODCAST)
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
                cur.execute('SELECT published FROM %s WHERE podcast_id = %d \
                            ORDER BY published DESC LIMIT 25'
                            % (db.TABLE_EPISODE, channel_id))
                while True:
                    row = cur.fetchone()
                    if row is None:
                        break
                    if total == 0:
                        edate = row[0]
                    total += (prev - row[0])
                    nr_episodes += 1
                    prev = row[0]
                cur.close()

            average = (total / nr_episodes) / (24 * 60 * 60) \
                if nr_episodes > 0 else 0

            if average == 0:
                yearly.append([average, channel_name, edate, paused])
            elif average <= 2:
                daily.append([average, channel_name, edate, paused])
            elif average <= 14:
                weekly.append([average, channel_name, edate, paused])
            elif average <= 61:
                monthly.append([average, channel_name, edate, paused])
            else:
                yearly.append([average, channel_name, edate, paused])

        # sort by averages
        daily.sort(key=lambda e: e[0])
        weekly.sort(key=lambda e: e[0])
        monthly.sort(key=lambda e: e[0])
        yearly.sort(key=lambda e: e[0])

        # open dialog
        dlg = Gtk.Dialog(_('Subscription Statistics'),
                         self.gpodder.main_window)
        dlg.set_default_size(420, 600)
        dlg.set_resizable(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_border_width(0)

        label = Gtk.Label(_('%d subscriptions (%d paused)') % (len(channels),
                          nr_paused))
        label.set_padding(0, 10)
        box.add(label)

        notebook = Gtk.Notebook()
        notebook.set_vexpand(True)
        notebook.set_scrollable(True)
        notebook.set_show_border(False)
        self.add_page(notebook, _('daily'), daily)
        self.add_page(notebook, _('weekly'), weekly)
        self.add_page(notebook, _('monthly'), monthly)
        self.add_page(notebook, _('yearly'), yearly)
        box.add(notebook)

        conf = config.Config(gpodder.config_file)
        label = Gtk.Label(_('Average days between the last %d episodes.') %
                          (conf.limit.episodes if conf.limit.episodes < 25
                           else 25))
        label.set_line_wrap(True)
        label.set_padding(0, 5)
        box.add(label)

        button = dlg.add_button(_('_Close'), Gtk.ResponseType.OK)
        button.set_margin_right(5)
        button.set_margin_bottom(5)
        dlg.connect("response", lambda w, r: dlg.destroy())

        dlg.vbox.pack_start(box, True, True, 0)
        dlg.vbox.show_all()
        dlg.show()
