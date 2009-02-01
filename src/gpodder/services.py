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
#  services.py -- Core Services for gPodder
#  Thomas Perl <thp@perli.net>   2007-08-24
#
#

from gpodder.liblogger import log
from gpodder.libgpodder import gl

from gpodder import util
from gpodder import resolver

import gtk
import gobject

import threading
import time
import urllib2
import os
import os.path


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


class DependencyManager(object):
    def __init__(self):
        self.dependencies = []

    def depend_on(self, feature_name, description, modules, tools):
        self.dependencies.append([feature_name, description, modules, tools])

    def modules_available(self, modules):
        """
        Receives a list of modules and checks if each
        of them is available. Returns a tuple with the
        first item being a boolean variable that is True
        when all required modules are available and False
        otherwise. The second item is a dictionary that
        lists every module as key with the available as
        boolean value.
        """
        result = {}
        all_available = True
        for module in modules:
            try:
                __import__(module)
                result[module] = True
            except:
                result[module] = False
                all_available = False

        return (all_available, result)

    def tools_available(self, tools):
        """
        See modules_available.
        """
        result = {}
        all_available = True
        for tool in tools:
            if util.find_command(tool):
                result[tool] = True
            else:
                result[tool] = False
                all_available = False

        return (all_available, result)

    def get_model(self):
        # Name, Description, Available (str), Available (bool), Missing (str)
        model = gtk.ListStore(str, str, str, bool, str)
        for feature_name, description, modules, tools in self.dependencies:
            modules_available, module_info = self.modules_available(modules)
            tools_available, tool_info = self.tools_available(tools)

            available = modules_available and tools_available
            if available:
                available_str = _('Available')
            else:
                available_str = _('Missing dependencies')

            missing_str = []
            for module in modules:
                if not module_info[module]:
                    missing_str.append(_('Python module "%s" not installed') % module)
            for tool in tools:
                if not tool_info[tool]:
                    missing_str.append(_('Command "%s" not installed') % tool)
            missing_str = '\n'.join(missing_str)

            model.append([feature_name, description, available_str, available, missing_str])
        return model


dependency_manager = DependencyManager()


# Register non-module-specific dependencies here
dependency_manager.depend_on(_('Bluetooth file transfer'), _('Send podcast episodes to Bluetooth devices. Needs Python Bluez bindings.'), ['bluetooth'], ['bluetooth-sendto'])
dependency_manager.depend_on(_('Update tags on MP3 files'), _('Support the "Update tags after download" option for MP3 files.'), ['eyeD3'], [])
dependency_manager.depend_on(_('Update tags on OGG files'), _('Support the "Update tags after download" option for OGG files.'), [], ['vorbiscomment'])


class CoverDownloader(ObservableService):
    """
    This class manages downloading cover art and notification
    of other parts of the system. Downloading cover art can
    happen either synchronously via get_cover() or in
    asynchronous mode via request_cover(). When in async mode,
    the cover downloader will send the cover via the
    'cover-available' message (via the ObservableService).
    """

    # Maximum width/height of the cover in pixels
    MAX_SIZE = 400

    def __init__(self):
        signal_names = ['cover-available', 'cover-removed']
        ObservableService.__init__(self, signal_names)

    def request_cover(self, channel, custom_url=None):
        """
        Sends an asynchronous request to download a
        cover for the specific channel.

        After the cover has been downloaded, the
        "cover-available" signal will be sent with
        the channel url and new cover as pixbuf.

        If you specify a custom_url, the cover will
        be downloaded from the specified URL and not
        taken from the channel metadata.
        """
        log('cover download request for %s', channel.url, sender=self)
        args = [channel, custom_url, True]
        threading.Thread(target=self.__get_cover, args=args).start()

    def get_cover(self, channel, custom_url=None, avoid_downloading=False):
        """
        Sends a synchronous request to download a
        cover for the specified channel.

        The cover will be returned to the caller.

        The custom_url has the same semantics as
        in request_cover().

        The optional parameter "avoid_downloading",
        when true, will make sure we return only
        already-downloaded covers and return None
        when we have no cover on the local disk.
        """
        (url, pixbuf) = self.__get_cover(channel, custom_url, False, avoid_downloading)
        return pixbuf

    def remove_cover(self, channel):
        """
        Removes the current cover for the channel
        so that a new one is downloaded the next
        time we request the channel cover.
        """
        util.delete_file(channel.cover_file)
        self.notify('cover-removed', channel.url)

    def replace_cover(self, channel, custom_url=None):
        """
        This is a convenience function that deletes
        the current cover file and requests a new
        cover from the URL specified.
        """
        self.remove_cover(channel)
        self.request_cover(channel, custom_url)

    def __get_cover(self, channel, url, async=False, avoid_downloading=False):
        if not async and avoid_downloading and not os.path.exists(channel.cover_file):
            return (channel.url, None)

        loader = gtk.gdk.PixbufLoader()
        pixbuf = None

        if not os.path.exists(channel.cover_file):
            if url is None:
                url = channel.image

            new_url = resolver.get_real_cover(channel.url)
            if new_url is not None:
                url = new_url

            if url is not None:
                image_data = None
                try:
                    log('Trying to download: %s', url, sender=self)

                    image_data = urllib2.urlopen(url).read()
                except:
                    log('Cannot get image from %s', url, sender=self)
             
                if image_data is not None:
                    log('Saving image data to %s', channel.cover_file, sender=self)
                    fp = open(channel.cover_file, 'wb')
                    fp.write(image_data)
                    fp.close()

        if os.path.exists(channel.cover_file):
            try:
                loader.write(open(channel.cover_file, 'rb').read())
                loader.close()
                pixbuf = loader.get_pixbuf()
            except:
                log('Data error while loading %s', channel.cover_file, sender=self)
        else:
            try:
                loader.close()
            except:
                pass

        if pixbuf is not None:
            new_pixbuf = util.resize_pixbuf_keep_ratio(pixbuf, self.MAX_SIZE, self.MAX_SIZE)
            if new_pixbuf is not None:
                # Save the resized cover so we do not have to
                # resize it next time we load it
                new_pixbuf.save(channel.cover_file, 'png')
                pixbuf = new_pixbuf

        if async:
            self.notify('cover-available', channel.url, pixbuf)
        else:
            return (channel.url, pixbuf)

cover_downloader = CoverDownloader()


class DownloadStatusManager(ObservableService):
    COLUMN_NAMES = { 0: 'episode', 1: 'speed', 2: 'progress', 3: 'url' }
    COLUMN_TYPES = ( gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_FLOAT, gobject.TYPE_STRING )
    PROGRESS_HOLDDOWN_TIMEOUT = 1

    def __init__( self):
        self.status_list = {}
        self.next_status_id = 0

        self.last_progress_status = (0, 0)
        self.last_progress_update = 0
        
        # use to correctly calculate percentage done
        self.downloads_done_bytes = 0
        
        self.max_downloads = gl.config.max_downloads
        self.semaphore = threading.Semaphore( self.max_downloads)

        self.tree_model = gtk.ListStore( *self.COLUMN_TYPES)
        self.tree_model_lock = threading.Lock()

        # batch add in progress?
        self.batch_mode_enabled = False
        # we set this flag if we would notify inside batch mode
        self.batch_mode_notify_flag = False

        # Used to notify all threads that they should
        # re-check if they can acquire the lock
        self.notification_event = threading.Event()
        self.notification_event_waiters = 0
        
        signal_names = ['list-changed', 'progress-changed', 'progress-detail', 'download-complete']
        ObservableService.__init__(self, signal_names)

    def start_batch_mode(self):
        """
        This is called when we are going to add multiple
        episodes to our download list, and do not want to
        notify the GUI for every single episode.

        After all episodes have been added, you MUST call
        the end_batch_mode() method to trigger a notification.
        """
        self.batch_mode_enabled = True

    def end_batch_mode(self):
        """
        This is called after multiple episodes have been
        added when start_batch_mode() has been called before.

        This sends out a notification that the list has changed.
        """
        self.batch_mode_enabled = False
        if self.batch_mode_notify_flag:
            self.notify('list-changed')
        self.batch_mode_notify_flag = False

    def notify_progress(self, force=False):
        now = (self.count(), self.average_progress())
        
        next_progress_update = self.last_progress_update + self.PROGRESS_HOLDDOWN_TIMEOUT

        if force or (now != self.last_progress_status and \
                time.time() > next_progress_update):
            self.notify( 'progress-changed', *now)
            self.last_progress_status = now
            self.last_progress_update = time.time()

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
        if self.batch_mode_enabled:
            self.batch_mode_notify_flag = True
        else:
            self.notify('list-changed')
        self.tree_model_lock.release()

    def remove_download_id( self, id):
        if not id in self.status_list:
            return
        iter = self.status_list[id]['iter']
	if iter is not None:
            self.tree_model_lock.acquire()
            util.idle_add(self.remove_iter, iter)
            self.tree_model_lock.release()
            self.status_list[id]['iter'] = None
            self.status_list[id]['thread'].cancel()
            del self.status_list[id]
            if not self.has_items():
                # Reset the counter now
                self.downloads_done_bytes = 0
        if self.batch_mode_enabled:
            self.batch_mode_notify_flag = True
        else:
            self.notify('list-changed')
        self.notify_progress(force=True)

    def count( self):
        return len(self.status_list)

    def has_items( self):
        return self.count() > 0
    
    def average_progress( self):
        if not len(self.status_list):
            return 0

        done = sum(status['progress']/100. * status['thread'].total_size for status in self.status_list.values())
        total = sum(status['thread'].total_size for status in self.status_list.values())
        if total + self.downloads_done_bytes == 0:
            return 0
        return float(done + self.downloads_done_bytes) / float(total + self.downloads_done_bytes) * 100

    def total_speed(self):
        if not len(self.status_list):
            return 0

        return sum(status['thread'].speed_value for status in self.status_list.values())

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
        for element in self.status_list.keys():
            # We need this, because status_list is modified from other threads
            if element in self.status_list:
                try:
                    thread = self.status_list[element]['thread']
                except:
                    thread = None

                if thread is not None and thread.url == url:
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
            if thread is not None and thread.url == url:
                self.remove_download_id( element)
                return True

        return False


download_status_manager = DownloadStatusManager()

