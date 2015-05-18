#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
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

# RTP Play support for gpodder
# There's no public (nor private) API, this is some ugly HTML parsing
# somini <somini@users.noreply.github.com>; 2014-12-19

import gpodder

import logging
import os
import time

import re
import email
import locale
import urllib

from gpodder import model
from gpodder import util
from lxml import etree

_ = gpodder.gettext

try:
    # For Python < 2.6, we use the "simplejson" add-on module
    import simplejson as json
except ImportError:
    # Python 2.6 already ships with a nice "json" module
    import json

logger = logging.getLogger(__name__)


def get_file_metadata(url):
    """Get file download metadata

    Returns a (size, type, name) from the given download
    URL. Will use the network connection to determine the
    metadata via the HTTP header fields.
    """
    track_fp = util.urlopen(url)
    headers = track_fp.info()
    filesize = headers["content-length"] or '0'
    filetype = headers["content-type"] or 'application/octet-stream'
    track_fp.close()
    return filesize, filetype


def rtp_parsedate(s):
    """Parse the RTP pages date format, in pt_PT locale.

    The format is 01 Jan, 2015
    """
    locale.setlocale(locale.LC_TIME, 'pt_PT.UTF-8')
    t = time.mktime(time.strptime(s, "%d %b, %Y"))
    locale.resetlocale()
    return t


def html_parser(url):
    return None if url is None else etree.parse(url, etree.HTMLParser())


class RTPPlayFeed(object):
    URL_REGEX = re.compile('http://www.rtp.pt/play/p([0-9]+)')
    PODCAST_REGEX = re.compile('http://www.rtp.pt/play/podcast/([0-9]+)')
    CACHE_FILE = os.path.join(gpodder.home, 'rtp_play.cache')

    @classmethod
    def handle_url(cls, url):
        m = cls.URL_REGEX.match(url) or cls.PODCAST_REGEX.match(url)
        if m is not None:
            RTPid = m.group(1)
            return cls(RTPid)

    def __init__(self, programID):
        self.programID = str(programID)
        self.play_url = 'http://www.rtp.pt/play/p%s/' % programID
        self.play_url_etree = None
        # Cache
        self.cache_read()

    def cache_read(self):
        filename = self.CACHE_FILE
        obj = {}
        if os.path.exists(filename):
            try:
                obj = json.load(open(filename, 'rb'), encoding='UTF-8')
            except:
                obj = {}
        self.cache = obj
        logger.debug("Cache Read")

    def cache_write(self):
        json.dump(self.cache,
                  open(self.CACHE_FILE, 'wb'),
                  sort_keys=True,
                  ensure_ascii=False,
                  encoding='UTF-8')
        logger.debug("Cache Write")

    def get_all_episodes(self):
        episode_ids = self.get_episodes_program()
        return self.metadata_episodes(episode_ids)

    def get_metadata_program(self):
        if self.programID is None:
            return None
        try:
            logger.debug('P%s: Get Metadata', self.programID)
            etree_play = html_parser(self.play_url)
            info_anchor = etree_play.xpath('//i[@class="fa fa-plus fa-lg text-muted"]/ancestor::a[1]')[0]
            info_url = None if info_anchor is None else "http://www.rtp.pt%s" % info_anchor.get("href")
            etree_info = html_parser(info_url)
            logger.debug('P%s: Parsing HTML', self.programID)
            e_title = etree_play.find('//div[@id="collapse-text"]/div/p[@class="h3"]/a').text.strip()
            e_link = info_url or self.play_url
            e_desc = "Get from etree_play" if info_url is None else ''.join(etree_info.find('//div[@class="Area ProgPrincipal"]//div[@class="grid_5 omega"]/p[2]').itertext())
            raw_coverart = etree_play.find('//div[@id="collapse-text"]/div/img').get("src")
            r_coverart = re.match('http:\/\/([^.]+\.).+\?src=([^&]+)&', raw_coverart)
            e_coverart = "http://%srtp.pt%s" % (r_coverart.group(1), r_coverart.group(2))
            logger.debug('P%s: Caching', self.programID)
            self.cache[self.programID] = {
                    'title': e_title,
                    'url': e_link,
                    'description': e_desc,
                    'coverart': e_coverart
                    }
        finally:
            self.cache_write()

    def get_episodes_program(self):
        e_cache = self.metadata('episodes') or {}
        ids_all = set(e_cache.keys())

        page = 1
        goto_next_page = True
        while goto_next_page:
            logger.debug('P%s: Updating Episode List - Page %d' % (self.programID, page))
            url = 'http://www.rtp.pt/play/bg_l_ep/?type=all&page={}&listProgram={}'.format(page, self.programID)
            etree_url = html_parser(url)
            if etree_url is None or etree_url.getroot() is None:  # Nothing more to parse
                goto_next_page = False
            else:
                ids_page = set()
                url_anchors = etree_url.xpath('//a[@class="episode-item"]')
                for anchor in url_anchors:
                    ids_page.add(re.search('e([0-9]+)', anchor.get('href')).group(1))
                if ids_page.issubset(ids_all):
                    logger.debug('P%s: No more new episodes' % self.programID)
                    goto_next_page = False
                else:
                    ids_all.update(ids_page)
                    page = page + 1
        return ids_all

    def get_metadata_episode(self, episodeID, cache=False):
        _cache_title = 'episodes'
        if self.programID is None:
            return None
        try:
            logger.debug('P%sE%s: Get Metadata', self.programID, episodeID)
            link = 'http://www.rtp.pt/play/p%s/e%s/' % (self.programID, episodeID)
            etree_link = html_parser(link)
            logger.debug('P%sE%s: Parsing HTML', self.programID, episodeID)
            raw_title = etree_link.find('//article//b[@class="h4"]')
            e_title = self.get_title() if raw_title is None else raw_title.text.strip()
            e_desc = ''.join(etree_link.find('//div[@id="promo"]/p').itertext()).strip()
            e_desc, _, _ = e_desc.partition("\r\n\t\t    ")
            raw_url = etree_link.findall('//script')[-1].text.strip()
            e_url = "http://cdn-ondemand.rtp.pt%s" % re.search('"file": "(.+?)"', raw_url).group(1)
            e_filesize, e_filetype = get_file_metadata(e_url)
            raw_date = etree.tostring(etree_link.find('//div[@id="collapse-text"]//p[@class="text-white"]')).strip()
            e_date = rtp_parsedate(re.search('\d{2} \w{3}, \d{4}', raw_date).group(0))
            logger.debug('P%sE%s: Caching', self.programID, episodeID)
            if _cache_title not in self.cache[self.programID]:
                self.cache[self.programID][_cache_title] = {}
            self.cache[self.programID][_cache_title][episodeID] = {
                    'title': e_title,
                    'link': link,
                    'description': e_desc,
                    'url': e_url,
                    'file_size': int(e_filesize),
                    'mime_type': e_filetype,
                    'guid': link,
                    'published': e_date,
                    }
        finally:
            if cache:
                self.cache_write()

    def metadata(self, name):
        if self.programID not in self.cache:
            self.get_metadata_program()
        if name not in self.cache[self.programID]:
            self.cache[self.programID][name] = {}
        return self.cache[self.programID][name]

    def metadata_episode(self, episodeID):
        if episodeID not in self.cache[self.programID]['episodes']:
            self.get_metadata_episode(episodeID)
        return self.cache[self.programID]['episodes'][episodeID]

    def metadata_episodes(self, episodeIDs):
        episodes = []
        for episodeID in episodeIDs:
            episode = self.metadata_episode(episodeID)
            episodes.append(episode)
        self.cache_write()  # Only once
        return episodes

    # Public methods
    def get_title(self):
        return self.metadata('title')

    def get_link(self):
        return self.metadata('url')

    def get_description(self):
        return self.metadata('description')

    def get_image(self):
        return self.metadata('coverart')

    def get_new_episodes(self, channel, existing_guids):
        all_episodes = self.get_all_episodes()
        all_guids = [ep['guid'] for ep in all_episodes]

        new_episodes = []
        for episode in all_episodes:
            if episode['guid'] not in existing_guids:
                gpo_episode = channel.episode_factory(episode)
                gpo_episode.save()
                new_episodes.append(gpo_episode)

        return new_episodes, all_guids

# Register our URL handler
model.register_custom_handler(RTPPlayFeed)
