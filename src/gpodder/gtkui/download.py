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
#  gpodder.gtkui.download -- Download management in GUIs (2009-08-24)
#  Based on code from gpodder.services (thp, 2007-08-24)
#

import collections
import html
import threading

from gi.repository import Gtk

import gpodder
from gpodder import download, util

_ = gpodder.gettext


class TaskQueue:
    def __init__(self):
        self.lock = threading.Lock()
        self.tasks = list()

    def __len__(self):
        with self.lock:
            return len(self.tasks)

    def add_task(self, task):
        with self.lock:
            if task not in self.tasks:
                self.tasks.append(task)

    def remove_task(self, task):
        with self.lock:
            try:
                self.tasks.remove(task)
                return True
            except ValueError:
                # already dequeued
                return False

    def pop(self):
        with self.lock:
            if len(self.tasks) == 0:
                return None
            task = self.tasks.pop(0)
            return task

    def move_after(self, task, after):
        with self.lock:
            try:
                index = self.tasks.index(after)
                self.tasks.remove(task)
                self.tasks.insert(index + 1, task)
            except ValueError:
                pass

    def move_before(self, task, before):
        with self.lock:
            try:
                index = self.tasks.index(before)
                self.tasks.remove(task)
                self.tasks.insert(index, task)
            except ValueError:
                pass


class DownloadStatusModel:
    # Symbolic names for our columns, so we know what we're up to
    C_TASK, C_NAME, C_URL, C_PROGRESS, C_PROGRESS_TEXT, C_ICON_NAME = list(range(6))

    SEARCH_COLUMNS = (C_NAME, C_URL)

    def __init__(self):
        self.list = Gtk.ListStore(object, str, str, int, str, str)
        self.work_queue = TaskQueue()

        # Set up stock icon IDs for tasks
        self._status_ids = collections.defaultdict(lambda: None)
        self._status_ids[download.DownloadTask.DOWNLOADING] = 'go-down'
        self._status_ids[download.DownloadTask.DONE] = Gtk.STOCK_APPLY
        self._status_ids[download.DownloadTask.FAILED] = 'dialog-error'
        self._status_ids[download.DownloadTask.CANCELLED] = 'media-playback-stop'
        self._status_ids[download.DownloadTask.PAUSED] = 'media-playback-pause'

    def get_model(self):
        return self.list

    def _format_message(self, episode, message, podcast):
        episode = html.escape(episode)
        podcast = html.escape(podcast)
        message = html.escape(message)
        return '%s\n<small>%s - %s</small>' % (episode, message, podcast)

    def request_update(self, iter, task=None):
        if task is None:
            # Ongoing update request from UI - get task from model
            task = self.list.get_value(iter, self.C_TASK)
        else:
            # Initial update request - update non-changing fields
            self.list.set(iter,
                    self.C_TASK, task,
                    self.C_URL, task.url)

        if task.status == task.FAILED:
            status_message = '%s: %s' % (
                    task.STATUS_MESSAGE[task.status],
                    task.error_message)
        elif task.status == task.DOWNLOADING:
            status_message = '%s (%.0f%%, %s/s)' % (
                    task.STATUS_MESSAGE[task.status],
                    task.progress * 100,
                    util.format_filesize(task.speed))
        else:
            status_message = task.STATUS_MESSAGE[task.status]

        if task.progress > 0 and task.progress < 1:
            current = util.format_filesize(task.progress * task.total_size, digits=1)
            total = util.format_filesize(task.total_size, digits=1)

            # Remove unit from current if same as in total
            # (does: "12 MiB / 24 MiB" => "12 / 24 MiB")
            current = current.split()
            if current[-1] == total.split()[-1]:
                current.pop()
            current = ' '.join(current)

            progress_message = ' / '.join((current, total))
        elif task.total_size > 0:
            progress_message = util.format_filesize(task.total_size,
                    digits=1)
        else:
            progress_message = ('unknown size')

        self.list.set(iter,
                self.C_NAME, self._format_message(task.episode.title,
                    status_message, task.episode.channel.title),
                self.C_PROGRESS, 100. * task.progress,
                self.C_PROGRESS_TEXT, progress_message,
                self.C_ICON_NAME, self._status_ids[task.status])

    def __add_new_task(self, task):
        iter = self.list.append()
        self.request_update(iter, task)

    def register_task(self, task):
        self.work_queue.add_task(task)
        util.idle_add(self.__add_new_task, task)

    def queue_task(self, task):
        with task:
            task.status = download.DownloadTask.QUEUED
        self.work_queue.add_task(task)

    def tell_all_tasks_to_quit(self):
        for row in self.list:
            task = row[DownloadStatusModel.C_TASK]
            if task is not None:
                with task:
                    # Pause currently-running (and queued) downloads
                    if task.status in (task.QUEUED, task.DOWNLOADING):
                        task.status = task.PAUSING

                    # Delete cancelled and failed downloads
                    if task.status in (task.CANCELLED, task.FAILED):
                        task.removed_from_list()

    def are_downloads_in_progress(self):
        """
        Returns True if there are any downloads in the
        QUEUED or DOWNLOADING status, False otherwise.
        """
        for row in self.list:
            task = row[DownloadStatusModel.C_TASK]
            if task is not None and \
                    task.status in (task.DOWNLOADING,
                                    task.QUEUED):
                return True

        return False

    def move_after(self, iter, position):
        self.list.move_after(iter, position)
        iter_task = self.list.get_value(iter, DownloadStatusModel.C_TASK)
        pos_task = self.list.get_value(position, DownloadStatusModel.C_TASK)
        self.work_queue.move_after(iter_task, pos_task)

    def move_before(self, iter, position):
        self.list.move_before(iter, position)
        iter_task = self.list.get_value(iter, DownloadStatusModel.C_TASK)
        pos_task = self.list.get_value(position, DownloadStatusModel.C_TASK)
        self.work_queue.move_before(iter_task, pos_task)

    def has_work(self):
        return len(self.work_queue) > 0

    def available_work_count(self):
        return len(self.work_queue)

    def get_next(self):
        return self.work_queue.pop()

    def set_downloading(self, task):
        # return False if Task was already dequeued by get_next
        return self.work_queue.remove_task(task)


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
