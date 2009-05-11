#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
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

#
# Makefile for building the Win32 Launcher for gPodder
# Thomas Perl <thpinfo.com>; 2009-04-29
#

CC=gcc
LDFLAGS=-mwindows

all: gpodder

gpodder: gpodder-res.o gpodder.o

gpodder-res.o: gpodder.res
	windres gpodder.res gpodder-res.o

clean:
	rm -f *.o

.PHONY: clean all
.DEFAULT: all

