# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4
import os
import json
import logging
import re

from datetime import timedelta
logger = logging.getLogger(__name__)

import gpodder
from gpodder import util

_ = gpodder.gettext

__title__ = _('Subtitle Downloader for TED Talks')
__description__ = _('Downloads .srt subtitles for TED Talks Videos')
__authors__ = 'Danilo Shiga <daniloshiga@gmail.com>'
__category__ = 'post-download'
__only_for__ = 'gtk, cli'


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

    def get_srt_filename(self, audio_filename):
        basename, _ = os.path.splitext(audio_filename)
        return basename + '.srt'

    def on_episode_downloaded(self, episode):
        guid_result = re.search(r'talk.ted.com:(\d+)', episode.guid)
        if guid_result is not None:
            talkId = int(guid_result.group(1))
        else:
            logger.debug('Not a TED Talk. Ignoring.')
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

        INTRO_DEFAULT = 15
        try:
            # intro in the data could be 15 or 15.33
            intro = episode_data
            intro = episode_data.split('introDuration":')[1] \
                                .split(',')[0] or INTRO_DEFAULT
            intro = int(float(intro)*1000)
        except (ValueError, IndexError), e:
            logger.info("Couldn't parse introDuration string: %s", intro)
            intro = INTRO_DEFAULT * 1000
        current_filename = episode.local_filename(create=False)
        srt_filename = self.get_srt_filename(current_filename)
        sub = self.ted_to_srt(sub_data, int(intro))

        try:
            with open(srt_filename, 'w+') as srtFile:
                srtFile.write(sub.encode("utf-8"))
        except Exception, e:
            logger.warn("Can't write srt file: %s",e)

    def on_episode_delete(self, episode, filename):
        srt_filename = self.get_srt_filename(filename)
        if os.path.exists(srt_filename):
            os.remove(srt_filename)

