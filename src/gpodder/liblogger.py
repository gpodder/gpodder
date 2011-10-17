# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
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
#  liblogger.py -- gPodder logging facility
#  Thomas Perl <thp perli net>   20061117
#
#

import traceback
import logging
import sys

loggers = {'': logging.getLogger('gpodder')}

# XXX: This is deprecated for gPodder 3, and in 2.x, we only provide
# this for legacy support of the existing codebase. Please use the
# standard Python logging facility for your hook scripts. Thanks! :)
def log(message, *args, **kwargs):
    if 'sender' in kwargs:
        sender = kwargs['sender'].__class__.__name__
    else:
        sender = ''

    if sender not in loggers:
        loggers[sender] = logging.getLogger(sender)

    loggers[sender].info(message, *args)

    if kwargs.get('traceback', False):
        error = traceback.format_exc()
        if error.strip() != 'None':
            print >>sys.stderr, error

