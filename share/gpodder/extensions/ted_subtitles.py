# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4
import os
import json
import logging

from datetime import timedelta
logger = logging.getLogger(__name__)

import gpodder
from gpodder import util

_ = gpodder.gettext

__title__ = _('Subtitle Downloader for TED Talks')
__description__ = _('Downloads .srt subtitles for TED Talks Videos')
__only_for__ = 'gtk, cli, qml'
__authors__ = 'Danilo Shiga <daniloshiga@gmail.com>'


class gPodderExtension(object):
    """
    TED Subtitle Download Extension
    Downloads ted subtitles
    """
    def __init__(self, container):
        self.container = container

    def milli_to_srt(self, time):
        """Converts milliseconds to srt time format"""
        srt_time = timedelta(milliseconds=time)
        srt_time = str(srt_time)
        if '.' in srt_time:
            srt_time = srt_time.replace('.', ',')[:11]
        else:
            # ',000' required to be a valid srt line
            srt_time += ',000'
        return srt_time

    def ted_to_srt(self, jsonstring, introduration):
        """Converts the json object to srt format"""
        jsonobject = json.loads(jsonstring)

        srtContent = ''
        for captionIndex, caption in enumerate(jsonobject['captions'], 1):
            startTime = self.milli_to_srt(introduration + caption['startTime'])
            endTime = self.milli_to_srt(introduration + caption['startTime'] +
                                        caption['duration'])
            srtContent += ''.join([str(captionIndex), os.linesep, startTime,
                                   ' --> ', endTime, os.linesep,
                                   caption['content'], os.linesep * 2])
        return srtContent

    def get_data_from_url(self, url):
        try:
            response = util.urlopen(url).read()
        except Exception, e:
            logger.warn("subtitle url returned error %s", e)
            return ''
        return response

    def on_episode_downloaded(self, episode):
        if 'talk.ted.com' not in episode.guid:
            logger.debug('Not a TED Talk. Ignoring.')
            return

        talkId = episode.guid.split(':')[-1]
        try:
            int(talkId)
        except ValueError:
            logger.warn('invalid talk id: %s', talkId)
            return

        sub_url = 'http://www.ted.com/talks/subtitles/id/%s/lang/eng' % talkId
        logger.info('subtitle url: %s', sub_url)
        sub_data = self.get_data_from_url(sub_url)
        if not sub_data:
            return

        logger.info('episode url: %s', episode.link)
        episode_data = self.get_data_from_url(episode.link)
        if not episode_data:
            return

        intro = episode_data.split('introDuration=')[1].split('&')[0] or 0
        current_filename = episode.local_filename(create=False)
        basename, _ = os.path.splitext(current_filename)
        sub = self.ted_to_srt(sub_data, int(intro))

        try:
            with open(basename + '.srt', 'w+') as srtFile:
                srtFile.write(sub.encode("utf-8"))
        except Exception, e:
            logger.warn("Can't write srt file: %s",e)
