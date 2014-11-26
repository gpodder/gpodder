# -*- coding: utf-8 -*-
# Extension script to stream podcasts to Sonos speakers
# Requirements: gPodder 3.x and the soco module (https://pypi.python.org/pypi/soco)
# (c) 2013-01-19 Stefan Kögl <stefan@skoegl.net>
# Released under the same license terms as gPodder itself.

from functools import partial

import gpodder
_ = gpodder.gettext

import logging
logger = logging.getLogger(__name__)

import soco
import requests


__title__ = _('Stream to Sonos')
__description__ = _('Stream podcasts to Sonos speakers')
__authors__ = 'Stefan Kögl <stefan@skoegl.net>'
__category__ = 'interface'
__only_for__ = 'gtk'


SONOS_CAN_PLAY = lambda e: 'audio' in e.file_type()

class gPodderExtension:
    def __init__(self, container):
        sd = soco.SonosDiscovery()
        speaker_ips = sd.get_speaker_ips()

        logger.info('Found Sonos speakers: %s' % ', '.join(speaker_ips))

        self.speakers = {}
        for speaker_ip in speaker_ips:
            controller = soco.SoCo(speaker_ip)

            try:
                info = controller.get_speaker_info()

            except requests.ConnectionError as ce:
                # ignore speakers we can't connect to
                continue

            name = info.get('zone_name', None)

            # devices that do not have a name are probably bridges
            if name:
                self.speakers[speaker_ip] = name

    def _stream_to_speaker(self, speaker_ip, episodes):
        """ Play or enqueue selected episodes """

        urls = [episode.url for episode in episodes if SONOS_CAN_PLAY(episode)]
        logger.info('Streaming to Sonos %s: %s'%(speaker_ip, ', '.join(urls)))

        controller = soco.SoCo(speaker_ip)

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
        for speaker_ip, name in self.speakers.items():
            callback = partial(self._stream_to_speaker, speaker_ip)

            item = ('/'.join((_('Stream to Sonos'), name)), callback)
            menu_entries.append(item)

        return menu_entries
