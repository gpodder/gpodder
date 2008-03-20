
# WIP. We might use this some time in the future.
#              -- Thomas Perl, 2008-03-19

# Released under the same license as gPodder.

import gtk
import gobject
import cairo

class gPodderSplashScreen(gtk.Window):
    (WIDTH, HEIGHT) = (250, 250)
    (WAIT, STEP) = (100, 20)

    def __init__(self, filename, caption):
        gtk.Window.__init__(self)
        self.caption = caption
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_keep_above(True)
        self.set_app_paintable(True)
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_opacity(1)
        self.connect('expose-event', self.expose_event)
        self.connect('screen-changed', self.screen_changed)
        self.resize(self.WIDTH, self.HEIGHT)

        self.fading_in = False

        self.svgsur = self.load_surface_from_file(filename)
        self.screen_changed(self)
        self.show_all()

    def fade_in(self):
        self.fading_in = True
        gobject.timeout_add(self.WAIT, self.update_opacity, True)

    def fade_out(self):
        if self.is_composited():
            self.fading_in = False
            gobject.timeout_add(self.WAIT, self.update_opacity, False, True)
        else:
            self.destroy()

    def expose_event(self, widget, event):
        cr = widget.window.cairo_create()
        if not self.is_composited():
            cr.set_source_rgb(0, 0, 0)
            cr.rectangle(0, 0, self.WIDTH, self.HEIGHT)
            cr.stroke()
            cr.set_source_rgb( 1, 1, 1)
            cr.rectangle(1, 1, self.WIDTH-2, self.HEIGHT-2)
            cr.fill()
        cr.set_source_rgba(0,0,0,0)
        if self.is_composited():
            cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        cr.set_source_surface(self.svgsur, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        texting = self.caption
        cr.set_font_size(30)
        cr.set_source_rgba(1, 1, 1, .5)
        (SHIFT_X, SHIFT_Y) = (20, -30)
        cr.move_to(SHIFT_X, self.HEIGHT+SHIFT_Y)
        cr.show_text(texting)
        cr.move_to(SHIFT_X+2, self.HEIGHT+SHIFT_Y+2)
        cr.show_text(texting)
        cr.move_to(SHIFT_X+2, self.HEIGHT+SHIFT_Y)
        cr.show_text(texting)
        cr.move_to(SHIFT_X, self.HEIGHT+SHIFT_Y+2)
        cr.show_text(texting)
        cr.fill()
        cr.set_source_rgba(0, 0, 0, 1)
        cr.move_to(SHIFT_X+1, self.HEIGHT+SHIFT_Y+1)
        cr.show_text(texting)
        cr.fill()
        return True

    def screen_changed(self, widget, old_screen=None):
        cm = widget.get_screen().get_rgba_colormap()
        if cm is not None:
            widget.set_colormap(cm)
    
    def load_surface_from_file(self, filename):
        pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(filename, self.WIDTH, self.HEIGHT)
    
        format = cairo.FORMAT_RGB24
        if pixbuf.get_has_alpha():
            format = cairo.FORMAT_ARGB32
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        image = cairo.ImageSurface(format, width, height)
    
        context = cairo.Context(image)
        gdkcontext = gtk.gdk.CairoContext(context)
        gdkcontext.set_source_pixbuf(pixbuf, 0, 0)
        gdkcontext.paint()
        return image
    
    def update_opacity(self, increase=True, close_after=False):
        if increase and self.fading_in:
            opacity = min(1.0, max(0.1, self.get_opacity()*1.1))
        else:
            opacity = self.get_opacity()-0.05
        self.set_opacity(max(0.0, min(1.0, opacity)))
        if opacity >= 0.0 and opacity <= 1.0:
            gobject.timeout_add(self.STEP, self.update_opacity, increase, close_after)
        elif close_after:
            self.destroy()

        return False


