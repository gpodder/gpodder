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
from HTMLParser import HTMLParser
from xml.etree import ElementTree

_ = gpodder.gettext

try:
    # For Python < 2.6, we use the "simplejson" add-on module
    import simplejson as json
except ImportError:
    # Python 2.6 already ships with a nice "json" module
    import json

logger = logging.getLogger(__name__)


class NaiveHTMLParser(HTMLParser):
    """
    Python 3.x HTMLParser extension with ElementTree support.
    @see https://github.com/marmelo/python-htmlparser
    """

    def __init__(self):
        self.root = None
        self.tree = []
        HTMLParser.__init__(self)

    def feed(self, data):
        HTMLParser.feed(self, data)
        return self.root

    def handle_starttag(self, tag, attrs):
        if len(self.tree) == 0:
            element = ElementTree.Element(tag, dict(self.__filter_attrs(attrs)))
            self.tree.append(element)
            self.root = element
        else:
            element = ElementTree.SubElement(self.tree[-1], tag, dict(self.__filter_attrs(attrs)))
            self.tree.append(element)

    def handle_endtag(self, tag):
        self.tree.pop()

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)
        pass

    def handle_data(self, data):
        if self.tree:
            self.tree[-1].text = data

    def get_root_element(self):
        return self.root

    def __filter_attrs(self, attrs):
        return filter(lambda x: x[0] and x[1], attrs) if attrs else []


def parse_url(url):
    if url is None:
        return None
    parser = NaiveHTMLParser()
    html = util.urlopen(url).read()
    root = parser.feed(html)
    parser.close()
    return root


def rtp_parsedate(s):
    """Parse the RTP pages date format, in pt_PT locale.

    The format is 01 Jan, 2015
    """
    locale.setlocale(locale.LC_TIME, 'pt_PT.UTF-8')
    t = time.mktime(time.strptime(s, "%d %b, %Y"))
    locale.resetlocale()
    return t


class RTPPlayFeed(object):
    URL_REGEXEN = [
            re.compile('http://www.rtp.pt/play/p([0-9]+)'),
            re.compile('http://www.rtp.pt/play/podcast/([0-9]+)'),
            ]
    CACHE_FILE = os.path.join(gpodder.home, 'rtp_play.cache')

    @classmethod
    def handle_url(cls, url):
        # NOTE: Can I keep the for here?
        for regex in cls.URL_REGEXEN:
            m = regex.match(url)
            if m is not None:
                RTPid = m.group(1)
                return cls(RTPid)

    def __init__(self, programmeID):
        self.programmeID = str(programmeID)
        self.url_play = 'http://www.rtp.pt/play/p%s/' % self.programmeID
        self.url_info = None
        # Cache
        self.cache_read()

    def cache_read(self):
        """
        Read the memory cache from disk
        """
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
        """
        Dump the memory cache to disk
        """
        json.dump(self.cache,
                  open(self.CACHE_FILE, 'wb'),
                  sort_keys=True,
                  ensure_ascii=False,
                  encoding='UTF-8')
        logger.debug("Cache Write")

    # Network requests and HTML parsing
    # All the nasty stuff should be contained here
    def get_metadata_programme(self, cache=False):
        """
        Retrieve all programme metadata, except episodes

        Key: programmeID
        """
        if self.programmeID is None:
            return None
        try:
            logger.debug('P%s: Get Metadata', self.programmeID)
            metadata = {}
            e_play = parse_url(self.url_play)
            # Alternative info website
            A_info = e_play.find('//i[@class="fa fa-plus fa-lg text-muted"]/ancestor::a[1]')
            self.url_info = None if A_info is None else A_info.get("href")
            e_info = parse_url(self.url_info)
            # Title
            A_title = e_play.find('//div[@id="collapse-text"]/div/p[@class="h3"]/a')
            tmp_title = A_title.text.strip()
            if tmp_title.find("\n") or len(tmp_title) > 100:
                # Stop using the title as as description!
                A_title = e_info.find('.SectionName > h1')
                if A_title is None:
                    # Just make something up
                    tmp_title = "RTP Play P%s" % self.programmeID
                tmp_title = A_title.text.strip()
            metadata['title'] = tmp_title
            # URL
            metadata['url'] = self.url_info or self.url_play
            # Description
            P_desc = e_info.find('//div[@class="Area ProgPrincipal"]//div[@class="grid_5 omega"]/p[2]')
            if P_desc is not None:
                temp_desc = ''.join(P_desc.itertext())
            else:
                # Just make something up
                temp_desc = "RTP Play Description\nProgramme %s" % (self.programmeID)
            metadata["description"] = temp_desc
            # Coverart
            IMG_coverart = e_play.find('//div[@id="collapse-text"]/div/img')
            if IMG_coverart is None:
                # Just make something up
                IMG_coverart = "" #Something
            temp_coverart_raw = IMG_coverart.get('src')
            temp_coverart_regex = re.match('http:\/\/([^.]+\.).+\?src=([^&]+)&', temp_coverart_raw)
            if temp_coverart_regex is not None:
                temp_coverart = 'http://%srtp.pt%s' % (temp_coverart_regex.group(1), temp_coverart_regex.group(2))
            else:
                # In case the pattern changes
                temp_coverart = temp_coverart_raw
            metadata['coverart'] = temp_coverart
            # The Episodes need something
            metadata['episodes'] = {}
            # Store it on the memory cache
            self.cache[self.programmeID] = metadata
        finally:
            if cache:
                self.cache_write()


    def get_metadata_episodes(self, cache=False):
        """
        Retrive the list of new episodes, with no metadata

        Key: programmeID
        """
        temp_ids = self.metadata('episodes') or {}
        ids_all = set(temp_ids.keys())
        page = 1
        goto_next_page = True
        while goto_next_page:
            logger.debug('P%s: Updating Episode List - Page %d' % (self.programmeID, page))
            url = 'http://www.rtp.pt/play/bg_l_ep/?type=all&page={}&listProgram={}'.format(page, self.programmeID)
            e_url = parse_url(url)
            if e_url is None:
                # Nothing more to parse
                goto_next_page = False
            else:
                ids_page = set()
                As_url = e_url.findall('a[@class="episode-item"]')
                for A_url in As_url:
                    ids_page.add(re.search('e([0-9]+)', A_url.get('href')).group(1))
                if ids_page.issubset(ids_all):
                    # Nothing new to parse
                    logger.debug('P%s: No more new episodes' % self.programmeID)
                    goto_next_page = False
                else:
                    # Add all the new episodes to the existing
                    ids_all.update(ids_page)
                    # Get to the next page
                    page = page + 1
        return ids_all

    def get_metadata_episode(self, episodeID, cache=False):
        """
        Retrieve all episode metadata, including final URL

        Key: programmeID, episodeID
        """
        if self.programmeID is None or episodeID is None:
            return None
        try:
            logger.debug('P%sE%s: Get Metadata', self.programmeID, episodeID)
            metadata = {}
            # Link
            link = 'http://www.rtp.pt/play/p%s/e%s/' % (self.programmeID, episodeID)
            e_link = parse_url(link)
            # Title
            B_title = e_link.find('//article//b[@class="h4"]')
            if B_title is None:
                temp_title = "%s E%s" % (sef.get_title(), episodeID)
            else:
                temp_title = B_title.text.strip()
            metadata['title'] = temp_title
            # Description
            P_desc = e_link.find('//div[@id="promo"]/p')
            if P_desc is None:
                temp_desc = "RTP Play Description\nProgramme %s Episode %s" % (self.programmeID, episodeID)
            else:
                temp_desc = ''.join(P_desc.itertext().strip())
                # There's a characteristic whitespace incantation
                # that separates the per-episode description from the rest.
                # If it doesn't exist, just keep the text unchanged
                temp_desc, _, _ = temp_desc.partition('\r\n\t\t    ')
            metadata['description'] = temp_desc
            # URL - Method 1: monkey-parsing JS
            SCRIPT_url = e_link.findall('//script')[-1]
            if SCRIPT_url is not None:
                temp_url_script = SCRIPT_url.text.strip()
                temp_url_inner_regex = re.search('"file": "(.+?)"', temp_url_script)
                if temp_url_inner_regex is not None:
                    temp_url = 'http://cdn-ondemand.rtp.pt%s' % temp_url_inner_regex.group(1)
            if temp_url is None:  # Abandon all hope of getting a URL
                raise Exception("Can't get a URL from P%sE%" % (self.programmeID, episodeID))
            metadata['url'] = temp_url
            temp_filesize, temp_filetype = get_file_metadata(temp_url)
            metadata['file_size'] = int(temp_filesize)
            metadata['mime_type'] = temp_file
            # Published Date
            P_date = e_link.find('//div[@id="collapse-text"]//p[@class="text-white"]')
            if P_date is None:
                # Something's not right, but to avoid errors just put right now
                temp_date = time.time()
            else:
                temp_date_raw = P_date.text.strip()  # Get the last text node
                temp_date_regex = re.search('\d{2} \w{3}, \d{4}', temp_date_raw)
                if temp_date_regex is None:
                    # Another fishy situation
                    temp_date = time.time()
                else:
                    temp_date = rtp_parsedate(temp_date_regex.group(0))
            metadata['published'] = temp_date
            # GUID: The link is enough
            metadata['guid'] = metadata['link']
            # Store it on the memory cache
            self.cache[self.programmeID]['episodes'][episodeID] = metadata
        finally:
            if cache:
                self.cache_write()

    # Private API
    def metadata(self, key, cache=True):
        """
        Get a single value of programme metadata

        Key: programmeID
        """
        if self.programmeID not in self.cache:
            self.get_metadata_programme()
        if key not in self.cache[self.programmeID]:
            return None
        if cache:
            self.cache_write()
        return self.cache[self.programmeID][key]

    def metadata_episode(self, episodeID, cache=False):
        """
        Get an array of metadata for a single episode

        Key: programmeID, episodeID
        """
        if episodeID not in self.cache[self.programmeID]['episodes']:
            self.get_metadata_episode(episodeID)
        if cache:
            self.cache_write()
        return self.cache[self.programmeID]['episodes'][episodeID]

    def metadata_episodes(self, episodeIDs, cache=True):
        """
        Get an array of arrays of metadata for the given episodes

        Key: programmeID, episodeIDs [episodeID]
        """
        episodes = []
        for episodeID in episodeIDs:
            episode = self.metadata_episode(episodeID, cache=False)
            episodes.append(episode)
        if cache:
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
        all_episodes_ids = self.get_metadata_episodes()
        all_episodes = self.metadata_episodes(all_episodes_ids)
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
