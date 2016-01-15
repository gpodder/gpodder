# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2016 Thomas Perl and the gPodder Team
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

from mygpoclient import feeds

import logging
logger = logging.getLogger(__name__)


def parse_entry(podcast, entry):
    download_url = entry['default_file']['url']
    return podcast.episode_factory({
        'title': entry['title'],
        'description': entry.get('description', ''),
        'url': download_url,
        'mime_type': entry['default_file']['mime_type'],
        'file_size': entry.get('filesize', -1),
        'guid': entry.get('guid', download_url),
        'link': entry.get('link', ''),
        'published': entry.get('released', 0),
        'total_time': entry.get('duration', 0),
    })


def update_using_feedservice(podcasts):
    urls = [podcast.url for podcast in podcasts]
    client = feeds.FeedserviceClient()
    # Last modified + logo/etc..
    result = client.parse_feeds(urls)

    for podcast in podcasts:
        feed = result.get_feed(podcast.url)
        if feed is None:
            logger.info('Feed not updated: %s', podcast.url)
            continue

        # Handle permanent redirects
        if feed.get('new_location', False):
            new_url = feed['new_location']
            logger.info('Redirect %s => %s', podcast.url, new_url)
            podcast.url = new_url

        # Error handling
        if feed.get('errors', False):
            logger.error('Error parsing feed: %s', repr(feed['errors']))
            continue

        # Update per-podcast metadata
        podcast.title = feed.get('title', podcast.url)
        podcast.link = feed.get('link', podcast.link)
        podcast.description = feed.get('description', podcast.description)
        podcast.cover_url = feed.get('logo', podcast.cover_url)
        #podcast.http_etag = feed.get('http_etag', podcast.http_etag)
        #podcast.http_last_modified = feed.get('http_last_modified', \
        #        podcast.http_last_modified)
        podcast.save()

        # Update episodes
        parsed_episodes = [parse_entry(podcast, entry) for entry in feed['episodes']]

        # ...




