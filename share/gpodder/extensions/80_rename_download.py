# -*- coding: utf-8 -*-
# Rename files after download based on the episode title
# Copyright (c) 2011-04-04 Thomas Perl <thp.io>
# Licensed under the same terms as gPodder itself

import logging
import os

import gpodder
from gpodder import util
from gpodder.model import PodcastEpisode

import gi  # isort:skip
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

logger = logging.getLogger(__name__)

_ = gpodder.gettext
N_ = gpodder.ngettext

__title__ = _('Rename episodes after download')
__description__ = _('Rename episodes to "<Episode Title>.<ext>" on download')
__authors__ = 'Bernd Schlapsi <brot@gmx.info>, Thomas Perl <thp@gpodder.org>'
__doc__ = 'https://gpodder.github.io/docs/extensions/renameafterdownload.html'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/RenameAfterDownload'
__category__ = 'post-download'

DefaultConfig = {
    'add_sortdate': False,  # Add the sortdate as prefix
    'add_podcast_title': False,  # Add the podcast title as prefix
    'sortdate_after_podcast_title': False,  # put the sortdate after podcast title
}


class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.gpodder = None
        self.config = self.container.config

    def on_episode_downloaded(self, episode):
        current_filename = episode.local_filename(create=False)

        new_filename = self.make_filename(current_filename, episode.title,
                                          episode.sortdate, episode.channel.title)

        if new_filename != current_filename:
            logger.info('Renaming: %s -> %s', current_filename, new_filename)
            os.rename(current_filename, new_filename)
            util.rename_episode_file(episode, new_filename)

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            self.gpodder = ui_object

    def on_create_menu(self):
        return [(_("Rename all downloaded episodes"), self.rename_all_downloaded_episodes)]

    def rename_all_downloaded_episodes(self):
        episodes = [e for c in self.gpodder.channels for e in [e for e in c.children if e.state == gpodder.STATE_DOWNLOADED]]
        number_of_episodes = len(episodes)
        if number_of_episodes == 0:
            self.gpodder.show_message(_('No downloaded episodes to rename'),
                _('Rename all downloaded episodes'), important=True)

        from gpodder.gtkui.interface.progress import ProgressIndicator

        progress_indicator = ProgressIndicator(
            _('Renaming all downloaded episodes'),
            '', True, self.gpodder.get_dialog_parent(), number_of_episodes)

        for episode in episodes:
            self.on_episode_downloaded(episode)

            if not progress_indicator.on_tick():
                break
        renamed_count = progress_indicator.tick_counter

        progress_indicator.on_finished()

        if renamed_count > 0:
            self.gpodder.show_message(
                N_('Renamed %(count)d downloaded episode',
                   'Renamed %(count)d downloaded episodes',
                   renamed_count) % {'count': renamed_count},
                _('Rename all downloaded episodes'), important=True)

    def make_filename(self, current_filename, title, sortdate, podcast_title):
        dirname = os.path.dirname(current_filename)
        filename = os.path.basename(current_filename)
        basename, ext = os.path.splitext(filename)

        new_basename = []
        new_basename.append(title)
        if self.config.sortdate_after_podcast_title:
            if self.config.add_sortdate:
                new_basename.insert(0, sortdate)
            if self.config.add_podcast_title:
                new_basename.insert(0, podcast_title)
        else:
            if self.config.add_podcast_title:
                new_basename.insert(0, podcast_title)
            if self.config.add_sortdate:
                new_basename.insert(0, sortdate)
        new_basename = ' - '.join(new_basename)

        # Remove unwanted characters and shorten filename (#494)
        # Also sanitize ext (see #591 where ext=.mp3?dest-id=754182)
        new_basename, ext = util.sanitize_filename_ext(
            new_basename,
            ext,
            PodcastEpisode.MAX_FILENAME_LENGTH,
            PodcastEpisode.MAX_FILENAME_WITH_EXT_LENGTH)
        new_filename = os.path.join(dirname, new_basename + ext)

        if new_filename == current_filename:
            return current_filename

        for filename in util.generate_names(new_filename):
            # Avoid filename collisions
            if not os.path.exists(filename):
                return filename

    def on_add_sortdate_toggled(self, widget):
        self.config.add_sortdate = widget.get_active()

    def on_add_podcast_title_toggled(self, widget):
        self.config.add_podcast_title = widget.get_active()

    def on_sortdate_after_podcast_title_toggled(self, widget):
        self.config.sortdate_after_podcast_title = widget.get_active()

    def show_preferences(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        title = Gtk.Label(use_markup=True, label=_('<b><big>Rename Episodes After Download</big></b>'))
        title.set_halign(Gtk.Align.CENTER)
        box.add(title)

        whatisthis = Gtk.Label(use_markup=True, wrap=True, label=_(
            'This extension renames episode files after download.'
            ' Episodes will be renamed according to \"&lt;Episode Title&gt;.&lt;ext&gt;\", with extra options below.\n\n'
            'The Rename all Downloaded Episodes option in the Extras menu will rename all currently downloaded episodes.'
        ))
        whatisthis.set_property('xalign', 0.0)
        box.add(whatisthis)

        box.pack_start(Gtk.HSeparator(), False, False, 0)

        self.container.add_sortdate_checkbox = Gtk.CheckButton(_('Add Sort Date'))
        self.container.add_sortdate_checkbox.set_active(self.config.add_sortdate)
        self.container.add_sortdate_checkbox.connect('toggled', self.on_add_sortdate_toggled)
        box.pack_start(self.container.add_sortdate_checkbox, False, False, 0)

        self.container.add_podcast_title_checkbox = Gtk.CheckButton(_('Add Podcast Title'))
        self.container.add_podcast_title_checkbox.set_active(self.config.add_podcast_title)
        self.container.add_podcast_title_checkbox.connect('toggled', self.on_add_podcast_title_toggled)
        box.pack_start(self.container.add_podcast_title_checkbox, False, False, 0)

        self.container.sortdate_after_podcast_title_checkbox = Gtk.CheckButton(_('Put Sortdate After Podcast Title'))
        self.container.sortdate_after_podcast_title_checkbox.set_active(self.config.sortdate_after_podcast_title)
        self.container.sortdate_after_podcast_title_checkbox.connect('toggled', self.on_sortdate_after_podcast_title_toggled)
        box.pack_start(self.container.sortdate_after_podcast_title_checkbox, False, False, 0)

        box.show_all()
        return box

    def on_preferences(self):
        return [(_('RenameAfterDownload'), self.show_preferences)]
