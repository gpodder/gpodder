# Copyright (c) 2011 Neal H. Walfield
#
# This software is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import with_statement
import os
import logging
import itertools
import sys
import string
import traceback
import time
import errno
import glob

logger = None
original_excepthook = None

def my_excepthook(exctype, value, tb):
    """Log uncaught exceptions."""
    logger.error(
        "Uncaught exception: %s"
        % (''.join(traceback.format_exception(exctype, value, tb)),))
    original_excepthook(exctype, value, tb)

def init(dot_directory, debug=True, max_logfiles=1, program_name=None):
    if not os.path.isabs(dot_directory):
        dot_directory = os.path.join(os.path.expanduser("~"), dot_directory)

    logging_directory = os.path.join(dot_directory, "logs")
    try:
        os.makedirs(logging_directory)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise

    if program_name is None:
        program_name = os.path.basename(sys.argv[0])
    string.translate(program_name, string.maketrans(' .', '__'))

    timestamp = time.strftime("%Y%m%d")

    logfiles = glob.glob(os.path.join(logging_directory,
                                      program_name + '-*.log'))
    if len(logfiles) >= max_logfiles:
        logfiles.sort()
        for f in logfiles[:-(max_logfiles+1)]:
            print "Purging old log file %s" % (f,)
            try:
                os.remove(f)
            except OSError, e:
                print "Removing %s: %s" % (f, str(e))

    logfile = os.path.join(logging_directory,
                           program_name + '-' + timestamp + '.log')

    print "Sending output to %s" % logfile

    global logger
    logger = logging.getLogger(__name__) 

    if debug:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format=('%(asctime)s (pid: ' + str(os.getpid()) + ') '
                + '%(levelname)-8s %(message)s'),
        filename=logfile,
        filemode='a')

    # Log uncaught exceptions.
    global original_excepthook
    original_excepthook = sys.excepthook
    sys.excepthook = my_excepthook

    def redirect(thing):
        filename = os.path.join(logging_directory, program_name + '.' + thing)
        try:
            with open(filename, "r") as fhandle:
                contents = fhandle.read()
        except IOError, e:
            if e.errno in (errno.ENOENT,):
                fhandle = None
                contents = ""
            else:
                logging.error("Reading %s: %s" % (filename, str(e)))
                raise

        logging.error("std%s of last run: %s" % (thing, contents))

        if fhandle is not None:
            os.remove(filename)

        print "Redirecting std%s to %s" % (thing, filename)
        return open(filename, "w", 0)
            
    sys.stderr = redirect('err')
    sys.stdout = redirect('out')

