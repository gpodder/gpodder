#!/usr/bin/python
# -*- coding: utf-8 -*-
####
# 01/2011 Bernd Schlapsi <brot@gmx.info>
#
# This script is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Dependencies:
# * python-mutagen (Mutagen is a Python module to handle audio metadata)
#
# This extension scripts removes coverart from all downloaded ogg files.
# The reason for this script is that my media player (MEIZU SL6)
# couldn't handle ogg files with included coverart

import os

import gpodder

import logging
logger = logging.getLogger(__name__)

from mutagen.oggvorbis import OggVorbis

_ = gpodder.gettext

__title__ = _('Remove cover art from OGG files')
__description__ = _('removes coverart from all downloaded ogg files')
__authors__ = 'Bernd Schlapsi <brot@gmx.info>'
__doc__ = 'http://wiki.gpodder.org/wiki/Extensions/RemoveOGGCover'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/RemoveOGGCover'
__category__ = 'post-download'


DefaultConfig = {
    'context_menu': True, # Show item in context menu
}


class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.config = self.container.config

    def on_episode_downloaded(self, episode):
        self.rm_ogg_cover(episode)

    def on_episodes_context_menu(self, episodes):
        if not self.config.context_menu:
            return None

        if 'audio/ogg' not in [e.mime_type for e in episodes
            if e.mime_type is not None and e.file_exists()]:
            return None

        return [(_('Remove cover art'), self._rm_ogg_covers)]

    def _rm_ogg_covers(self, episodes):
        for episode in episodes:
            self.rm_ogg_cover(episode)

    def rm_ogg_cover(self, episode):
        filename = episode.local_filename(create=False)
        if filename is None:
            return

        basename, extension = os.path.splitext(filename)

        if episode.file_type() != 'audio':
            return

        if extension.lower() != '.ogg':
            return

        try:
            ogg = OggVorbis(filename)

            found = False
            for key in ogg.keys():
                if key.startswith('cover'):
                    found = True
                    ogg.pop(key)

            if found:
                logger.info('Removed cover art from OGG file: %s', filename)
                ogg.save()
        except Exception, e:
            logger.warn('Failed to remove OGG cover: %s', e, exc_info=True)

