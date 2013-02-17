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

import cgi
import urllib

import logging
logger = logging.getLogger(__name__)

from PySide.QtCore import QObject, Property, Signal, Slot
from PySide.QtGui import QSortFilterProxyModel

from gpodder import qml
from gpodder.qml.model import convert


class gPodderEpisodeListModel(qml.model.CommonEpisodeListModel):
    def __init__(self, config):
        qml.model.CommonEpisodeListModel.__init__(self, config)
        self._filter = config.ui.qml_desktop.state.episode_list_filter

    def sort(self):
#        caption, eql = EPISODE_LIST_FILTERS[self._filter]
#
#        if eql is None:
#            self._filtered = self._objects
#        else:
#            eql = query.EQL(eql)
#            match = lambda episode: eql.match(episode._episode)
#            self._filtered = filter(match, self._objects)
        self._filtered = sorted(self._objects)
        self.reset()
#        print("myModel:")
#        print(self.columnCount(QModelIndex()))

#    @Slot(result=int)
#    def getFilter(self):
#        return self._filter
#
#    @Slot(int)
#    def setFilter(self, filter_index):
#        self._config.ui.qml_desktop.state.episode_list_filter = filter_index

#    def data(self, index, role):
#        if index.isValid():
#            if role == Qt.DisplayRole:
#                return self.get_object(index)
#            elif role == Qt.DecorationRole:
#                return self.get_object(index).qsection
#            elif role == 2:
#                return self.get_object(index).qtitle
#            elif role == 3:
#                return self.get_object(index).qfilesize
#            elif role == 4:
#                return self.get_object(index).qduration
#            elif role == 5:
#                return self.get_object(index).qpubdate
#        return None


class SortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        QSortFilterProxyModel.__init__(self, parent)

    @Slot(int, result=QObject)
    def get(self, index):
        return self.sourceModel().get(index)

    @Slot(result=int)
    def sectionCount(self):
        return self.sourceModel().sectionCount()


class OmplPodcast(QObject):
    changed = Signal()

    def __init__(self, omplItem):
        QObject.__init__(self)
        self.checked = False
        self.title = omplItem['title']
        self.description = omplItem['description']
        self.url = omplItem['url']

    @classmethod
    def sort_key(cls, podcast):
        return (podcast.title)

    def _title(self):
        return convert(self.title)

    qtitle = Property(unicode, _title, notify=changed)

    def _checked(self):
        return self.checked

    qchecked = Property(bool, _checked, notify=changed)

    def _description(self):
        return convert(self.description)

    qdescription = Property(unicode, _description, notify=changed)

    @Slot(bool)
    def setChecked(self, checked):
        self.checked = checked
        self.changed.emit()


class OpmlListModel(qml.model.gPodderPodcastListModel):
    def __init__(self, importer):
        qml.model.gPodderPodcastListModel.__init__(self)

        for channel in importer.items:
            self.append(OmplPodcast(channel))

    def _format_channel(self, channel):
        title = cgi.escape(urllib.unquote_plus(channel['title']))
        description = cgi.escape(channel['description'])
        return '<b>%s</b>\n%s' % (title, description)

    def sort(self):
        self._objects = sorted(self._objects, key=OmplPodcast.sort_key)
        self.reset()

    @Slot(bool)
    def setCheckedAll(self, checked):
        for channel in self.get_objects():
            channel.setChecked(checked)

    def getSelected(self):
        selected = []
        for channel in self.get_objects():
            if channel.checked == True:
                selected.append(channel)

        return selected
