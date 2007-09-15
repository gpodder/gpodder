# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (C) 2005-2007 Thomas Perl <thp at perli.net>
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

write_to_stdout = False


def enable_verbose():
    global write_to_stdout
    write_to_stdout = True


def log( message, *args, **kwargs):
    if 'sender' in kwargs:
        message = '(%s) %s' % ( kwargs['sender'].__class__.__name__, message )
    if write_to_stdout:
        print message % args
        if kwargs.get( 'traceback', False):
            error = traceback.format_exc()
            if error.strip() != 'None':
                print error


def msg( type, message, *args):
    s = message % args
    print '%c\t%s' % ( type[0].upper(), s )

