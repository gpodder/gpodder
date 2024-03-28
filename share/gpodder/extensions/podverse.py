# -*- coding: utf-8 -*-
# Searches podverse (podverse.fm) database for podcasts

# (c) 2024 Eric Le Lay <elelay.fr:contact>
# Released under the same license terms as gPodder itself.

# Inspired by gpodder-core plugin "podverse", by kirbylife <hola@kirbylife.dev>
# https://github.com/gpodder/gpodder-core/blob/master/src/gpodder/plugins/podverse.py

import logging
from urllib.parse import quote_plus

import gpodder
from gpodder.directory import PROVIDERS, DirectoryEntry, Provider
from gpodder.util import urlopen

logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Search Podverse')
__description__ = _('Search podverse podcast index')
__authors__ = 'Eric Le Lay <elelay.fr:contact>'
__doc__ = 'https://gpodder.github.io/docs/extensions/podverse.html'


class PodverseDirectoryProvider(Provider):
    def __init__(self):
        self.name = _('Podverse search')
        self.kind = Provider.PROVIDER_SEARCH
        self.icon = None  # TODO: there is no way for a provider to register a custom icon

    def on_search(self, query):
        # see https://api.podverse.fm/api/v1/swagger#operations-podcast-getPodcasts
        json_url = f"https://api.podverse.fm/api/v1/podcast?page=1&searchTitle={quote_plus(query)}&sort=top-past-week"

        json_data = urlopen(json_url, headers={"accept": "application/json"}).json()

        # contrary to swagger api we get a [results_page, total_length] 2 element list
        # See code in https://github.com/podverse/podverse-api/blob/develop/src/controllers/podcast.ts#L311
        if isinstance(json_data, list) and len(json_data) == 2 and isinstance(json_data[0], list):
            logger.debug("Search for %s yields %i results, of which we display %i",
                query, json_data[1], len(json_data[0]))
            json_data = json_data[0]
        else:
            logger.debug("Search for %s yields %i results", query, len(json_data))

        return [
            DirectoryEntry(e["title"],
                           e["feedUrls"][0]["url"],
                           image=e["imageUrl"],
                           description=e["description"])
            for e in json_data if not e["credentialsRequired"]
        ]


class gPodderExtension:
    """ (un)register a podverse search provider """
    def __init__(self, container):
        pass

    def on_load(self):
        logger.info('Registering Podverse.')
        PROVIDERS.append(None)
        PROVIDERS.append(PodverseDirectoryProvider)

    def on_unload(self):
        logger.info('Unregistering Podverse.')
        try:
            PROVIDERS.remove(PodverseDirectoryProvider)
        except Exception:
            logger.exception("Unable to remove PodverseDirectoryProvider")
