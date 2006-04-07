
#
# gPodder (a media aggregator / podcast client)
# Copyright (C) 2005-2006 Thomas Perl <thp at perli.net>
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
from threading import Thread
from threading import Lock
from shutil import move

import libgpodder
import signal

import popen2
import re
import md5

import gtk
import gobject

class downloadThread( object):
    url = ""
    filename = ""
    tempname = ""
    
    ready_event = None
    pid = -1
    percentage = "0"
    speed = _("unknown")

    thread = None
    result = -1

    statusmgr = None
    statusmgr_id = None

    cutename = None

    # for downloaded items
    channelitem = None
    item = None
    localdb = None

    # well..
    is_cancelled = False
    
    def __init__( self, url, filename, ready_event = None, statusmgr = None, cutename = _("unknown"), channelitem = None, item = None, localdb = None):
        self.url = url.replace( "%20", " ")
        
        self.filename = filename
        self.tempname = dirname( self.filename) + "/.tmp-" + basename( self.filename)
        
        self.ready_event = ready_event
        self.pid= -1
        self.percentage = "0"
        self.speed = _("unknown")
        
        self.thread = None
        self.result = -1

	self.cutename = cutename

        self.channelitem = channelitem
        self.item = item
        self.localdb = localdb

	self.statusmgr = statusmgr
	if self.statusmgr != None:
	    # request new id from status manager
	    self.statusmgr_id = self.statusmgr.getNextId()
	    self.statusmgr.registerId( self.statusmgr_id, self)
    
    def thread_function( self):
        command = "wget \"" + self.url + "\" -O \"" + self.tempname + "\""
        print command
        process = popen2.Popen3( command, True)
        
        self.pid = process.pid
        stderr = process.childerr
        
        while process.poll() == -1 and self.is_cancelled == False:
            msg = stderr.readline( 80)
            if libgpodder.isDebugging():
	        print msg
            msg = msg.strip()
            
            if msg.find("%") != -1:
                try:
                    self.percentage = (int(msg[(msg.find("%") - 2)] + msg[(msg.find("%") - 1)])+0.001)/100.0
                except:
                    self.percentage = '0'
                
                iter = re.compile('...\... .B\/s').finditer( msg)
                for speed_string in iter:
                    self.speed = speed_string.group(0).strip()

            if self.statusmgr != None:
	        self.statusmgr.updateInfo( self.statusmgr_id, { 'episode':self.cutename, 'speed':self.speed, 'progress':int(self.percentage*100), 'url':self.url})
	    # self.statusmgr
        
        if process.wait() == 0:
            move( self.tempname, self.filename)
        
        self.result = process.poll()
        self.pid = -1

	if self.statusmgr != None:
	    self.statusmgr.unregisterId( self.statusmgr_id)
	# self.statusmgr

        if self.result == 0 and self.channelitem != None and self.item != None:
            if libgpodder.isDebugging():
                print "downloadThread finished: adding downloaded item to downloaded list"
            self.channelitem.addDownloadedItem( self.item)
            
            # if we have received a localDB, clear its cache
            if self.localdb != None:
                self.localdb.clear_cache()
        
        if self.ready_event != None:
            self.ready_event.set()
    
    def cancel( self):
        self.is_cancelled = True
        if self.pid != -1:
            system( "kill -9 " + str( self.pid))
    
    def download( self):
        self.thread = Thread( target=self.thread_function)
        self.thread.start()


class downloadStatusManager( object):
    status_list = None
    next_status_id = 0
    tree_model = None
    smlock = None # this lock should be used around any treemodel calls
    
    def __init__( self):
        self.status_list = {}
	self.next_status_id = 0         #    Episode name         Speed             progress (100)     url of download
        self.smlock = Lock()

        # use smlock around every tree_model usage, as seen here:
        self.smlock.acquire()
	self.tree_model = gtk.ListStore( gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_STRING)
        self.smlock.release()
    
    def getNextId( self):
        res = self.next_status_id
	self.next_status_id = res + 1
	return res

    def registerId( self, id, thread):
        self.smlock.acquire()
        self.status_list[id] = { 'iter':self.tree_model.append(), 'thread':thread }
        self.smlock.release()

    def remove_iter( self, iter):
        self.tree_model.remove( iter)
        return False

    def unregisterId( self, id):
        if not id in self.status_list:
            return
        iter = self.status_list[id]['iter']
	if iter != None:
            self.smlock.acquire()
            gobject.idle_add( self.remove_iter, iter)
            self.smlock.release()
            self.status_list[id]['iter'] = None
            self.status_list[id]['thread'].cancel()
            del self.status_list[id]

    def updateInfo( self, id, new_status = { 'episode':"unknown", 'speed':"0b/s", 'progress':0, 'url':"unknown" }):
        if not id in self.status_list:
            return
        iter = self.status_list[id]['iter']
	if iter != None:
            self.smlock.acquire()
            gobject.idle_add( self.tree_model.set, iter, 0, new_status['episode'])
            gobject.idle_add( self.tree_model.set, iter, 1, new_status['speed'])
            gobject.idle_add( self.tree_model.set, iter, 2, new_status['progress'])
            gobject.idle_add( self.tree_model.set, iter, 3, new_status['url'])
            self.smlock.release()

    def is_download_in_progress( self, url):
        for element in self.status_list:
	    thread = self.status_list[element]['thread']
	    if thread != None and thread.url == url:
	        return True
	
	return False

    def cancelAll( self):
        for element in self.status_list:
	    self.status_list[element]['iter'] = None
	    self.status_list[element]['thread'].cancel()
        # clear the tree model after cancelling
        gobject.idle_add( self.tree_model.clear)

    def get_url_by_iter( self, iter):
        result = self.tree_model.get_value( iter, 3)
        return result

    def get_title_by_iter( self, iter):
        result = self.tree_model.get_value( iter, 0)
        return result

    def cancel_by_url( self, url):
        for element in self.status_list:
	    thread = self.status_list[element]['thread']
	    if thread != None and thread.url == url:
                self.unregisterId( element)
		return True
        
        return False

    def getModel( self):
        return self.tree_model
# end downloadStatusManager

# getWebData: get an rss feed and save it locally, return content
def getWebData( url, force_update):
    filename = configpath + md5.new( url).hexdigest() + ".feed"
    downloadProcedure( url, filename, force_update)

    return filename
# end getWebData()

# downloadProcedure: gerneric implementation of downloading with gui
def downloadProcedure( url, filename, force_update):
    global dlinfo_speed
    global dlinfo_percentage
    global dlinfo_result
    
    url = url.replace( "%20", " ")
    
    dlinfo_speed = '...'
    dlinfo_percentage = "0"
    dlinfo_result = -1
    
    # check if file does not exist and download if necessary
    if( os.path.exists( filename) == False or force_update == True):
        wait_dialog_display( url, filename, dlinfo_speed)
        
        # set up the thread and start it in the background
        finished = threading.Event()
        argumente = ( url, filename, finished)
        mythread = threading.Thread( target=downloadThread, args=argumente )
        mythread.start()

        # wait for thread to be finished
        while finished.isSet() == False:
            finished.wait( 0.1)
            wait_dialog_update( url, filename, dlinfo_speed, dlinfo_percentage)
            updui()
        # end while
        wait_dialog_destroy()
    # end if
    
    # the error handling comes here..
    if dlinfo_result > 0:
        if dlinfo_result == 9:
            showMessage( _("Download has been cancelled."))
        else:
            showMessage( _("Download error. Wget exit code was: %d") % dlinfo_result)
        # end if
    # end if
    
    # make the download result available to caller
    return dlinfo_result
# end downloadProcedure()

