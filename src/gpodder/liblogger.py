

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
#  liblogger.py -- gPodder logging facility
#  Thomas Perl <thp perli net>   20061117
#
#



write_to_stdout = False


def enable_verbose():
    global write_to_stdout
    write_to_stdout = True


def log( message, *args, **kwargs):
    if 'sender' in kwargs:
        message = '(%s) %s' % ( kwargs['sender'].__class__.__name__, message )
    if write_to_stdout:
        print message % args


def msg( type, message, *args):
    s = message % args
    print '%c\t%s' % ( type[0].upper(), s )

