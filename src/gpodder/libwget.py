
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

import popen2
import re

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
    
    def __init__( self, url, filename, ready_event = None):
        self.url = url.replace( "%20", " ")
        
        self.filename = filename
        self.tempname = dirname( self.filename) + "/.tmp-" + basename( self.filename)
        
        self.ready_event = ready_event
        self.pid= -1
        self.percentage = "0"
        self.speed = "unknown"
        
        self.thread = None
        self.result = -1
    
    def thread_function( self):
        command = "/usr/bin/wget \"" + self.url + "\" -O \"" + self.tempname + "\""
        print command
        process = popen2.Popen3( command, True)
        
        self.pid = process.pid
        stderr = process.childerr
        
        while process.poll() == -1:
            msg = stderr.readline( 80)
            print msg
            msg = msg.strip()
            
            if msg.find("%") != -1:
                self.percentage = (int(msg[(msg.find("%") - 2)] + msg[(msg.find("%") - 1)])+0.001)/100.0;
                
                iter = re.compile('...\... .B\/s').finditer( msg)
                for speed_string in iter:
                    self.speed = speed_string.group(0).strip()
        
        if process.wait() == 0:
            move( self.tempname, self.filename)
        
        self.result = process.poll()
        self.pid = -1
        
        if self.ready_event != None:
            self.ready_event.set()
    
    def cancel( self):
        if self.pid != -1:
            system( "kill -9 " + str( self.pid))
    
    def download( self):
        self.thread = Thread( target=self.thread_function)
        self.thread.start()



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
