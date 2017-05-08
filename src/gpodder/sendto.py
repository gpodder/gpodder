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

import gpodder

from gpodder import util
from gpodder import services
from gpodder.task import Task, TaskCancelledException

import logging
logger = logging.getLogger(__name__)

import calendar

_ = gpodder.gettext

import os.path
import time

class SendToFailedException(Exception): pass


class SendTo(object):
    def __init__(self,
            download_status_model,
            download_queue_manager):
        self.download_status_model = download_status_model
        self.download_queue_manager = download_queue_manager

    def add_send_to(self, episodes, folder, done_callback=None):
        if episodes:
            for episode in sorted(episodes, key=lambda e: e.pubdate_prop):
                if episode.was_downloaded(and_exists=True):
                    sync_task=SendToTask(episode, folder)
                    sync_task.status=sync_task.QUEUED
                    self.download_status_model.register_task(sync_task)
                    # Executes after task has been registered
                    util.idle_add(self.download_queue_manager.queue_task, sync_task)
        else:
            logger.warning("No episodes to send")

        if done_callback:
            done_callback()


class SendToTask(Task):
    """ An object representing copying an Episode """

    # Possible states this send to task can be in
    STATUS_MESSAGE = (_('Added'), _('Queued'), _('Copying'),
            _('Finished'), _('Failed'), _('Cancelled'), _('Paused'))
    ACTIVITY = "SendTo"

    def cleanup(self):
        # XXX: Should we delete temporary/incomplete files here?
        pass

    def __init__(self, episode, target_folder):
        super(SendToTask, self).__init__(SendToTask.ACTIVITY, episode)

        self.target_folder = target_folder
        self.copy_from = episode.local_filename(create=False)
        assert self.copy_from is not None
        base, extension = os.path.splitext(self.copy_from)
        self.filename = self.build_filename(episode.sync_filename(), extension)

        self.total_size = util.calculate_size(self.copy_from)
        self.buffer_size = 1024*1024 # 1 MiB

    def do_run(self):
        try:
            logger.info('Starting SendToTask')
            self.sendto()
        except TaskCancelledException as e:
            raise
        except Exception as e:
            self.status = Task.FAILED
            logger.error('Send-To failed: %s', str(e), exc_info=True)
            self.error_message = _('Error: %s') % (str(e),)

        if self.status == Task.ACTIVE:
            # Everything went well - we're done
            self.status = Task.DONE
            if self.total_size <= 0:
                self.total_size = util.calculate_size(self.filename)
                logger.info('Total size updated to %d', self.total_size)
            self.progress = 1.0
            return True

        # We finished, but not successfully (at least not really)
        return False

    def sendto(self):
        """ synchronously copy file to target """
        # verify free space
        needed = util.calculate_size(self.copy_from)
        free = util.get_free_disk_space(self.target_folder)
        if free == -1:
            logger.warn('Cannot determine free disk space on device')
        elif needed > free:
            d = {'path': self.destination, 'free': util.format_filesize(free), 'need': util.format_filesize(needed)}
            message =_('Not enough space in %(path)s: %(free)s available, but need at least %(need)s')
            raise SendToFailedException(message % d)

        self.copy_file_progress(self.status_updated)

    def copy_file_progress(self, reporthook):
        try:
            in_file = open(self.copy_from, 'rb')
        except IOError as ioerror:
            d = {'filename': ioerror.filename, 'message': ioerror.strerror}
            message = _('Error opening %(filename)s: %(message)s')
            raise SendToFailedException(message % d)

        copy_to = os.path.join(self.target_folder, self.filename)
        try:
            out_file = open(copy_to, 'wb')
        except (OSError, IOError) as ioerror:
            # Remove characters not supported by VFAT (#282)
            new_filename = re.sub(r"[\"*/:<>?\\|]", "_", self.filename)
            destination = os.path.join(self.target_folder, new_filename)
            if (copy_to == destination):
                d = {'filename': ioerror.filename, 'message': ioerror.strerror}
                message = _('Error opening %(filename)s: %(message)s')
                raise SendToFailedException(message % d)

        logger.info('Copying %s => %s', os.path.basename(self.copy_from), copy_to)

        in_file.seek(0, os.SEEK_END)
        total_bytes = in_file.tell()
        in_file.seek(0)

        bytes_read = 0
        s = in_file.read(self.buffer_size)
        while s:
            bytes_read += len(s)
            try:
                out_file.write(s)
                # debug: slow down to see progress
                # time.sleep(1)
            except IOError as ioerror:
                try:
                    out_file.close()
                except:
                    pass
                try:
                    logger.info('Trying to remove partially copied file: %s' % copy_to)
                    os.unlink( copy_to)
                    logger.info('Yeah! Unlinked %s at least..' % copy_to)
                except:
                    logger.error('Error while trying to unlink %s. OH MY!' % copy_to)
                raise SendToFailedException(ioerror.strerror)
            reporthook(bytes_read, 1, total_bytes)
            s = in_file.read(self.buffer_size)
        out_file.close()
        in_file.close()

    @staticmethod
    def build_filename(filename, extension):
        filename = util.sanitize_filename(filename)
        if not filename.endswith(extension):
            filename += extension
        return filename
