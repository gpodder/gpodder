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

__title__ = _('Rename after download')
__description__ = _('rename files after download based on the episode title')
__author__ = 'Bernd Schlapsi <brot@gmx.info>'


class gPodderExtension:
    def __init__(self, container):
        self.container = container

    def on_load(self):
        logger.info('Extension "%s" is being loaded.' % __title__)

    def on_unload(self):
        logger.info('Extension "%s" is being unloaded.' % __title__)

    def on_episode_downloaded(self, episode):
        current_filename = episode.local_filename(create=False)

        new_filename = self.rename_file(current_filename, episode.title)
        logger.info('Renaming %s -> %s:', current_filename, new_filename)

        os.rename(current_filename, new_filename)
        util.rename_episode_file(episode, new_filename)

    def rename_file(self, current_filename, title):
        dirname = os.path.dirname(current_filename)
        filename = os.path.basename(current_filename)
        basename, ext = os.path.splitext(filename)

        new_filename = util.sanitize_encoding(title) + ext
        return os.path.join(dirname, new_filename)
