# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2013 Thomas Perl and the gPodder Team
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

# gpodder.test.util - Unit tests for gpodder.util
# Kyle Stevens <kstevens715@gmail.com>; 2013-05-25


import unittest

import gpodder

from gpodder import util

class TestNormalizeFeedUrl(unittest.TestCase):

    def test_convert_scheme(self):
        self.assertEqual(util.normalize_feed_url('itpc://example.org/podcast.rss'), 'http://example.org/podcast.rss')

    def test_no_url_scheme(self):
        self.assertEqual(util.normalize_feed_url('curry.com'), 'http://curry.com/')

    def test_convert_to_lower(self):
        self.assertEqual(util.normalize_feed_url('http://Example.COM/'), 'http://example.com/')

    def test_auth_not_altered(self):
        self.assertEqual(util.normalize_feed_url('http://Bob@example.com:Password@Example.COM/'), 'http://Bob@example.com:Password@example.com/')

    def test_remove_empty_query(self):
        self.assertEqual(util.normalize_feed_url('http://example.org/test?'), 'http://example.org/test')

    def test_shortcut(self):
        self.assertEqual(util.normalize_feed_url('fb:43FPodcast'), 'http://feeds.feedburner.com/43FPodcast')

class TestUrlAddAuthentication(unittest.TestCase):

    def test_exclamation_in_password_not_escaped(self):
        self.assertEqual(util.url_add_authentication('https://host.com/', 'foo', 'b!r'), 'https://foo:b!r@host.com/')

    def test_blank_user_none_password(self):
        self.assertEqual(util.url_add_authentication('https://host.com/', '', None), 'https://host.com/')

    def test_none_user_none_password(self):
        self.assertEqual(util.url_add_authentication('http://example.org/', None, None), 'http://example.org/')

    def test_telnet_user_password(self):
        self.assertEqual(util.url_add_authentication('telnet://host.com/', 'foo', 'bar'), 'telnet://foo:bar@host.com/')

    def test_ftp_user_none_password(self):
        self.assertEqual(util.url_add_authentication('ftp://example.org', 'billy', None), 'ftp://billy@example.org')

    def test_ftp_user_blank_password(self):
        self.assertEqual(util.url_add_authentication('ftp://example.org', 'billy', ''), 'ftp://billy:@example.org')

    def test_localhost(self):
        self.assertEqual(util.url_add_authentication('http://localhost/x', 'aa', 'bc'), 'http://aa:bc@localhost/x')

    def test_forward_slash_in_user_and_at_in_pass_allowed(self):
        self.assertEqual(util.url_add_authentication('http://blubb.lan/u.html', 'i/o', 'P@ss:'), 'http://i%2Fo:P@ss:@blubb.lan/u.html')

    def test_at_in_user_and_slash_in_pass_allowed(self):
        self.assertEqual(util.url_add_authentication('http://i%2F:P%40%3A@cx.lan', 'P@x', 'i/'), 'http://P@x:i%2F@cx.lan')

    def test_existing_auth_replaced(self):
        self.assertEqual(util.url_add_authentication('http://a:b@x.org/', 'c', 'd'), 'http://c:d@x.org/')

    def test_spaces_in_user_and_password_are_escaped(self):
        self.assertEqual(util.url_add_authentication('http://x.org/', 'a b', 'c d'), 'http://a%20b:c%20d@x.org/')
