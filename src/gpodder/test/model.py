#
# gpodder.test.model - Unit tests for gpodder.model (2013-02-12)
# Copyright (c) 2013, Thomas Perl <m@thp.io>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.
#


import unittest

import gpodder

from gpodder import model

class TestEpisodePublishedProperties(unittest.TestCase):
    PUBLISHED_UNIXTIME = 1360666744
    PUBLISHED_SORT = '2013-02-12'

    def setUp(self):
        self.podcast = model.PodcastChannel(None)
        self.episode = model.PodcastEpisode(self.podcast)
        self.episode.published = self.PUBLISHED_UNIXTIME

    def test_sortdate(self):
        self.assertEqual(self.episode.sortdate, self.PUBLISHED_SORT)

class TestSectionFromContentType(unittest.TestCase):
    def setUp(self):
        self.podcast = model.PodcastChannel(None)
        self.podcast.url = 'http://example.com/feed.rss'
        self.audio_episode = model.PodcastEpisode(self.podcast)
        self.audio_episode.mime_type = 'audio/mpeg'
        self.video_episode = model.PodcastEpisode(self.podcast)
        self.video_episode.mime_type = 'video/mp4'

    def test_audio(self):
        self.podcast.children = [self.audio_episode]
        self.assertEqual(self.podcast._get_content_type(), 'audio')

    def test_video(self):
        self.podcast.children = [self.video_episode]
        self.assertEqual(self.podcast._get_content_type(), 'video')

    def test_more_video_than_audio(self):
        self.podcast.children = [self.audio_episode, self.video_episode, self.video_episode]
        self.assertEqual(self.podcast._get_content_type(), 'video')

