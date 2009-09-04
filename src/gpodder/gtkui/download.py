# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
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
#  gpodder.gtkui.download -- Download management in GUIs (2009-08-24)
#  Based on code from gpodder.services (thp, 2007-08-24)
#

import gpodder
from gpodder.liblogger import log

from gpodder import util
from gpodder import download

import gtk
import gobject

import collections

_ = gpodder.gettext


class DownloadStatusModel(gtk.ListStore):
    # Symbolic names for our columns, so we know what we're up to
    C_TASK, C_NAME, C_URL, C_PROGRESS, C_PROGRESS_TEXT, C_SIZE_TEXT, \
            C_ICON_NAME, C_SPEED_TEXT, C_STATUS_TEXT = range(9)

    SEARCH_COLUMNS = (C_NAME, C_URL)

    def __init__(self):
        gtk.ListStore.__init__(self, object, str, str, int, str, str, str, str, str)

        # Set up stock icon IDs for tasks
        self._status_ids = collections.defaultdict(lambda: None)
        self._status_ids[download.DownloadTask.DOWNLOADING] = gtk.STOCK_GO_DOWN
        self._status_ids[download.DownloadTask.DONE] = gtk.STOCK_APPLY
        self._status_ids[download.DownloadTask.FAILED] = gtk.STOCK_STOP
        self._status_ids[download.DownloadTask.CANCELLED] = gtk.STOCK_CANCEL
        self._status_ids[download.DownloadTask.PAUSED] = gtk.STOCK_MEDIA_PAUSE

    def request_update(self, iter, task=None):
        if task is None:
            # Ongoing update request from UI - get task from model
            task = self.get_value(iter, self.C_TASK)
        else:
            # Initial update request - update non-changing fields
            self.set(iter,
                    self.C_TASK, task,
                    self.C_NAME, str(task),
                    self.C_URL, task.url)

        if task.status == task.FAILED:
            status_message = _('Failed: %s') % (task.error_message,)
        else:
            status_message = task.STATUS_MESSAGE[task.status]

        if task.status == task.DOWNLOADING:
            speed_message = '%s/s' % util.format_filesize(task.speed)
        else:
            speed_message = ''

        self.set(iter,
                self.C_PROGRESS, 100.*task.progress,
                self.C_PROGRESS_TEXT, '%.0f%%' % (task.progress*100.,),
                self.C_SIZE_TEXT, util.format_filesize(task.total_size),
                self.C_ICON_NAME, self._status_ids[task.status],
                self.C_SPEED_TEXT, speed_message,
                self.C_STATUS_TEXT, status_message)

    def __add_new_task(self, task):
        iter = self.append()
        self.request_update(iter, task)

    def register_task(self, task):
        util.idle_add(self.__add_new_task, task)

    def tell_all_tasks_to_quit(self):
        for row in self:
            task = row[DownloadStatusModel.C_TASK]
            if task is not None:
                # Pause currently-running (and queued) downloads
                if task.status in (task.QUEUED, task.DOWNLOADING):
                    task.status = task.PAUSED

                # Delete cancelled and failed downloads
                if task.status in (task.CANCELLED, task.FAILED):
                    task.removed_from_list()

    def are_downloads_in_progress(self):
        """
        Returns True if there are any downloads in the
        QUEUED or DOWNLOADING status, False otherwise.
        """
        for row in self:
            task = row[DownloadStatusModel.C_TASK]
            if task is not None and \
                    task.status in (task.DOWNLOADING, \
                                    task.QUEUED):
                return True

        return False

    def cancel_by_url(self, url):
        for row in self:
            task = row[DownloadStatusModel.C_TASK]
            if task is not None and task.url == url and \
                    task.status in (task.DOWNLOADING, \
                                    task.QUEUED):
                task.status = task.CANCELLED
                return True

        return False

