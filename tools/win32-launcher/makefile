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
#

#
# Makefile for building the Win32 Launcher for gPodder
# Thomas Perl <thp@gpodder.org>; 2009-04-29
#

CROSS ?= i686-w64-mingw32

CC := $(CROSS)-gcc
CXX := $(CROSS)-g++
CPP := $(CROSS)-cpp
RANLIB := $(CROSS)-ranlib
STRIP := $(CROSS)-strip
WINDRES := $(CROSS)-windres

LDFLAGS += -lkernel32 -lshell32 -lole32
MODULES := gpodder folderselector
TARGETS := gpodder.exe gpo.exe

all: $(TARGETS)

gpodder.exe: gpodder-res.o $(addsuffix _gui.o, $(MODULES))
	$(CC) -o $@ -mwindows $^ $(LDFLAGS)
	$(STRIP) -s $@

gpo.exe: gpo-res.o $(addsuffix _cli.o, $(MODULES))
	$(CC) -o $@ $^ $(LDFLAGS)
	$(STRIP) -s $@

%_gui.o: %.c
	$(CC) -c -o $@ $(CFLAGS) -DGPODDER_GUI $^

%_cli.o: %.c
	$(CC) -c -o $@ $(CFLAGS) -DGPODDER_CLI $^

%-res.o: %.res
	$(WINDRES) $^ $@

clean:
	$(RM) *.o

distclean: clean
	$(RM) $(TARGETS)

.PHONY: distclean clean all
.DEFAULT: all
