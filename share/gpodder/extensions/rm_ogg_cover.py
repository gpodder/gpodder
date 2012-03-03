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

try:
    from mutagen.oggvorbis import OggVorbis
except:
    logger.error( '(remove ogg cover extension) Could not find mutagen')

_ = gpodder.gettext

__title__ = _('Remove Coverart from OGG')
__description__ = _('removes coverart from all downloaded ogg files')
__author__ = 'Bernd Schlapsi <brot@gmx.info>'


DefaultConfig = {
    'extensions': {
        'rm_ogg_cover': {
            'context_menu': True,
        }
    }
}


class gPodderExtension:
    def __init__(self, container):
        self.container = container

    def on_load(self):
        logger.info('Extension "%s" is being loaded.' % __title__)

    def on_unload(self):
        logger.info('Extension "%s" is being unloaded.' % __title__)

    def on_episode_downloaded(self, episode):
        self.rm_ogg_cover(episode)

    def on_episodes_context_menu(self, episodes):
        if not self.container.config.context_menu:
            return None

        if 'audio/ogg' not in [e.mime_type for e in episodes
            if e.mime_type is not None and e.file_exists()]:
            return None

        return [(self.container.metadata.title, self._rm_ogg_covers)]

    def _rm_ogg_covers(self, episodes):
        for episode in episodes:
            self.rm_ogg_cover(episode)

    def rm_ogg_cover(self, episode):
        filename = episode.local_filename(create=False, check_only=True)
        if filename is None:
            return

        (basename, extension) = os.path.splitext(filename)
        if episode.file_type() == 'audio' and extension.lower().endswith('ogg'):
            logger.info(u'trying to remove cover from %s' % filename)
            found = False

            try:
                ogg = OggVorbis(filename)
                for key in ogg.keys():
                    if key.startswith('cover'):
                        found = True
                        ogg.pop(key)

                if found:
                    logger.info(u'removed cover from the ogg file successfully')
                    ogg.save()
                else:
                    logger.info(u'there was no cover to remove in the ogg file')
            except:
                None
