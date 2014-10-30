# -*- coding: utf-8 -*-
# Add a context menu to show the episode website (bug 1958)
# (c) 2014-10-20 Thomas Perl <thp.io/about>
# Released under the same license terms as gPodder itself.

import gpodder
from gpodder import util

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('"Open website" episode context menu')
__description__ = _('Add a context menu item for opening the website of an episode')
__authors__ = 'Thomas Perl <thp@gpodder.org>'
__category__ = 'interface'
__only_for__ = 'gtk'


class gPodderExtension:
    def __init__(self, container):
        self.container = container

    def open_website(self, episodes):
        for episode in episodes:
            util.open_website(episode.link)

    def on_episodes_context_menu(self, episodes):
        return [(_('Open website'), self.open_website)]
