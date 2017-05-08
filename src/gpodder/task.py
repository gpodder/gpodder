# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2016 Thomas Perl and the gPodder Team
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
#  task.py -- Task queue management
#  Thomas Perl <thp@perli.net>   2007-09-15
#
#  Based on libwget.py (2005-10-29)
#

import logging

from gpodder import util
import gpodder

import math
import threading
import time

logger = logging.getLogger(__name__)

_ = gpodder.gettext

# special activity, which has a configurable worker count limit
# other activities only get 1 worker
DOWNLOAD_ACTIVITY = "Download"


class QueueWorker(object):
    def __init__(self, queue, exit_callback, continue_check_callback, activity):
        self.queue = queue
        self.exit_callback = exit_callback
        self.continue_check_callback = continue_check_callback
        self.activity = activity

    def __repr__(self):
        return "%s (handling %s)" % (threading.current_thread().getName(), self.activity) 

    def run(self):
        logger.info('Starting new thread: %s', self)
        while True:
            if not self.continue_check_callback(self):
                return

            try:
                task = self.queue.get_next(self.activity)
                logger.info('%s is processing: %s', self, task)
                task.run()
                task.recycle()
            except StopIteration as e:
                logger.info('No more tasks for %s to carry out.', self)
                break
        self.exit_callback(self)


class ForceWorker(object):
    def __init__(self, task):
        self.task = task

    def __repr__(self):
        return threading.current_thread().getName()

    def run(self):
        logger.info('Starting new thread: %s', self)
        logger.info('%s is processing: %s', self, self.task)
        self.task.run()


class QueueManager(object):
    def __init__(self, config, queue):
        self._config = config
        self.tasks = queue

        self.worker_threads_access = threading.RLock()
        self.worker_threads = {}

    def __exit_callback(self, worker_thread):
        with self.worker_threads_access:
            if worker_thread.activity in self.worker_threads:
                self.worker_threads[worker_thread.activity].remove(worker_thread)

    def __max_thread_count(self, activity):
        if activity == DOWNLOAD_ACTIVITY:
            if self._config.max_downloads_enabled and self._config.max_downloads > 0:
                max_threads = self._config.max_downloads
            else:
                max_threads = math.inf
        else:
            max_threads = 1
        return max_threads

    def __continue_check_callback(self, worker_thread):
        with self.worker_threads_access:
            if worker_thread.activity in self.worker_threads:
                max_threads = self.__max_thread_count(worker_thread.activity)
                if len(self.worker_threads[worker_thread.activity]) > max_threads:
                    self.worker_threads.remove(worker_thread)
                    return False
                else:
                    return True
            else:
                # stray thread => stop it
                return False

    def __spawn_threads(self, activity=DOWNLOAD_ACTIVITY):
        """Spawn new worker threads if necessary
        """
        with self.worker_threads_access:
            if not self.tasks.has_work(activity):
                return

            max_threads = self.__max_thread_count(activity)
            if len(self.worker_threads.get(activity, [])) < max_threads:
                # We have to create a new thread here, there's work to do
                logger.info('Starting new worker thread for %s.', activity)

                worker = QueueWorker(self.tasks, self.__exit_callback,
                                     self.__continue_check_callback,
                                     activity)
                if activity not in self.worker_threads:
                    self.worker_threads[activity] = [worker]
                else:
                    self.worker_threads[activity].append(worker)
                util.run_in_background(worker.run)

    def update_max_downloads(self):
        self.__spawn_threads()

    def force_start_task(self, task):
        if self.tasks.set_active(task):
            worker = ForceWorker(task)
            util.run_in_background(worker.run)

    def queue_task(self, task):
        """Marks a task as queued
        """
        task.status = Task.QUEUED
        self.__spawn_threads(task.activity)


class TaskCancelledException(Exception):
    pass


class Task(object):
    """An object representing an I/O task

    The task's nature (Download, Sync, SendTo) is given by task.activity

    While the task is in progress, you can access its properties:

        str(task)             # name of the episode
        task.episode          # Episode object of this task
        task.podcast_url      # URL of the podcast this download belongs to
        task.progress         # from 0.0 to 1.0
        task.speed            # in bytes per second (0.0)
        task.status           # current status
        task.status_changed   # True if the status has been changed (see below)
        task.total_size       # in bytes
        task.url              # URL of the episode being downloaded


    You can cancel a running task by setting its status:

        task.status = Task.CANCELLED

    The task will then abort as soon as possible (due to the nature
    of downloading data, this can take a while when the Internet is
    busy).
    TODO: interrupt the worker thread after some time for stuck tasks?

    The "status_changed" attribute gets set to True everytime the
    "status" attribute changes its value. After you get the value of
    the "status_changed" attribute, it is always reset to False:

        if task.status_changed:
            new_status = task.status
            # .. update the UI accordingly ..

    Obviously, this also means that you must have at most *one*
    place in your UI code where you check for status changes and
    broadcast the status updates from there.

    While the task is taking place and after the .run() method
    has finished, you can get the final status to check if the task
    was successful:

        if task.status == Task.DONE:
            # .. everything ok ..
        elif task.status == Task.FAILED:
            # .. an error happened, and the
            #    error_message attribute is set ..
            print task.error_message
        elif task.status == Task.PAUSED:
            # .. user paused the task..
        elif task.status == Task.CANCELLED:
            # .. user cancelled the task..

    Depending on the task, there might be a difference between and pausing,
    e.g. a temporary file gets deleted when cancelling, but does
    not get deleted when pausing.

    Be sure to call .removed_from_list() on this task when removing
    it from the UI, so that it can carry out any pending clean-up
    actions (e.g. removing the temporary file when the task has not
    finished successfully; i.e. task.status != Task.DONE).
    """
    # Possible states a task can be in
    STATUS_MESSAGE = (_('Added'), _('Queued'), _('Active'),
            _('Finished'), _('Failed'), _('Cancelled'), _('Paused'))
    (INIT, QUEUED, ACTIVE, DONE, FAILED, CANCELLED, PAUSED) = list(range(7))

    # Minimum time between progress updates (in seconds)
    MIN_TIME_BETWEEN_UPDATES = 1.

    def __str__(self):
        return self.episode.title

    def __get_episode(self):
        return self.__episode

    episode = property(fget=__get_episode)

    def __get_status(self):
        return self.__status

    def __set_status(self, status):
        if status != self.__status:
            self.__status_changed = True
            self.__status = status

    status = property(fget=__get_status, fset=__set_status)

    def __get_status_changed(self):
        if self.__status_changed:
            self.__status_changed = False
            return True
        else:
            return False

    status_changed = property(fget=__get_status_changed)

    def __get_activity(self):
        return self.__activity

    def __set_activity(self, activity):
        self.__activity = activity

    activity = property(fget=__get_activity, fset=__set_activity)

    def __get_url(self):
        return self.episode.url

    url = property(fget=__get_url)

    def __get_podcast_url(self):
        return self.episode.channel.url

    podcast_url = property(fget=__get_podcast_url)

    @staticmethod
    def status_message(status):
        """ method called to get a string representation of a status.
            Override this in subclasses as needed.
        """
        return STATUS_MESSAGE[status]

    def cancel(self):
        if self.status in (self.ACTIVE, self.QUEUED):
            self.status = self.CANCELLED

    def removed_from_list(self):
        """
        Called to cleanup if necessary.
        """
        if self.status != self.DONE:
            self.cleanup()

    def __init__(self, activity, episode):
        self.__status = Task.INIT
        self.__activity = activity
        self.__episode = episode
        self.__status_changed = True

        self.total_size = 0
        self.progress = 0.0
        self.speed = 0.0
        self.error_message = None
        
        # Variables for speed calculation
        self._start_time = 0
        self._start_blocks = 0
        self._speed_refresh_period = 1

        # Have we already shown this task in a notification?
        self._notification_shown = False

        # Progress update functions
        self._progress_updated = None
        self._last_progress_updated = 0.

    def notify_as_finished(self):
        """
        The UI can call the method "notify_as_finished()" to determine if
        this task still has still to be shown as "finished"
        in a notification window. This will return True only the first time
        it is called when the status is DONE. After returning True once,
        it will always return False afterwards.
        """
        if self.status == Task.DONE:
            if self._notification_shown:
                return False
            else:
                self._notification_shown = True
                return True

        return False

    def notify_as_failed(self):
        """
        Same as notify_as_finished() for failed tasks
        """
        if self.status == Task.FAILED:
            if self._notification_shown:
                return False
            else:
                self._notification_shown = True
                return True

        return False

    def add_progress_callback(self, callback):
        self._progress_updated = callback

    def status_updated(self, count, blockSize, totalSize):
        """
        Call this method from run() to report progress update,
        after updating self.total_size.

        Raises TaskCancelledException if status is cancelled or paused,
        to stop the run() method in its thread.
        Don't catch it.
        """
        if self.total_size > 0:
            self.progress = max(0.0, min(1.0, count*blockSize/self.total_size))
            if self._progress_updated is not None:
                diff = time.time() - self._last_progress_updated
                if diff > self.MIN_TIME_BETWEEN_UPDATES or self.progress == 1.:
                    self._progress_updated(self.progress)
                    self._last_progress_updated = time.time()

        self.calculate_speed(count, blockSize)

        if self.status in (Task.CANCELLED, Task.PAUSED):
            raise TaskCancelledException()

    def calculate_speed(self, count, blockSize):
        """
        Compute download/sync speed.
        Called from status_updated().
        """
        if count % self._speed_refresh_period == 0:
            now = time.time()
            if self._start_time == 0:
                self._start_time = now
                self._start_blocks = count

            passed = now - self._start_time
            if passed > 0:
                speed = ((count-self._start_blocks)*blockSize)/passed
            else:
                speed = 0

            self.speed = float(speed)

    def recycle(self):
        """ hook for subclasses """
        pass

    def cleanup(self):
        """
        hook for subclasses.
        Called on cancel
        """
        pass

    def run(self):
        """ perform the task synchronously """
        # Speed calculation (re-)starts here
        self._start_time = 0
        self._start_blocks = 0

        # If the download has already been cancelled, skip it
        if self.status == Task.CANCELLED:
            self.cleanup()
            self.progress = 0.0
            self.speed = 0.0
            return False

        # We only start this task if its status is "active"
        # FIXME: setting status to ACTIVE afterwards is useless
        if self.status != Task.ACTIVE:
            return False

        # We are running this task right now
        self._notification_shown = False

        # do the actual work in subclass
        try:
            success = self.do_run()
        except TaskCancelledException:
            success = False
            logger.info('Task has been cancelled/paused: %s', self)
            if self.status == Task.CANCELLED:
                self.cleanup()
                self.progress = 0.0

        self.speed = 0.0
        return success

    def do_run(self):
        """
        main method to implement in subclasses.
        @return Success?
        """
        pass

    def post_run(self):
        """ code to run in the GUI Thread after task finished """
        pass