
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
#  libwget.py -- wget download functionality
#  thomas perl <thp@perli.net>   20051029
#
#

from os.path import basename
from os.path import dirname

from os import system
from os import kill
from threading import Thread
from threading import Lock
from threading import Semaphore
from shutil import move

from gpodder import util
from gpodder import services

from liblogger import log

import libgpodder

import signal

import popen2
import re
import md5

import gtk
import gobject

class downloadThread( object):
    def __init__( self, url, filename, ready_event = None, cutename = _("unknown"), channelitem = None, item = None, localdb = None):
        self.url = url.replace( "%20", " ")
        
        self.filename = filename
        self.tempname = dirname( self.filename) + "/.tmp-" + basename( self.filename)
        
        self.ready_event = ready_event
        self.pid= -1
        self.percentage = 0.0
        self.speed = _("unknown")
        
        self.thread = None
        self.result = -1

	self.cutename = cutename

        self.channelitem = channelitem
        self.item = item
        self.localdb = localdb

        self.is_cancelled = False

	self.download_id = services.download_status_manager.reserve_download_id()
	services.download_status_manager.register_download_id( self.download_id, self)
    
    def thread_function( self):
        acquired = False

        gl = libgpodder.gPodderLib()
        util.delete_file( self.tempname)

        command = [ 'wget', '--timeout=120', '--continue', '--output-document="%s"' % self.tempname ]

        if self.channelitem and (self.channelitem.username or self.channelitem.password):
            command.append( '--user="%s"' % self.channelitem.username)
            command.append( '--password="%s"' % self.channelitem.password)

        if gl.limit_rate:
            command.append( '--limit-rate=%.1fk' % gl.limit_rate_value)

        command.append( '"%s"' % self.url)
        command = ' '.join( command)

        log( 'Command: %s', command)
        services.download_status_manager.update_status( self.download_id, episode = self.cutename, speed = _('Queued'), url = self.url)
        acquired = services.download_status_manager.s_acquire()

        # if after acquiring the lock, we are already cancelled,
        # the user has cancelled this download while it was queued
        if self.is_cancelled:
	    services.download_status_manager.remove_download_id( self.download_id)
            if self.ready_event != None:
                self.ready_event.set()
         
            if acquired:
                services.download_status_manager.s_release()
            return

        process = popen2.Popen3( command, True)
        
        self.pid = process.pid
        stderr = process.childerr
        
        while process.poll() == -1 and self.is_cancelled == False:
            msg = stderr.readline( 80)
            msg = msg.strip()
            #log( 'wget> %s', msg)

            if msg.find("%") != -1:
                try:
                    self.percentage = (int(msg[(msg.find("%") - 2)] + msg[(msg.find("%") - 1)])+0.001)/100.0
                except:
                    pass
               
                # Fedora/RedHat seem to have changed the output format of "wget", so we
                # first try to "detect" the speed in the Fedora/RedHat format and if we 
                # don't succeed, we'll use a regular expression to find the speed string.
                # Also see: doc/dev/redhat-wget-output.txt

                try:
                    speed_msg = msg.split()[7]
                except:
                    speed_msg = ''

                if re.search('[KB]', speed_msg):
                    self.speed = speed_msg
                else:
                    iter = re.compile('...\... .B\/s').finditer( msg)
                    for speed_string in iter:
                        self.speed = speed_string.group(0).strip()

	    services.download_status_manager.update_status( self.download_id, speed = self.speed, progress = int(self.percentage*100))
        
        if process.wait() == 0:
            try:
                move( self.tempname, self.filename)
            except:
                log( 'Error happened during moving tempfile :/')
                raise
        else:
            # Delete partially downloaded file
            util.delete_file( self.tempname)
        
        self.result = process.poll()
        self.pid = -1

	services.download_status_manager.remove_download_id( self.download_id)

        if self.result == 0 and self.channelitem and self.item:
            log( 'Download thread finished: Adding downloaded item to local database')
            self.channelitem.addDownloadedItem( self.item)
            
            # if we have received a localDB, clear its cache
            if self.localdb != None:
                self.localdb.clear_cache()
        
        if self.ready_event != None:
            self.ready_event.set()

        if acquired:
            services.download_status_manager.s_release()
    
    def cancel( self):
        self.is_cancelled = True
        if self.pid != -1:
            kill( self.pid, signal.SIGKILL)
    
    def download( self):
        self.thread = Thread( target=self.thread_function)
        self.thread.start()

