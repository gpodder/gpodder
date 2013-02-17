# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2012 Thomas Perl and the gPodder Team
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


from PySide.QtCore import Slot

from gpodder import util
from gpodder import query

from gpodder import qml
from gpodder.qml.common import EPISODE_LIST_FILTERS, EPISODE_LIST_LIMIT

import logging
logger = logging.getLogger(__name__)


class gPodderEpisodeListModel(qml.model.CommonEpisodeListModel):
    def __init__(self, config, root):
        qml.model.CommonEpisodeListModel.__init__(self, config)
        self._filter = config.ui.qml.state.episode_list_filter
        self._root = root

    def sort(self):
        self._root.main.clearEpisodeListModel()

        @util.run_in_background
        def filter_and_load_episodes():
            caption, eql = EPISODE_LIST_FILTERS[self._filter]

            if eql is None:
                self._filtered = self._objects
            else:
                eql = query.EQL(eql)
                match = lambda episode: eql.match(episode._episode)
                self._filtered = filter(match, self._objects)

            def to_dict(episode):
                return {
                    'episode_id': episode._episode.id,

                    'episode': episode,

                    'title': episode.qtitle,
                    'podcast': episode.qpodcast,
                    'cover_url': episode.qpodcast.qcoverart,
                    'filetype': episode.qfiletype,

                    'duration': episode.qduration,
                    'downloading': episode.qdownloading,
                    'position': episode.qposition,
                    'progress': episode.qprogress,
                    'downloaded': episode.qdownloaded,
                    'isnew': episode.qnew,
                    'archive': episode.qarchive,
                }

            processed = map(to_dict, self._filtered[:EPISODE_LIST_LIMIT])
            self._root.setEpisodeListModel.emit(processed)

            # Keep a reference here to avoid crashes
            self._processed = processed

    @Slot(result=int)
    def getFilter(self):
        return self._filter

    @Slot(int)
    def setFilter(self, filter_index):
        self._config.ui.qml.state.episode_list_filter = filter_index
