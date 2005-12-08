
#
# gPodder
# Copyright (c) 2005 Thomas Perl <thp@perli.net>
# Released under the GNU General Public License (GPL)
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
from shutil import move

import libgpodder
import signal

import popen2
import re

import gtk
import gobject

class downloadThread( object):
    url = ""
    filename = ""
    tempname = ""
    
    ready_event = None
    pid = -1
    percentage = "0"
    speed = "unknown"

    thread = None
    result = -1

    statusmgr = None
    statusmgr_id = None

    cutename = None
    
    def __init__( self, url, filename, ready_event = None, statusmgr = None, cutename = "unknown"):
        self.url = url.replace( "%20", " ")
        
        self.filename = filename
        self.tempname = dirname( self.filename) + "/.tmp-" + basename( self.filename)
        
        self.ready_event = ready_event
        self.pid= -1
        self.percentage = "0"
        self.speed = "unknown"
        
        self.thread = None
        self.result = -1

	self.cutename = cutename

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
        
        while process.poll() == -1:
            msg = stderr.readline( 80)
            if libgpodder.isDebugging():
	        print msg
            msg = msg.strip()
            
            if msg.find("%") != -1:
                self.percentage = (int(msg[(msg.find("%") - 2)] + msg[(msg.find("%") - 1)])+0.001)/100.0;
                
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
        
        if self.ready_event != None:
            self.ready_event.set()
    
    def cancel( self):
        if self.pid != -1:
            system( "kill -9 " + str( self.pid))
    
    def download( self):
        self.thread = Thread( target=self.thread_function)
        self.thread.start()


class downloadStatusManager( object):
    status_list = None
    next_status_id = 0
    tree_model = None
    
    def __init__( self):
        self.status_list = {}
	self.next_status_id = 0         #    Episode name         Speed             progress (100)     url of download
	self.tree_model = gtk.ListStore( gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_STRING)
    
    def getNextId( self):
        res = self.next_status_id
	self.next_status_id = res + 1
	return res

    def registerId( self, id, thread):
        self.status_list[id] = { 'iter':self.tree_model.append(), 'thread':thread }

    def unregisterId( self, id):
        iter = self.status_list[id]['iter']
	if iter != None:
            self.tree_model.remove( iter)
            self.status_list[id]['thread'].cancel()
            del self.status_list[id]

    def updateInfo( self, id, new_status = { 'episode':"unknown", 'speed':"0b/s", 'progress':0, 'url':"unknown" }):
        iter = self.status_list[id]['iter']
	if iter != None:
            self.tree_model.set( iter, 0, new_status['episode'])
            self.tree_model.set( iter, 1, new_status['speed'])
            self.tree_model.set( iter, 2, new_status['progress'])
	    self.tree_model.set( iter, 3, new_status['url'])

    def is_download_in_progress( self, url):
        for element in self.status_list:
	    thread = self.status_list[element]['thread']
	    if thread != None and thread.url == url:
	        return True
	
	return False

    def cancelAll( self):
        self.tree_model.clear()
        for element in self.status_list:
	    self.status_list[element]['iter'] = None
	    self.status_list[element]['thread'].cancel()

    def cancel_by_url( self, url):
        for element in self.status_list:
	    thread = self.status_list[element]['thread']
	    if thread != None and thread.url == url:
	        thread.cancel()
		return True
        
        return False

    def getModel( self):
        return self.tree_model
# end downloadStatusManager

def getDownloadFilename( url):
    global downloadpath
    filename = os.path.basename( url)
    
    # strip question mark (and everything behind it)
    indexOfQuestionMark = filename.rfind( "?")
    if( indexOfQuestionMark != -1):
        filename = filename[0:indexOfQuestionMark]
    # end if
    
    downloadfilename = downloadpath+filename
    
    return downloadfilename.replace( "%20", " ")
# end getDownloadFilename()

# downloadFile: simply download a file to current directory
def downloadFile( url):
    filename = getDownloadFilename( url)
    # download it, and never overwrite anything =)
    result = downloadProcedure( url, filename, False)
    
    return result
# end downloadFile()

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
    
    dlinfo_speed = "initializing download..."
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
            showMessage( "Download has been cancelled.")
        else:
            showMessage( "wget exited with status: " + str( dlinfo_result))
            print "*** THERE HAS BEEN AN ERROR WHILE DOWNLOADING **"
        # end if
    # end if
    
    # make the download result available to caller
    return dlinfo_result
# end downloadProcedure()

