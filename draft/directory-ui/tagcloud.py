
from gi.repository import Gtk
from gi.repository import GObject
import cgi

tags = (
        ('Electronica', 5),
        ('Reggae', 5),
        ('Electro', 20),
        ('Detroit Techno', 4),
        ('Funk', 14),
        ('Jazz', 4),
        ('Minimal', 20),
        ('Soulful Drum and Bass', 6),
        ('Dub', 7),
        ('Drum and Bass', 23),
        ('Deep Techno', 7),
        ('Deephouse', 27),
        ('Soulful', 9),
        ('Minimal Techno', 30),
        ('Downtempo', 17),
        ('House', 29),
        ('Dubstep', 14),
        ('Techno', 32),
        ('Electrotech', 8),
        ('Techhouse', 28),
        ('Disco', 15),
        ('Downbeat', 28),
        ('Electrohouse', 14),
        ('Hiphop', 25),
        ('Trance', 6),
        ('Freestyle', 14),
        ('Funky House', 3),
        ('Minimal House', 4),
        ('Nu Jazz', 11),
        ('Chill-Out', 6),
        ('Breaks', 10),
        ('UK Garage', 4),
        ('Soul', 10),
        ('Progressive House', 3),
        ('Lounge', 6),
)


class TagCloud(Gtk.Layout):
    __gsignals__ = {
            'selected': (GObject.SignalFlags.RUN_LAST, None,
                           (GObject.TYPE_STRING,))
    }

    def __init__(self, tags, min_size=20, max_size=36):
        self.__gobject_init__()
        Gtk.Layout.__init__(self)
        self._tags = tags
        self._min_size = min_size
        self._max_size = max_size
        self._min_weight = min(weight for tag, weight in self._tags)
        self._max_weight = max(weight for tag, weight in self._tags)
        self._size = 0, 0
        self._alloc_id = self.connect('size-allocate', self._on_size_allocate)
        self._init_tags()
        self._in_relayout = False

    def _on_size_allocate(self, widget, allocation):
        self._size = (allocation.width, allocation.height)
        if not self._in_relayout:
            self.relayout()

    def _init_tags(self):
        for tag, weight in self._tags:
            label = Gtk.Label()
            markup = '<span size="%d">%s</span>' % (1000*self._scale(weight), cgi.escape(tag))
            label.set_markup(markup)
            button = Gtk.ToolButton(**{'icon-widget': label})
            button.connect('clicked', lambda b: self.emit('selected', tag))
            self.put(button, 1, 1)

    def _scale(self, weight):
        weight_range = float(self._max_weight-self._min_weight)
        ratio = float(weight-self._min_weight)/weight_range
        return int(self._min_size + (self._max_size-self._min_size)*ratio)

    def relayout(self):
        self._in_relayout = True
        x, y, max_h = 0, 0, 0
        current_row = []
        pw, ph = self._size
        def fixup_row(widgets, x, y, max_h):
            residue = (pw - x)
            x = int(residue/2)
            for widget in widgets:
                r = widget.size_request()
                cw, ch = r.width, r.height
                self.move(widget, x, y+max(0, int((max_h-ch)/2)))
                x += cw + 10
        for child in self.get_children():
            r = child.size_request()
            w, h = r.width, r.height
            if x + w > pw:
                fixup_row(current_row, x, y, max_h)
                y += max_h + 10
                max_h, x = 0, 0
                current_row = []

            self.move(child, x, y)
            x += w + 10
            max_h = max(max_h, h)
            current_row.append(child)
        fixup_row(current_row, x, y, max_h)
        self.set_size(pw, y+max_h)
        def unrelayout():
            self._in_relayout = False
            return False
        GObject.idle_add(unrelayout)
GObject.type_register(TagCloud)

if __name__ == '__main__':
    l = TagCloud(tags)

    try:
        import hildon
        w = hildon.StackableWindow()
        sw = hildon.PannableArea()
    except:
        w = Gtk.Window()
        w.set_default_size(600, 300)
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    w.set_title('Tag cloud Demo')
    w.add(sw)
    sw.add(l)

    def on_tag_selected(cloud, tag):
        print 'tag selected:', tag

    l.connect('selected', on_tag_selected)

    w.show_all()
    w.connect('destroy', Gtk.main_quit)

    Gtk.main()

