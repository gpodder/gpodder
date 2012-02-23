#!/usr/bin/python
# Example script that can be used as post-play extension in media players
#
# Set the configuration options "audio_played_dbus" and "video_played_dbus"
# to True to let gPodder leave the played status untouched when playing
# files in the media player. After playback has finished, call this script
# with the filename of the played episodes as single argument. The episode
# will be marked as played inside gPodder.
#
# Usage: gpodder_mark_played.py /path/to/episode.mp3
#        (the gPodder GUI has to be running)
#
# Thomas Perl <thp@gpodder.org>; 2009-09-09

import sys
import os

if len(sys.argv) != 2:
    print >>sys.stderr, """
    Usage: %s /path/to/episode.mp3
    """ % (sys.argv[0],)
    sys.exit(1)

filename = os.path.abspath(sys.argv[1])

import dbus
import gpodder

session_bus = dbus.SessionBus()
proxy = session_bus.get_object(gpodder.dbus_bus_name, \
                               gpodder.dbus_gui_object_path)
interface = dbus.Interface(proxy, gpodder.dbus_interface)

if not interface.mark_episode_played(filename):
    print >>sys.stderr, 'Warning: Could not mark episode as played.'
    sys.exit(2)

