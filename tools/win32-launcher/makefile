#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2012 Thomas Perl and the gPodder Team
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
# Thomas Perl <thp@gpodder.org>; 2009-04-29
#

CC=gcc
LDFLAGS=-lkernel32 -lshell32 -lwininet

all: gpodder gpo

gpodder: gpodder-res.o gpodder_gui.o downloader_gui.o
	$(CC) -o $@ -mwindows $^ $(LDFLAGS)

gpo: gpo-res.o gpodder_cli.o downloader_cli.o
	$(CC) -o $@ $^ $(LDFLAGS)

gpodder_gui.o: gpodder.c
	$(CC) -c -o $@ $(CFLAGS) -DGPODDER_GUI $^

gpodder_cli.o: gpodder.c
	$(CC) -c -o $@ $(CFLAGS) -DGPODDER_CLI $^

downloader_gui.o: downloader.c
	$(CC) -c -o $@ $(CFLAGS) -DGPODDER_GUI $^

downloader_cli.o: downloader.c
	$(CC) -c -o $@ $(CFLAGS) -DGPODDER_CLI $^

gpodder-res.o: gpodder.res
	windres $^ $@

gpo-res.o: gpo.res
	windres $^ $@

clean:
	-rm -f *.o
	-del *.o

.PHONY: clean all
.DEFAULT: all

