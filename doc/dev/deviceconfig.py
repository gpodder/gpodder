# New device configuration UI draft
# Thomas Perl <thp@gpodder.org>; 2010-03-23

import gtk
import os

w = gtk.Window()
w.set_default_size(400, 200)
v = gtk.HBox()
v.set_border_width(12)
v.set_spacing(6)
w.add(v)

sw = gtk.ScrolledWindow()
sw.set_shadow_type(gtk.SHADOW_IN)
sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

v.add(sw)

class Device(object):
    __slots__ = {
            'type': int,
            'name': str,
            'mountpoint': str,
            'on_sync_mark_played': bool,
            'on_sync_delete': bool,
            'disable_pre_sync_conversion': bool,
            # MP3-Player specific
            'delete_played': bool,
            'playlist_file': str,
            'playlist_absolute_path': bool,
            'playlist_win_path': bool,
            'use_scrobbler_log': bool,
            'max_filename_length': int,
            'custom_sync_name': str,
            'only_sync_not_played': bool,
            'channel_subfolders': bool,
            'rockbox_copy_coverart': bool,
            # iPod-specific
            'purge_old_episodes': bool,
            'delete_played_from_db': bool,
    }
    FOLDER, IPOD, MTP = range(3)

    def __init__(self, type_, name, mountpoint):
        self.type = type_
        self.name = name
        self.mountpoint = mountpoint

    def get_markup(self):
        return '%s\n<small>%s</small>' % (self.name, self.mountpoint)

    def get_icon(self, images_folder='data/images'):
        if self.type == self.FOLDER:
            return os.path.join(images_folder, 'folder.png')
        elif self.type == self.IPOD:
            return os.path.join(images_folder, 'ipod.png')
        elif self.type == self.MTP:
            return os.path.join(images_folder, 'mtp.png')

class DeviceList(gtk.ListStore):
    C_DEVICE, C_ICON, C_NAME = range(3)

    def __init__(self):
        gtk.ListStore.__init__(self, object, gtk.gdk.Pixbuf, str)

    def add_device(self, device):
        pixbuf = gtk.gdk.pixbuf_new_from_file(device.get_icon())
        self.append((device, pixbuf, device.get_markup()))

m = DeviceList()
m.add_device(Device(Device.IPOD, 'Apple iPod', '/media/ipod'))
m.add_device(Device(Device.FOLDER, 'MP3 Player', '/media/mp3/Podcasts'))
m.add_device(Device(Device.MTP, 'MTP Device', 'Using libmtp'))

tv = gtk.TreeView(m)
tv.set_headers_visible(False)

col = gtk.TreeViewColumn('')

cell = gtk.CellRendererPixbuf()
col.pack_start(cell, False)
col.add_attribute(cell, 'pixbuf', DeviceList.C_ICON)
cell = gtk.CellRendererText()
col.pack_start(cell, True)
col.add_attribute(cell, 'markup', DeviceList.C_NAME)

tv.append_column(col)

sw.add(tv)

h = gtk.VBox()
h.set_spacing(6)
v.pack_start(h, False, False)

for s in (gtk.STOCK_ADD, gtk.STOCK_EDIT, gtk.STOCK_REMOVE):
    i = gtk.image_new_from_stock(s, gtk.ICON_SIZE_BUTTON)
    b = gtk.Button()
    b.set_image(i)
    h.pack_start(b, False, False)

w.show_all()
w.connect('destroy', gtk.main_quit)
gtk.main()

