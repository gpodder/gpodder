#!/usr/bin/python
# Progressbar icon tester
# Thomas Perl <thp.io/about>; 2012-02-05
#
# based on: Simple script to test gPodder's "pill" pixbuf implementation
#           Thomas Perl <thp.io/about>; 2009-09-13

import sys
sys.path.insert(0, 'src')

import gtk

from gpodder.gtkui.draw import draw_cake_pixbuf

def gen(percentage):
    pixbuf = draw_cake_pixbuf(percentage)
    return gtk.image_new_from_pixbuf(pixbuf)

w = gtk.Window()
w.connect('destroy', gtk.main_quit)
v = gtk.VBox()
w.add(v)
for y in xrange(1):
    h = gtk.HBox()
    h.set_homogeneous(True)
    v.add(h)
    PARTS = 20
    for x in xrange(PARTS + 1):
        h.add(gen(float(x)/float(PARTS)))
w.set_default_size(400, 100)
w.show_all()
gtk.main()

