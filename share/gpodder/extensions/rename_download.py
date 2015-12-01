# -*- coding: utf-8 -*-
# Rename files after download based on the episode title
# Copyright (c) 2011-04-04 Thomas Perl <thp.io>
# Licensed under the same terms as gPodder itself

import os

import gpodder
from gpodder import util

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Rename episodes after download')
__description__ = _('Rename episodes to "<Episode Title>.<ext>" on download')
__authors__ = 'Bernd Schlapsi <brot@gmx.info>, Thomas Perl <thp@gpodder.org>'
__doc__ = 'http://wiki.gpodder.org/wiki/Extensions/RenameAfterDownload'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/RenameAfterDownload'
__category__ = 'post-download'

DefaultConfig = {
    'add_sortdate': False, # Add the sortdate as prefix
    'add_podcast_title': False, # Add the podcast title as prefix
}


class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.config = self.container.config

    def on_episode_downloaded(self, episode):
        current_filename = episode.local_filename(create=False)

        new_filename = self.make_filename(current_filename, episode.title,
                                          episode.sortdate, episode.channel.title)

        if new_filename != current_filename:
            logger.info('Renaming: %s -> %s', current_filename, new_filename)
            os.rename(current_filename, new_filename)
            util.rename_episode_file(episode, new_filename)

    def make_filename(self, current_filename, title, sortdate, podcast_title):
        dirname = os.path.dirname(current_filename)
        filename = os.path.basename(current_filename)
        basename, ext = os.path.splitext(filename)

        new_basename = []
        new_basename.append(util.sanitize_encoding(title) + ext)
        if self.config.add_podcast_title:
            new_basename.insert(0, podcast_title)
        if self.config.add_sortdate:
            new_basename.insert(0, sortdate)
        new_basename = ' - '.join(new_basename)

        # On Windows, force ASCII encoding for filenames (bug 1724)
        new_basename = util.sanitize_filename(new_basename,
                use_ascii=gpodder.ui.win32)
        new_filename = os.path.join(dirname, new_basename)

        if new_filename == current_filename:
            return current_filename

        for filename in util.generate_names(new_filename):
            # Avoid filename collisions
            if not os.path.exists(filename):
                return filename

