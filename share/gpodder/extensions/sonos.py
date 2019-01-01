# -*- coding: utf-8 -*-
# Extension script to stream podcasts to Sonos speakers
# Requirements: gPodder 3.x and the soco module >= 0.7 (https://pypi.python.org/pypi/soco)
# (c) 2013-01-19 Stefan Kögl <stefan@skoegl.net>
# Released under the same license terms as gPodder itself.

import logging
from functools import partial

import requests

import gpodder
import soco

_ = gpodder.gettext

logger = logging.getLogger(__name__)

__title__ = _('Stream to Sonos')
__description__ = _('Stream podcasts to Sonos speakers')
__authors__ = 'Stefan Kögl <stefan@skoegl.net>'
__category__ = 'interface'
__only_for__ = 'gtk'


def SONOS_CAN_PLAY(e):
    return 'audio' in e.file_type()


class gPodderExtension:
    def __init__(self, container):
        speakers = soco.discover()
        logger.info('Found Sonos speakers: %s' % ', '.join(name.player_name for name in speakers))

        self.speakers = {}
        for speaker in speakers:

            try:
                info = speaker.get_speaker_info()

            except requests.ConnectionError as ce:
                # ignore speakers we can't connect to
                continue

            name = info.get('zone_name', None)
            uid = speaker.uid

            # devices that do not have a name are probably bridges
            if name:
                self.speakers[uid] = speaker

    def _stream_to_speaker(self, speaker_uid, episodes):
        """ Play or enqueue selected episodes """

        urls = [episode.url for episode in episodes if SONOS_CAN_PLAY(episode)]
        logger.info('Streaming to Sonos %s: %s' % (self.speakers[speaker_uid].ip_address, ', '.join(urls)))

        controller = self.speakers[speaker_uid].group.coordinator

        # enqueue and play
        for episode in episodes:
            controller.play_uri(episode.url)
            episode.playback_mark()

        controller.play()

    def on_episodes_context_menu(self, episodes):
        """ Adds a context menu for each Sonos speaker group """

        # Only show context menu if we can play at least one file
        if not any(SONOS_CAN_PLAY(e) for e in episodes):
            return []

        menu_entries = []
        for uid in list(self.speakers.keys()):
            callback = partial(self._stream_to_speaker, uid)

            controller = self.speakers[uid]
            is_grouped = ' (Grouped)' if len(controller.group.members) > 1 else ''
            name = controller.group.label + is_grouped
            item = ('/'.join((_('Stream to Sonos'), name)), callback)
            menu_entries.append(item)

        # Remove any duplicate group names. I doubt Sonos allows duplicate speaker names,
        # but we do initially get duplicated group names with the loop above
        return list(dict(menu_entries).items())
