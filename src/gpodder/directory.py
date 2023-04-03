# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2018 The gPodder Team
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


#
# gpodder.directory - Podcast directory and search providers
# Thomas Perl <thp@gpodder.org>; 2014-10-22
#

import urllib.error
import urllib.parse
import urllib.request

import gpodder
from gpodder import opml, util

_ = gpodder.gettext


class DirectoryEntry(object):
    def __init__(self, title, url, image=None, subscribers=-1, description=None):
        self.title = title
        self.url = url
        self.image = image
        self.subscribers = subscribers
        self.description = description


class DirectoryTag(object):
    def __init__(self, tag, weight):
        self.tag = tag
        self.weight = weight


class Provider(object):
    PROVIDER_SEARCH, PROVIDER_URL, PROVIDER_FILE, PROVIDER_TAGCLOUD, PROVIDER_STATIC = list(range(5))

    def __init__(self):
        self.name = ''
        self.kind = self.PROVIDER_SEARCH
        self.icon = None

    def on_search(self, query):
        # Should return a list of DirectoryEntry objects
        raise NotImplemented()

    def on_url(self, url):
        # Should return a list of DirectoryEntry objects
        raise NotImplemented()

    def on_file(self, filename):
        # Should return a list of DirectoryEntry objects
        raise NotImplemented()

    def on_tag(self, tag):
        # Should return a list of DirectoryEntry objects
        raise NotImplemented()

    def on_static(self):
        # Should return a list of DirectoryEntry objects
        raise NotImplemented()

    def get_tags(self):
        # Should return a list of DirectoryTag objects
        raise NotImplemented()


def directory_entry_from_opml(url):
    return [DirectoryEntry(d['title'], d['url'], description=d['description']) for d in opml.Importer(url).items]


def directory_entry_from_mygpo_json(url):
    r = util.urlopen(url)
    if not r.ok:
        raise Exception('%s: %d %s' % (url, r.status_code, r.reason))

    return [DirectoryEntry(d['title'], d['url'], d['logo_url'], d['subscribers'], d['description'])
            for d in r.json()]


class GPodderNetSearchProvider(Provider):
    def __init__(self):
        self.name = _('gpodder.net search')
        self.kind = Provider.PROVIDER_SEARCH
        self.icon = 'directory-gpodder.png'

    def on_search(self, query):
        return directory_entry_from_mygpo_json('http://gpodder.net/search.json?q=' + urllib.parse.quote(query))


class OpmlWebImportProvider(Provider):
    def __init__(self):
        self.name = _('OPML from web')
        self.kind = Provider.PROVIDER_URL
        self.icon = 'directory-opml.png'

    def on_url(self, url):
        return directory_entry_from_opml(url)


class OpmlFileImportProvider(Provider):
    def __init__(self):
        self.name = _('OPML file')
        self.kind = Provider.PROVIDER_FILE
        self.icon = 'directory-opml.png'

    def on_file(self, filename):
        return directory_entry_from_opml(filename)


class GPodderRecommendationsProvider(Provider):
    def __init__(self):
        self.name = _('Getting started')
        self.kind = Provider.PROVIDER_STATIC
        self.icon = 'directory-examples.png'

    def on_static(self):
        return directory_entry_from_opml('http://gpodder.org/directory.opml')


class GPodderNetToplistProvider(Provider):
    def __init__(self):
        self.name = _('gpodder.net Top 50')
        self.kind = Provider.PROVIDER_STATIC
        self.icon = 'directory-toplist.png'

    def on_static(self):
        return directory_entry_from_mygpo_json('http://gpodder.net/toplist/50.json')


class GPodderNetTagsProvider(Provider):
    def __init__(self):
        self.name = _('gpodder.net Tags')
        self.kind = Provider.PROVIDER_TAGCLOUD
        self.icon = 'directory-tags.png'

    def on_tag(self, tag):
        return directory_entry_from_mygpo_json('http://gpodder.net/api/2/tag/%s/50.json' % urllib.parse.quote(tag))

    def get_tags(self):
        url = 'http://gpodder.net/api/2/tags/40.json'

        r = util.urlopen(url)
        if not r.ok:
            raise Exception('%s: %d %s' % (url, r.status_code, r.reason))

        return [DirectoryTag(d['tag'], d['usage']) for d in r.json()]


class SoundcloudSearchProvider(Provider):
    def __init__(self):
        self.name = _('Soundcloud search')
        self.kind = Provider.PROVIDER_SEARCH
        self.icon = 'directory-soundcloud.png'

    def on_search(self, query):
        # XXX: This cross-import of the plugin here is bad, but it
        # works for now (no proper plugin architecture...)
        from gpodder.plugins.soundcloud import search_for_user

        return [DirectoryEntry(entry['username'], entry['permalink_url']) for entry in search_for_user(query)]


class FixedOpmlFileProvider(Provider):
    def __init__(self, filename):
        self.name = _('Imported OPML file')
        self.kind = Provider.PROVIDER_STATIC
        self.icon = 'directory-opml.png'

        self.filename = filename

    def on_static(self):
        return directory_entry_from_opml(self.filename)


PROVIDERS = [
    GPodderRecommendationsProvider,
    None,
    GPodderNetSearchProvider,
    GPodderNetToplistProvider,
    # GPodderNetTagsProvider,
    None,
    OpmlWebImportProvider,
    # OpmlFileImportProvider,
    None,
    SoundcloudSearchProvider,
]
