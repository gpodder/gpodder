import dbus
import gobject
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib
    
import unittest
from test import test_support

import gettext
gettext.install('gpodder')
import libgpodder

class GPodderAppDBusTestCase(unittest.TestCase):

    # Only use setUp() and tearDown() if necessary

    def setUp(self):
        # Get a proxy object of a GPodderApp
        bus = dbus.SessionBus()
        self.gpodder_app_proxy = bus.get_object('net.perli.gpodder.GPodderApp',
                                                '/net/perli/gpodder/GPodderApp')
        self.gpodder_app_iface = dbus.Interface(self.gpodder_app_proxy,
                                                'net.perli.gpodder.GPodderAppIFace')
    def tearDown(self):
        # TODO:Stop the GPodderApp
        self.gpodder_app_iface.quit()
        self.failUnlessRaises(dbus.DBusException, self.gpodder_app_iface.is_running)
    
    def test_start(self):
        self.failUnlessRaises(dbus.DBusException, self.gpodder_app_iface.is_running)
        gpodderapp = libgpodder.gPodderLib()
        self.failUnlessEqual(True, gpodderapp.is_running())

def test_main():
    test_support.run_unittest(GPodderAppDBusTestCase)

if __name__ == '__main__':
    test_main()
