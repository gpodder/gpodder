#
# Simple sed script to convert the output of "svn status" to a format
# suitable for appending to a ChangeLog file; used by the Makefile
#
# Copyright (c) 2007 Thomas Perl <thp@perli.net>
# Released under the terms of the GNU GPL v3 or later
#
/^[^MAD].*$/d
s/^M *\(.*\)$/\t* \1: /
s/^A *\(.*\)$/\t* \1: Added/
s/^D *\(.*\)$/\t* \1: Removed/
