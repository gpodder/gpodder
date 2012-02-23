
import gtk
import gobject
import pango
import tagcloud
import json

w = gtk.Dialog()
w.set_title('Discover new podcasts')
w.set_default_size(650, 450)

tv = gtk.TreeView()
tv.set_headers_visible(False)
tv.set_size_request(160, -1)

class OpmlEdit(object): pass
class Search(object): pass
class OpmlFixed(object): pass
class TagCloud(object): pass

search_providers = (
        ('gpodder.net', 'search_gpodder.png', Search),
        ('YouTube', 'search_youtube.png', Search),
        ('SoundCloud', 'search_soundcloud.png', Search),
        ('Miro Guide', 'search_miro.png', Search),
)

directory_providers = (
        ('Toplist', 'directory_toplist.png', OpmlFixed),
        ('Examples', 'directory_example.png', OpmlFixed),
        ('Tag cloud', 'directory_tags.png', TagCloud),
)

SEPARATOR = (True, pango.WEIGHT_NORMAL, '', None, None)
C_SEPARATOR, C_WEIGHT, C_TEXT, C_ICON, C_PROVIDER = range(5)
store = gtk.ListStore(bool, int, str, gtk.gdk.Pixbuf, object)

opml_pixbuf = gtk.gdk.pixbuf_new_from_file('directory_opml.png')
store.append((False, pango.WEIGHT_NORMAL, 'OPML', opml_pixbuf, OpmlEdit))

store.append(SEPARATOR)

for name, icon, provider in search_providers:
    pixbuf = gtk.gdk.pixbuf_new_from_file(icon)
    store.append((False, pango.WEIGHT_NORMAL, name, pixbuf, provider))

store.append(SEPARATOR)

for name, icon, provider in directory_providers:
    pixbuf = gtk.gdk.pixbuf_new_from_file(icon)
    store.append((False, pango.WEIGHT_NORMAL, name, pixbuf, provider))

store.append(SEPARATOR)

for i in range(1, 5):
    store.append((False, pango.WEIGHT_NORMAL, 'Bookmark %d' % i, None, None))

tv.set_model(store)

def is_row_separator(model, iter):
    return model.get_value(iter, C_SEPARATOR)

tv.set_row_separator_func(is_row_separator)

column = gtk.TreeViewColumn('')
cell = gtk.CellRendererPixbuf()
column.pack_start(cell, False)
column.add_attribute(cell, 'pixbuf', C_ICON)
cell = gtk.CellRendererText()
column.pack_start(cell)
column.add_attribute(cell, 'text', C_TEXT)
column.add_attribute(cell, 'weight', C_WEIGHT)
tv.append_column(column)

def on_row_activated(treeview, path, column):
    model = treeview.get_model()
    iter = model.get_iter(path)

    for row in model:
        row[C_WEIGHT] = pango.WEIGHT_NORMAL

    if iter:
        model.set_value(iter, C_WEIGHT, pango.WEIGHT_BOLD)
        provider = model.get_value(iter, C_PROVIDER)
        use_provider(provider)

tv.connect('row-activated', on_row_activated)

sw = gtk.ScrolledWindow()
sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
sw.set_shadow_type(gtk.SHADOW_IN)
sw.add(tv)

sidebar = gtk.VBox()
sidebar.set_spacing(6)

sidebar.pack_start(sw, True, True)
sidebar.pack_start(gtk.Button('Add bookmark'), False, False)

vb = gtk.VBox()
vb.set_spacing(6)

title_label = gtk.Label('Title')
title_label.set_alignment(0, 0)
vb.pack_start(title_label, False, False)

search_hbox = gtk.HBox()
search_hbox.set_spacing(6)
search_label = gtk.Label('')
search_hbox.pack_start(search_label, False, False)
search_entry = gtk.Entry()
search_hbox.pack_start(search_entry, True, True)
search_button = gtk.Button('')
search_hbox.pack_start(search_button, False, False)

vb.pack_start(search_hbox, False, False)

tagcloud_sw = gtk.ScrolledWindow()
tagcloud_sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
tagcloud_sw.set_shadow_type(gtk.SHADOW_IN)
podcast_tags = json.loads("""
[
{"tag": "Technology",
"usage": 530 },
{"tag": "Society & Culture",
"usage": 420 },
{"tag": "Arts",
"usage": 400},
{"tag": "News & Politics",
"usage": 320}
]
""")
tagcloudw = tagcloud.TagCloud(list((x['tag'], x['usage']) for x in podcast_tags), 10, 14)
tagcloud_sw.set_size_request(-1, 130)
tagcloud_sw.add(tagcloudw)
vb.pack_start(tagcloud_sw, False, False)

podcasts_sw = gtk.ScrolledWindow()
podcasts_sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
podcasts_sw.set_shadow_type(gtk.SHADOW_IN)
podcasts_tv = gtk.TreeView()
podcasts_sw.add(podcasts_tv)
vb.pack_start(podcasts_sw, True, True)


hb = gtk.HBox()
hb.set_spacing(12)
hb.set_border_width(12)
hb.pack_start(sidebar, False, True)
hb.pack_start(vb, True, True)

w.vbox.add(hb)
w.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
w.add_button('Subscribe', gtk.RESPONSE_OK)
w.set_response_sensitive(gtk.RESPONSE_OK, False)

def use_provider(provider):
    if provider == OpmlEdit:
        search_label.set_text('URL:')
        search_button.set_label('Download')
    else:
        search_label.set_text('Search:')
        search_button.set_label('Search')

    if provider in (OpmlEdit, Search):
        title_label.hide()
        search_hbox.show()
        search_entry.set_text('')
        def later():
            search_entry.grab_focus()
            return False
        gobject.idle_add(later)
    elif provider == TagCloud:
        title_label.hide()
        search_hbox.hide()
    else:
        if provider == OpmlFixed:
            title_label.set_text('Example stuff')
        elif provider == TagCloud:
            title_label.set_text('Tag cloud')
        title_label.show()
        search_hbox.hide()

    tagcloud_sw.set_visible(provider == TagCloud)

    print 'using provider:', provider

#w.connect('destroy', gtk.main_quit)
w.show_all()

on_row_activated(tv, (0,), None)

w.run()

#gtk.main()

