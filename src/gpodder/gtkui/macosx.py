# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2013 Thomas Perl and the gPodder Team
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

import struct
import sys

from gpodder import util

def aeKeyword(fourCharCode):
    """transform four character code into a long"""
    return struct.unpack('I', fourCharCode)[0]


# for the kCoreEventClass, kAEOpenDocuments, ... constants
# comes with macpython
from Carbon.AppleEvents import *

# all this depends on pyObjc (http://pyobjc.sourceforge.net/).
# There may be a way to achieve something equivalent with only
# what's in MacPython (see for instance http://mail.python.org/pipermail/pythonmac-sig/2006-May/017373.html)
# but I couldn't achieve this !

# Also note that it only works when gPodder is not running !
# For some reason I don't get the events afterwards...
try:
    from AppKit import NSObject
    from AppKit import NSAppleEventManager
    from AppKit import NSAppleEventDescriptor

    class gPodderEventHandler(NSObject):
        """ handles Apple Events for :
            - Open With... (and dropping a file on the icon)
            - "subscribe to podcast" from firefox
        The code was largely inspired by gedit-osx-delegate.m, from the
        gedit project
        (see http://git.gnome.org/browse/gedit/tree/gedit/osx/gedit-osx-delegate.m?id=GEDIT_2_28_3).
        """

        # keeps a reference to the gui.gPodder class
        gp = None

        def register(self, gp):
            """ register all handlers with NSAppleEventManager """
            self.gp = gp
            aem = NSAppleEventManager.sharedAppleEventManager()
            aem.setEventHandler_andSelector_forEventClass_andEventID_(
                self, 'openFileEvent:reply:', aeKeyword(kCoreEventClass), aeKeyword(kAEOpenDocuments))
            aem.setEventHandler_andSelector_forEventClass_andEventID_(
                self, 'subscribeEvent:reply:', aeKeyword('GURL'), aeKeyword('GURL'))

        def openFileEvent_reply_(self, event, reply):
            """ handles an 'Open With...' event"""
            urls = []
            filelist = event.paramDescriptorForKeyword_(aeKeyword(keyDirectObject))
            numberOfItems = filelist.numberOfItems()
            for i in range(1,numberOfItems+1):
                fileAliasDesc = filelist.descriptorAtIndex_(i)
                fileURLDesc = fileAliasDesc.coerceToDescriptorType_(aeKeyword(typeFileURL))
                fileURLData = fileURLDesc.data()
                url = buffer(fileURLData.bytes(),0,fileURLData.length())
                url = str(url)
                util.idle_add(self.gp.on_item_import_from_file_activate, None,url)
                urls.append(str(url))

            print >>sys.stderr,("open Files :",urls)
            result = NSAppleEventDescriptor.descriptorWithInt32_(42)
            reply.setParamDescriptor_forKeyword_(result, aeKeyword('----'))

        def subscribeEvent_reply_(self, event, reply):
            """ handles a 'Subscribe to...' event"""
            filelist = event.paramDescriptorForKeyword_(aeKeyword(keyDirectObject))
            fileURLData = filelist.data()
            url = buffer(fileURLData.bytes(),0,fileURLData.length())
            url = str(url)
            print >>sys.stderr,("Subscribe to :"+url)
            util.idle_add(self.gp.subscribe_to_url, url)

            result = NSAppleEventDescriptor.descriptorWithInt32_(42)
            reply.setParamDescriptor_forKeyword_(result, aeKeyword('----'))

    # global reference to the handler (mustn't be destroyed)
    handler = gPodderEventHandler.alloc().init()
except ImportError:
    print >> sys.stderr, """
    Warning: pyobjc not found. Disabling "Subscribe with" events handling
    """
    handler = None

def register_handlers(gp):
    """ register the events handlers (and keep a reference to gPodder's instance)"""
    if handler is not None:
        handler.register(gp)

