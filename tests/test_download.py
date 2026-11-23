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
import pytest

from gpodder.download import DownloadURLOpener, gPodderDownloadHTTPError


class DummyChannel:
    auth_username = None
    auth_password = None


def test_accepted_response_is_not_saved_as_episode(httpserver, tmp_path):
    """A 202 Accepted body is not the episode, so it must not be written.

    The server tells us it queued the request and will serve the file later;
    saving the body would leave a status page where the audio file should be.
    """
    httpserver.expect_request('/episode.mp3').respond_with_data(
        '{"status": "queued"}', status=202, content_type='application/json')
    target = tmp_path / 'episode.mp3.partial'

    opener = DownloadURLOpener(DummyChannel())
    with pytest.raises(gPodderDownloadHTTPError) as exc_info:
        opener.retrieve_resume(httpserver.url_for('/episode.mp3'), str(target))

    assert exc_info.value.error_code == 202
    assert 'try again later' in exc_info.value.error_message
    assert target.read_bytes() == b''


def test_ok_response_is_saved(httpserver, tmp_path):
    httpserver.expect_request('/episode.mp3').respond_with_data(
        b'audio bytes', content_type='audio/mpeg')
    target = tmp_path / 'episode.mp3.partial'

    opener = DownloadURLOpener(DummyChannel())
    headers, _ = opener.retrieve_resume(httpserver.url_for('/episode.mp3'),
            str(target))

    assert target.read_bytes() == b'audio bytes'
