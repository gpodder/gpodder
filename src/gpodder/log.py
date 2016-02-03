# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2016 Thomas Perl and the gPodder Team
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

# gpodder.log - Logging setup
# Thomas Perl <thp@gpodder.org>; 2012-03-02
# Based on an initial draft by Neal Walfield


import gpodder

import glob
import logging
import os
import sys
import time
import traceback

logger = logging.getLogger(__name__)

def setup(verbose=True):
    # Configure basic stdout logging
    STDOUT_FMT = '%(created)f [%(name)s] %(levelname)s: %(message)s'
    logging.basicConfig(format=STDOUT_FMT,
            level=logging.DEBUG if verbose else logging.WARNING)

    # Replace except hook with a custom one that logs it as an error
    original_excepthook = sys.excepthook
    def on_uncaught_exception(exctype, value, tb):
        message = ''.join(traceback.format_exception(exctype, value, tb))
        logger.error('Uncaught exception: %s', message)
        original_excepthook(exctype, value, tb)
    sys.excepthook = on_uncaught_exception

    if os.environ.get('GPODDER_WRITE_LOGS', 'yes') != 'no':
        # Configure file based logging
        logging_basename = time.strftime('%Y-%m-%d.log')
        logging_directory = os.path.join(gpodder.home, 'Logs')
        if not os.path.isdir(logging_directory):
            try:
                os.makedirs(logging_directory)
            except:
                logger.warn('Cannot create output directory: %s',
                        logging_directory)
                return False

        # Keep logs around for 5 days
        LOG_KEEP_DAYS = 5

        # Purge old logfiles if they are older than LOG_KEEP_DAYS days
        old_logfiles = glob.glob(os.path.join(logging_directory, '*-*-*.log'))
        for old_logfile in old_logfiles:
            st = os.stat(old_logfile)
            if time.time() - st.st_mtime > 60*60*24*LOG_KEEP_DAYS:
                logger.info('Purging old logfile: %s', old_logfile)
                try:
                    os.remove(old_logfile)
                except:
                    logger.warn('Cannot purge logfile: %s', exc_info=True)

        root = logging.getLogger()
        logfile = os.path.join(logging_directory, logging_basename)
        file_handler = logging.FileHandler(logfile, 'a', 'utf-8')
        FILE_FMT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
        file_handler.setFormatter(logging.Formatter(FILE_FMT))
        root.addHandler(file_handler)

    logger.debug('==== gPodder starts up (ui=%s) ===', ', '.join(name
        for name in ('cli', 'gtk') if getattr(gpodder.ui, name, False)))

    return True

