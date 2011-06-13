# -*- coding: utf-8 -*-
# gpodder.net API Client
# Copyright (C) 2009-2010 Thomas Perl
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import mygpoclient

import datetime

def join(*args):
    """Join separate URL parts to a ful URL"""
    return '/'.join(args)

def iso8601_to_datetime(s):
    """Convert a ISO8601-formatted string to datetime

    >>> iso8601_to_datetime('2009-12-29T19:25:33')
    datetime.datetime(2009, 12, 29, 19, 25, 33)
    >>> iso8601_to_datetime('2009-12-29T19:25:33Z')
    datetime.datetime(2009, 12, 29, 19, 25, 33)
    >>> iso8601_to_datetime('xXxXxXxXxxxxXxxxXxx')
    >>>
    """
    for format in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ'):
        try:
            return datetime.datetime.strptime(s, format)
        except ValueError:
            continue

    return None

def datetime_to_iso8601(dt):
    """Convert a datetime to a ISO8601-formatted string

    >>> datetime_to_iso8601(datetime.datetime(2009, 12, 29, 19, 25, 33))
    '2009-12-29T19:25:33'
    """
    return dt.strftime('%Y-%m-%dT%H:%M:%S')

def position_to_seconds(s):
    """Convert a position string to its amount of seconds

    >>> position_to_seconds('00:00:01')
    1
    >>> position_to_seconds('00:01:00')
    60
    >>> position_to_seconds('01:00:00')
    3600
    >>> position_to_seconds('02:59:59')
    10799
    >>> position_to_seconds('100:00:00')
    360000
    """
    hours, minutes, seconds = (int(x) for x in s.split(':', 2))
    return (((hours*60)+minutes)*60)+seconds

def seconds_to_position(seconds):
    """Convert the amount of seconds to a position string

    >>> seconds_to_position(1)
    '00:00:01'
    >>> seconds_to_position(60)
    '00:01:00'
    >>> seconds_to_position(60*60)
    '01:00:00'
    >>> seconds_to_position(59 + 60*59 + 60*60*2)
    '02:59:59'
    >>> seconds_to_position(60*60*100)
    '100:00:00'
    """
    minutes = int(seconds/60)
    seconds = seconds % 60
    hours = int(minutes/60)
    minutes = minutes % 60
    return '%02d:%02d:%02d' % (hours, minutes, seconds)


