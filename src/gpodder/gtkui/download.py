# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2015 Thomas Perl and the gPodder Team
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

from gpodder import util
from gpodder import download

import gtk
import cgi

import collections

_ = gpodder.gettext


class DownloadStatusModel(gtk.ListStore):
    # Symbolic names for our columns, so we know what we're up to
    C_TASK, C_NAME, C_URL, C_PROGRESS, C_PROGRESS_TEXT, C_ICON_NAME = range(6)

    SEARCH_COLUMNS = (C_NAME, C_URL)

    def __init__(self):
        gtk.ListStore.__init__(self, object, str, str, int, str, str)

        # Set up stock icon IDs for tasks
        self._status_ids = collections.defaultdict(lambda: None)
        self._status_ids[download.DownloadTask.DOWNLOADING] = gtk.STOCK_GO_DOWN
        self._status_ids[download.DownloadTask.DONE] = gtk.STOCK_APPLY
        self._status_ids[download.DownloadTask.FAILED] = gtk.STOCK_STOP
        self._status_ids[download.DownloadTask.CANCELLED] = gtk.STOCK_CANCEL
        self._status_ids[download.DownloadTask.PAUSED] = gtk.STOCK_MEDIA_PAUSE

    def _format_message(self, episode, message, podcast):
        episode = cgi.escape(episode)
        podcast = cgi.escape(podcast)
        return '%s\n<small>%s - %s</small>' % (episode, message, podcast)

    def request_update(self, iter, task=None):
        if task is None:
            # Ongoing update request from UI - get task from model
            task = self.get_value(iter, self.C_TASK)
        else:
            # Initial update request - update non-changing fields
            self.set(iter,
                    self.C_TASK, task,
                    self.C_URL, task.url)

        if task.status == task.FAILED:
            status_message = '%s: %s' % (\
                    task.STATUS_MESSAGE[task.status], \
                    task.error_message)
        elif task.status == task.DOWNLOADING:
            status_message = '%s (%.0f%%, %s/s)' % (\
                    task.STATUS_MESSAGE[task.status], \
                    task.progress*100, \
                    util.format_filesize(task.speed))
        else:
            status_message = task.STATUS_MESSAGE[task.status]

        if task.progress > 0 and task.progress < 1:
            current = util.format_filesize(task.progress*task.total_size, digits=1)
            total = util.format_filesize(task.total_size, digits=1)

            # Remove unit from current if same as in total
            # (does: "12 MiB / 24 MiB" => "12 / 24 MiB")
            current = current.split()
            if current[-1] == total.split()[-1]:
                current.pop()
            current = ' '.join(current)

            progress_message = ' / '.join((current, total))
        elif task.total_size > 0:
            progress_message = util.format_filesize(task.total_size, \
                    digits=1)
        else:
            progress_message = ('unknown size')

        self.set(iter,
                self.C_NAME, self._format_message(task.episode.title,
                    status_message, task.episode.channel.title),
                self.C_PROGRESS, 100.*task.progress, \
                self.C_PROGRESS_TEXT, progress_message, \
                self.C_ICON_NAME, self._status_ids[task.status])

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


class DownloadTaskMonitor(object):
    """A helper class that abstracts download events"""
    def __init__(self, episode, on_can_resume, on_can_pause, on_finished):
        self.episode = episode
        self._status = None
        self._on_can_resume = on_can_resume
        self._on_can_pause = on_can_pause
        self._on_finished = on_finished

    def task_updated(self, task):
        if self.episode.url == task.episode.url and self._status != task.status:
            if task.status in (task.DONE, task.FAILED, task.CANCELLED):
                self._on_finished()
            elif task.status == task.PAUSED:
                self._on_can_resume()
            elif task.status in (task.QUEUED, task.DOWNLOADING):
                self._on_can_pause()
            self._status = task.status


