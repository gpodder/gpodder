from os.path import exists
from os import makedirs
from os import unlink
from constants import isDebugging

def deleteFilename( filename):
    if isDebugging():
        print "deleteFilename: " + filename
    try:
        unlink( filename)
    except:
        # silently ignore 
        pass

def createIfNecessary( path):
    if not exists( path):
        try:
            makedirs( path)
            return True
        except:
            if isDebugging():
                print 'createIfNecessary: could not create: %s' % ( path )
            return False
    
    return True
