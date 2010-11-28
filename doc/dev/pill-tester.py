#!/usr/bin/python
# Simple script to test gPodder's "pill" pixbuf implementation
# Thomas Perl <thp.io/about>; 2009-09-13

import sys
sys.path.insert(0, 'src')

import gtk

from gpodder.gtkui.draw import draw_pill_pixbuf

def gen(x, y):
    if y >= x:
        pixbuf = draw_pill_pixbuf(str(x), str(y))
        return gtk.image_new_from_pixbuf(pixbuf)
    else:
        pixbuf = draw_pill_pixbuf('0', '0')
        return gtk.image_new_from_pixbuf(pixbuf)

w = gtk.Window()
w.connect('destroy', gtk.main_quit)
v = gtk.VBox()
w.add(v)
for y in xrange(15):
    h = gtk.HBox()
    h.set_homogeneous(True)
    v.add(h)
    for x in xrange(15):
        h.add(gen(x, y))
w.set_default_size(400, 400)
w.show_all()
gtk.main()

