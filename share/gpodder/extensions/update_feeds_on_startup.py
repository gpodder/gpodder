# -*- coding: utf-8 -*-
# Starts episode update search on startup
#
# (c) 2012-10-13 Bernd Schlapsi <brot@gmx.info>
# Released under the same license terms as gPodder itself.

import logging

import gpodder

logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Search for new episodes on startup')
__description__ = _('Starts the search for new episodes on startup')
__authors__ = 'Bernd Schlapsi <brot@gmx.info>'
__doc__ = 'https://gpodder.github.io/docs/extensions/searchepisodeonstartup.html'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/SearchEpisodeOnStartup'
__category__ = 'interface'
__only_for__ = 'gtk'


class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.config = self.container.config
        self.gpodder = None

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            self.gpodder = ui_object

    def on_find_partial_downloads_done(self):
        if self.gpodder:
            self.gpodder.update_feed_cache()
