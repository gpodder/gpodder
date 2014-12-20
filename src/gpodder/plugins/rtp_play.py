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

_ = gpodder.gettext

from gpodder import model
from gpodder import util

try:
	# For Python < 2.6, we use the "simplejson" add-on module
	import simplejson as json
except ImportError:
	# Python 2.6 already ships with a nice "json" module
	import json

import logging
logger = logging.getLogger(__name__)

import os
import time

import re
import email
import locale
import urllib
from lxml import etree

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
	t = time.mktime( time.strptime(s, "%d %b, %Y") )
	locale.resetlocale()
	return t
def soundcloud_parsedate(s):
	    """Parse a string into a unix timestamp

	    Only strings provided by Soundcloud's API are
	    parsed with this function (2009/11/03 13:37:00).
	    """
	    m = re.match(r'(\d{4})/(\d{2})/(\d{2}) (\d{2}):(\d{2}):(\d{2})', s)
	    return time.mktime([int(x) for x in m.groups()]+[0, 0, -1])

def save_cache(filename, obj):
	json.dump(obj, open(filename, 'w'))
def read_cache(filename):
	obj = {}
	if os.path.exists(filename):
		try:
			obj = json.load(open(filename, 'r'))
		except:
			obj = {}
	return obj

class RTPPlayFeed(object):
	URL_REGEX = re.compile('http://www.rtp.pt/play/p([0-9]+)')
	PODCAST_REGEX = re.compile('http://www.rtp.pt/play/podcast/([0-9]+)')
	CACHE_FILE = os.path.join(gpodder.home, 'RTPPlay.cache')
	URL_CACHE_FILE = os.path.join(gpodder.home, 'url.cache')

	@classmethod
	def handle_url(cls, url):
		m = cls.URL_REGEX.match(url) or cls.PODCAST_REGEX.match(url)
		if m is not None:
			RTPid = m.group(1)
			logger.debug("RTP Play id: %s" % RTPid)
			return cls(RTPid)

	def __init__(self, programID):
		self.programID = str(programID)
		self.play_url = 'http://www.rtp.pt/play/p%s/' % programID
		self.play_url_etree = None

	def _root_etree(self):
		if self.play_url_etree is None:
			self.play_url_etree = etree.parse(self.play_url, etree.HTMLParser())
		return self.play_url_etree

	def get_episodes(self):
		"""Get a generator of episodes from a program

		The generator will give you a dictionary for
		every episode it can find for its program."""
		logger.debug("RTP %s: Get All Episodes" % self.programID)
		episodes = []

		try:
			episode_ids = set() # No duplicates
			page = 1
			goto_next_page = True
			while goto_next_page:
				logger.debug("RTP %s: Episodes - Page %d" % (self.programID, page))
				rawURL = 'http://www.rtp.pt/play/bg_l_ep/?type=all&page={}&listProgram={}'.format(page,self.programID)
				root = etree.parse(rawURL, etree.HTMLParser())
				if root is None or root.getroot() is None: # Nothing more to parse
					goto_next_page = False
				else:
					page_episodes = root.xpath('//a[@class="episode-item"]')
					for episode_anchor in page_episodes:
						r = re.compile('e([0-9]+)').search(episode_anchor.get("href"))
						episode_ids.add(r.group(1))
					page = page + 1

			logger.debug("RTP %s: Episodes = %d" % (self.programID, len(episode_ids)))

			for episodeID in episode_ids: # Might take a while
				eURL = 'http://www.rtp.pt/play/p%s/e%s/' % (self.programID, episodeID)
				logger.debug("RTP %s: Episode %s@%s" % (self.programID, episodeID, eURL))
				root = etree.parse(eURL, etree.HTMLParser())
				url_text = root.findall('//script')[-1].text.strip()
				url = "http://cdn-ondemand.rtp.pt%s" % re.compile('"file": "(.+?)"').search(url_text).group(1)
				filesize, filetype = get_file_metadata(url)
				eDate = etree.tostring(root.xpath('//div[@id="collapse-text"]//p[@class="text-white"]')[0]).strip()
				date = re.compile('\d{2} \w{3}, \d{4}').search(eDate).group(0)
				episode = {
						'title' : root.xpath('//div[@id="collapse-text"]//p[@class="h3"]/a')[0].text,
						'link' : eURL,
						'description' : etree.tostring(root.xpath('//div[@id="promo"]/p')[0]).strip(),
						'url' : url,
						'file_size' : int(filesize),
						'mime_type' : filetype,
						'guid' : eURL,
						'published' : rtp_parsedate(date),
				}
				episodes.append(episode)
		finally:
			logger.debug("Finished parsing all the episodes")# Do nothing
		return episodes

	# Public methods
	def get_title(self):
		logger.debug("RTP %s: Get Title" % self.programID)
		return self._root_etree().xpath('//div[@id="collapse-text"]/div/p[@class="h3"]/a/text()')[0].strip()
	def get_link(self):
		logger.debug("RTP %s: Get Link" % self.programID)
		info_anchor = self._root_etree().xpath('//i[@class="fa fa-plus fa-lg text-muted"]/ancestor::a[1]')
		if len(info_anchor) == 1:
			return "http://www.rtp.pt%s" % info_anchor[0].get("href")
		else:
			return self.play_url
	def get_description(self):
		logger.debug("RTP %s: Get desc", self.programID)
		root_info = etree.parse(self.get_link(), etree.HTMLParser())
		return ''.join(root_info.find('//div[@class="Area ProgPrincipal"]//div[@class="grid_5 omega"]/p[2]').itertext())
	def get_image(self):
		logger.debug("RTP %s: Get Coverart", self.programID)
		s = self._root_etree().xpath('//div[@id="collapse-text"]/div/img')[0].get("src")
		r = re.compile('http:\/\/([^.]+\.).+\?src=([^&]+)&').match(s)
		return "http://%srtp.pt%s" % (r.group(1), r.group(2))
	def get_new_episodes(self, channel, existing_guids):
		all_episodes = self.get_episodes()
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
