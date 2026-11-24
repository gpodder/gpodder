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
import xml.dom.minidom
from types import SimpleNamespace

from gpodder import opml

CHANNEL = SimpleNamespace(
    title='Some Podcast',
    description='Description of the podcast',
    url='https://example.com/feed.xml',
    section='audio',
)


def test_export_puts_title_in_text(tmp_path):
    filename = str(tmp_path / 'subscriptions.opml')
    assert opml.Exporter(filename).write([CHANNEL])

    outline = [o for o in xml.dom.minidom.parse(filename).getElementsByTagName('outline')
               if o.getAttribute('type') == 'rss'][0]
    assert outline.getAttribute('title') == 'Some Podcast'
    assert outline.getAttribute('text') == 'Some Podcast'
    assert outline.getAttribute('description') == 'Description of the podcast'


def test_export_import_round_trip(tmp_path):
    filename = str(tmp_path / 'subscriptions.opml')
    assert opml.Exporter(filename).write([CHANNEL])

    assert opml.Importer(filename).items == [{
        'url': 'https://example.com/feed.xml',
        'title': 'Some Podcast',
        'description': 'Description of the podcast',
        'section': 'audio',
    }]


def test_import_old_gpodder_export(tmp_path):
    # Older gPodder versions wrote the description into the text attribute
    filename = tmp_path / 'old.opml'
    filename.write_text(
        '<?xml version="1.0" encoding="utf-8"?>'
        '<opml version="2.0"><body>'
        '<outline title="audio" text="audio">'
        '<outline title="Some Podcast" text="Description of the podcast"'
        ' xmlUrl="https://example.com/feed.xml" type="rss"/>'
        '</outline></body></opml>')

    assert opml.Importer(str(filename)).items == [{
        'url': 'https://example.com/feed.xml',
        'title': 'Some Podcast',
        'description': 'Description of the podcast',
        'section': 'audio',
    }]
