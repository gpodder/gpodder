import dbus
import gobject
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib
    
import unittest
from test import test_support
from os import chdir
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
        try:
            self.gpodder_app_iface.unregister()
        except dbus.DBusException:
            pass
        self.failUnlessRaises(dbus.DBusException, self.gpodder_app_iface.is_running)
    
    def test_start(self):
        """The backend is started if not running"""
        self.failUnlessRaises(dbus.DBusException, self.gpodder_app_iface.is_running)
        gpodderapp = libgpodder.gPodderLib()
        self.failUnlessEqual(True, gpodderapp.is_running())

    def test_different_wd(self):
        """The backend is started if backend is in path"""
        chdir('../..')
        gpodderapp = libgpodder.gPodderLib()
        self.failUnlessEqual(True, gpodderapp.is_running())

    def test_one_unregister(self):
        """The backend stops when last client unregisters (one client)"""
        # Check with one client
        gpodderapp = libgpodder.gPodderLib()
        a = gpodderapp.unregister()
        self.failUnlessRaises(dbus.DBusException, self.gpodder_app_iface.is_running)
        
    def test_multiple_unregister(self):
        """The backend stops when last client unregisters (multiple clients)"""
        gpodderapp = libgpodder.gPodderLib()

        # add a second client
        gpodderapp.register()

        # kill one client, the backend should still be running
        gpodderapp.unregister()
        self.failUnlessEqual(True, gpodderapp.is_running())

        # kill the other client, the backend stops
        gpodderapp.unregister()
        self.failUnlessRaises(dbus.DBusException, self.gpodder_app_iface.is_running)

def test_main():
    test_support.run_unittest(GPodderAppDBusTestCase)

if __name__ == '__main__':
    test_main()
