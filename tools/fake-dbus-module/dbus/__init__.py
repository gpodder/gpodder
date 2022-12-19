import dbus.exceptions  # noqa: F401


class SessionBus(object):
    def __init__(self, *args, **kwargs):
        self.fake = True

    def add_signal_receiver(self, *args, **kwargs):
        pass

    def name_has_owner(self, *args, **kwargs):
        return False


SystemBus = SessionBus
