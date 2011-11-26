import dbus.exceptions

class SessionBus(object):
    def __init__(self, *args, **kwargs):
        pass

    def add_signal_receiver(self, *args, **kwargs):
        pass

    def name_has_owner(self, *args, **kwargs):
        return False

SystemBus = SessionBus
