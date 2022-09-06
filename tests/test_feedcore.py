# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2023 The gPodder Team
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
import io

import pytest
import requests.exceptions

from gpodder.feedcore import Fetcher, NEW_LOCATION, Result, UPDATED_FEED


class MyFetcher(Fetcher):
    def parse_feed(self, url, feed_data, data_stream, headers, status, **kwargs):
        return Result(status, {
            'parse_feed': {
                'url': url,
                'feed_data': feed_data,
                'data_stream': data_stream,
                'headers': headers,
                'extra_args': dict(**kwargs),
            },
        })


SIMPLE_RSS = """
<rss>
    <channel>
        <title>Feed Name</title>
        <item>
        <title>Some Episode Title</title>
        <guid>urn:test/ep1</guid>
        <pubDate>Sun, 25 Nov 2018 17:28:03 +0000</pubDate>
        <enclosure
          url="/ep1.ogg"
          type="audio/ogg"
          length="100000"/>
        </item>
    </channel>
</rss>
"""

def test_easy(httpserver):
    res_data = SIMPLE_RSS
    httpserver.expect_request('/feed').respond_with_data(SIMPLE_RSS, content_type='text/xml')
    res = MyFetcher().fetch(httpserver.url_for('/feed'), custom_key='value')
    assert res.status == UPDATED_FEED
    args = res.feed['parse_feed']
    assert args['headers']['content-type'] == 'text/xml'
    assert isinstance(args['data_stream'], io.BytesIO)
    assert args['data_stream'].getvalue().decode('utf-8') == SIMPLE_RSS
    assert args['url'] == httpserver.url_for('/feed')
    assert args['extra_args']['custom_key'] == 'value'

def test_redirect(httpserver):
    res_data = SIMPLE_RSS
    httpserver.expect_request('/endfeed').respond_with_data(SIMPLE_RSS, content_type='text/xml')
    redir_headers = {
        'Location': '/endfeed',
    }
    # temporary redirect
    httpserver.expect_request('/feed').respond_with_data(status=302, headers=redir_headers)
    httpserver.expect_request('/permanentfeed').respond_with_data(status=301, headers=redir_headers)
    
    res = MyFetcher().fetch(httpserver.url_for('/feed'))
    assert res.status == UPDATED_FEED
    args = res.feed['parse_feed']
    assert args['headers']['content-type'] == 'text/xml'
    assert isinstance(args['data_stream'], io.BytesIO)
    assert args['data_stream'].getvalue().decode('utf-8') == SIMPLE_RSS
    assert args['url'] == httpserver.url_for('/feed')

    res = MyFetcher().fetch(httpserver.url_for('/permanentfeed'))
    assert res.status == NEW_LOCATION
    assert res.feed == httpserver.url_for('/endfeed')


def test_redirect_loop(httpserver):
    """ verify that feedcore fetching will not loop indefinitely on redirects """
    redir_headers = {
        'Location': '/feed',  # it loops
    }
    httpserver.expect_request('/feed').respond_with_data(status=302, headers=redir_headers)

    with pytest.raises(requests.exceptions.TooManyRedirects):
        res = MyFetcher().fetch(httpserver.url_for('/feed'))
        assert res.status == UPDATED_FEED
        args = res.feed['parse_feed']
        assert args['headers']['content-type'] == 'text/xml'
        assert isinstance(args['data_stream'], io.BytesIO)
        assert args['data_stream'].getvalue().decode('utf-8') == SIMPLE_RSS
        assert args['url'] == httpserver.url_for('/feed')

def test_temporary_error_retry(httpserver):
    httpserver.expect_ordered_request('/feed').respond_with_data(status=503)
    res_data = SIMPLE_RSS
    httpserver.expect_ordered_request('/feed').respond_with_data(SIMPLE_RSS, content_type='text/xml')
    res = MyFetcher().fetch(httpserver.url_for('/feed'))
    assert res.status == UPDATED_FEED
    args = res.feed['parse_feed']
    assert args['headers']['content-type'] == 'text/xml'
    assert args['url'] == httpserver.url_for('/feed')
