#
# Simple sed script to convert the output of "svn status" to a format
# suitable for appending to a ChangeLog file; used by the Makefile
#
# Copyright (c) 2007 Thomas Perl <thp@perli.net>
# Released under the terms of the GPL v2 or later
#
/^[^MAD].*$/d
s/^M *\(.*\)$/        * \1: /
s/^A *\(.*\)$/        + \1: /
s/^D *\(.*\)$/        - \1: /
