# -*- coding: utf-8 -*-
# Add a context menu to show the episode/podcast website (bug 1958)
# (c) 2014-10-20 Thomas Perl <thp.io/about>
# Released under the same license terms as gPodder itself.

import logging

import gpodder
from gpodder import util

logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('"Open website" episode and podcast context menu')
__description__ = _('Add a context menu item for opening the website of an episode or podcast')
__authors__ = 'Thomas Perl <thp@gpodder.org>'
__category__ = 'interface'
__only_for__ = 'gtk'


class gPodderExtension:
    def __init__(self, container):
        self.container = container

    def has_website(self, episodes):
        for episode in episodes:
            if episode.link:
                return True

    def open_website(self, episodes):
        for episode in episodes:
            if episode.link:
                util.open_website(episode.link)

    def open_channel_website(self, channel):
        util.open_website(channel.link)

    def on_episodes_context_menu(self, episodes):
        return [(_('Open website'), self.open_website if self.has_website(episodes) else None)]

    def on_channel_context_menu(self, channel):
        return [(_('Open website'), self.open_channel_website if channel.link else None)]
