# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2008 Thomas Perl and the gPodder Team
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
#  services.py -- Core Services for gPodder
#  Thomas Perl <thp@perli.net>   2007-08-24
#
#

from gpodder.liblogger import log
from gpodder.libgpodder import gl

from gpodder import util

import gtk
import gobject

import threading


class ObservableService(object):
    def __init__(self, signal_names=[]):
        self.observers = {}
        for signal in signal_names:
            self.observers[signal] = []

    def register(self, signal_name, observer):
        if signal_name in self.observers:
            if not observer in self.observers[signal_name]:
                self.observers[signal_name].append(observer)
            else:
                log('Observer already added to signal "%s".', signal_name, sender=self)
        else:
            log('Signal "%s" is not available for registration.', signal_name, sender=self)

    def unregister(self, signal_name, observer):
        if signal_name in self.observers:
            if observer in self.observers[signal_name]:
                self.observers[signal_name].remove(observer)
            else:
                log('Observer could not be removed from signal "%s".', signal_name, sender=self)
        else:
            log('Signal "%s" is not available for un-registration.', signal_name, sender=self)

    def notify(self, signal_name, *args):
        if signal_name in self.observers:
            for observer in self.observers[signal_name]:
                util.idle_add(observer, *args)
        else:
            log('Signal "%s" is not available for notification.', signal_name, sender=self)


class DownloadStatusManager(ObservableService):
    COLUMN_NAMES = { 0: 'episode', 1: 'speed', 2: 'progress', 3: 'url' }
    COLUMN_TYPES = ( gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_FLOAT, gobject.TYPE_STRING )

    def __init__( self):
        self.status_list = {}
        self.next_status_id = 0

        self.last_progress_status  = ( 0, 0 )
        
        # use to correctly calculate percentage done
        self.downloads_done_bytes = 0
        
        self.max_downloads = gl.config.max_downloads
        self.semaphore = threading.Semaphore( self.max_downloads)

        self.tree_model = gtk.ListStore( *self.COLUMN_TYPES)
        self.tree_model_lock = threading.Lock()

        # Used to notify all threads that they should
        # re-check if they can acquire the lock
        self.notification_event = threading.Event()
        self.notification_event_waiters = 0
        
        signal_names = ['list-changed', 'progress-changed', 'progress-detail', 'download-complete']
        ObservableService.__init__(self, signal_names)

    def notify_progress( self):
        now = ( self.count(), self.average_progress() )
        
        if now != self.last_progress_status:
            self.notify( 'progress-changed', *now)
            self.last_progress_status = now

    def s_acquire( self):
        if not gl.config.max_downloads_enabled:
            return False
        
        # Acquire queue slots if user has decreased the slots
        while self.max_downloads > gl.config.max_downloads:
            self.semaphore.acquire()
            self.max_downloads -= 1

        # Make sure we update the maximum number of downloads
        self.update_max_downloads()

        while self.semaphore.acquire(False) == False:
            self.notification_event_waiters += 1
            self.notification_event.wait(2.)
            self.notification_event_waiters -= 1

            # If we are the last thread that woke up from
            # the notification_event, clear the flag here
            if self.notification_event_waiters == 0:
                self.notification_event.clear()
                
            # If the user has change the config option since the
            # last time we checked, return false and start download
            if not gl.config.max_downloads_enabled:
                return False

        # If we land here, we've acquired exactly the one we need
        return True
    
    def update_max_downloads(self):
        # Release queue slots if user has enabled more slots
        while self.max_downloads < gl.config.max_downloads:
            self.semaphore.release()
            self.max_downloads += 1

        # Notify all threads that the limit might have been changed
        self.notification_event.set()

    def s_release( self, acquired = True):
        if acquired:
            self.semaphore.release()

    def reserve_download_id( self):
        id = self.next_status_id
	self.next_status_id = id + 1
	return id

    def remove_iter( self, iter):
        self.tree_model.remove( iter)
        return False

    def register_download_id( self, id, thread):
        self.tree_model_lock.acquire()
        self.status_list[id] = { 'iter': self.tree_model.append(), 'thread': thread, 'progress': 0.0, 'speed': _('Queued'), }
        self.notify( 'list-changed')
        self.tree_model_lock.release()

    def remove_download_id( self, id):
        if not id in self.status_list:
            return
        iter = self.status_list[id]['iter']
	if iter != None:
            self.tree_model_lock.acquire()
            util.idle_add(self.remove_iter, iter)
            self.tree_model_lock.release()
            self.status_list[id]['iter'] = None
            self.status_list[id]['thread'].cancel()
            del self.status_list[id]
            if not self.has_items():
                # Reset the counter now
                self.downloads_done_bytes = 0
        self.notify( 'list-changed')
        self.notify_progress()

    def count( self):
        return len(self.status_list)

    def has_items( self):
        return self.count() > 0
    
    def average_progress( self):
        if not len(self.status_list):
            return 0

        done = sum(status['progress']/100. * status['thread'].total_size for status in self.status_list.values())
        total = sum(status['thread'].total_size for status in self.status_list.values())
        return float(done + self.downloads_done_bytes) / float(total + self.downloads_done_bytes) * 100

    def update_status( self, id, **kwargs):
        if not id in self.status_list:
            return

        iter = self.status_list[id]['iter']
        if iter:
            self.tree_model_lock.acquire()
            for ( column, key ) in self.COLUMN_NAMES.items():
                if key in kwargs:
                    util.idle_add(self.tree_model.set, iter, column, kwargs[key])
                    self.status_list[id][key] = kwargs[key]
            self.tree_model_lock.release()

        if 'progress' in kwargs and 'speed' in kwargs and 'url' in self.status_list[id]:
            self.notify( 'progress-detail', self.status_list[id]['url'], kwargs['progress'], kwargs['speed'])

        self.notify_progress()
        
    def download_completed(self, id):
        if id in self.status_list:
            self.notify('download-complete', self.status_list[id]['episode'])
            self.downloads_done_bytes += self.status_list[id]['thread'].total_size

    def request_progress_detail( self, url):
        for status in self.status_list.values():
            if 'url' in status and status['url'] == url and 'progress' in status and 'speed' in status:
                self.notify( 'progress-detail', url, status['progress'], status['speed'])

    def is_download_in_progress( self, url):
        for element in self.status_list:
	    thread = self.status_list[element]['thread']
	    if thread != None and thread.url == url:
	        return True
	
	return False

    def cancel_all( self):
        for element in self.status_list:
	    self.status_list[element]['iter'] = None
	    self.status_list[element]['thread'].cancel()
        # clear the tree model after cancelling
        util.idle_add(self.tree_model.clear)
        self.downloads_done_bytes = 0

    def cancel_by_url( self, url):
        for element in self.status_list:
	    thread = self.status_list[element]['thread']
	    if thread != None and thread.url == url:
                self.remove_download_id( element)
		return True
        
        return False


download_status_manager = DownloadStatusManager()

