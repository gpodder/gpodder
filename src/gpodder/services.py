
#
# gPodder (a media aggregator / podcast client)
# Copyright (C) 2005-2007 Thomas Perl <thp at perli.net>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, 
# MA  02110-1301, USA.
#


#
#  services.py -- Core Services for gPodder
#  Thomas Perl <thp@perli.net>   2007-ß8-24
#
#

from gpodder.liblogger import log

from gpodder import libgpodder

import gtk
import gobject

import threading


class DownloadStatusManager( object):
    COLUMN_NAMES = { 0: 'episode', 1: 'speed', 2: 'progress', 3: 'url' }
    COLUMN_TYPES = ( gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_STRING )

    def __init__( self):
        self.status_list = {}
        self.next_status_id = 0

        self.last_progress_status  = ( 0, 0 )
        
        self.max_downloads = libgpodder.gPodderLib().max_downloads
        self.semaphore = threading.Semaphore( self.max_downloads)

        self.tree_model = gtk.ListStore( *self.COLUMN_TYPES)
        self.tree_model_lock = threading.Lock()

        self.observers = { 'list-changed': [], 'progress-changed': [] }


    def register( self, signal_name, observer):
        if signal_name in self.observers:
            if not observer in self.observers[signal_name]:
                self.observers[signal_name].append( observer)
            else:
                log( 'Observer already added to signal "%s".', signal_name, sender = self)
        else:
            log( 'Signal "%s" is not available for registration.', signal_name, sender = self)

    def notify( self, signal_name, *args):
        if signal_name in self.observers:
            for observer in self.observers[signal_name]:
                gobject.idle_add( observer, *args)
        else:
            log( 'Signal "%s" is not available for notification.', signal_name, sender = self)


    def notify_progress( self):
        now = ( self.count(), self.average_progress() )
        
        if now != self.last_progress_status:
            self.notify( 'progress-changed', *now)
            self.last_progress_status = now

    def s_acquire( self):
        if not libgpodder.gPodderLib().max_downloads_enabled:
            return False

        # Release queue slots if user has enabled more slots
        while self.max_downloads < libgpodder.gPodderLib().max_downloads:
            self.semaphore.release()
            self.max_downloads += 1

        # Acquire queue slots if user has decreased the slots
        while self.max_downloads > libgpodder.gPodderLib().max_downloads:
            self.semaphore.acquire()
            self.max_downloads -= 1

        return self.semaphore.acquire()

    def s_release( self):
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
        self.status_list[id] = { 'iter': self.tree_model.append(), 'thread': thread, 'progress': 0 }
        self.notify( 'list-changed')
        self.tree_model_lock.release()

    def remove_download_id( self, id):
        if not id in self.status_list:
            return
        iter = self.status_list[id]['iter']
	if iter != None:
            self.tree_model_lock.acquire()
            gobject.idle_add( self.remove_iter, iter)
            self.tree_model_lock.release()
            self.status_list[id]['iter'] = None
            self.status_list[id]['thread'].cancel()
            del self.status_list[id]
        self.notify( 'list-changed')
        self.notify_progress()

    def count( self):
        return len(self.status_list)

    def has_items( self):
        return self.count() > 0
    
    def average_progress( self):
        if not len(self.status_list):
            return 0

        return sum( [ status['progress'] for status in self.status_list.values() ]) / len( self.status_list)

    def update_status( self, id, **kwargs):
        if not id in self.status_list:
            return

        if 'progress' in kwargs:
            self.status_list[id]['progress'] = kwargs['progress']

        self.notify_progress()

        iter = self.status_list[id]['iter']
        if iter:
            self.tree_model_lock.acquire()
            for ( column, key ) in self.COLUMN_NAMES.items():
                if key in kwargs:
                    gobject.idle_add( self.tree_model.set, iter, column, kwargs[key])
            self.tree_model_lock.release()

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
        gobject.idle_add( self.tree_model.clear)

    def get_url_by_iter( self, iter):
        result = self.tree_model.get_value( iter, 3)
        return result

    def cancel_by_url( self, url):
        for element in self.status_list:
	    thread = self.status_list[element]['thread']
	    if thread != None and thread.url == url:
                self.remove_download_id( element)
		return True
        
        return False


download_status_manager = DownloadStatusManager()

