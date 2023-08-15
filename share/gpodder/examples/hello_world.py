
# Use a logger for debug output - this will be managed by gPodder.
import logging

logger = logging.getLogger(__name__)

# Provide some metadata that will be displayed in the gPodder GUI.
__title__ = 'Hello World Extension'
__description__ = 'Explain in one sentence what this extension does.'
__only_for__ = 'gtk, cli'
__authors__ = 'Thomas Perl <m@thp.io>'


class gPodderExtension:
    # The extension will be instantiated the first time it's used.
    # You can do some sanity checks here and raise an Exception if
    # you want to prevent the extension from being loaded.
    def __init__(self, container):
        self.container = container

    # This function will be called when the extension is enabled or
    # loaded. This is when you want to create helper objects or hook
    # into various parts of gPodder.
    def on_load(self):
        logger.info('Extension is being loaded.')
        print('=' * 40)
        print('container:', self.container)
        print('container.manager:', self.container.manager)
        print('container.config:', self.container.config)
        print('container.manager.core:', self.container.manager.core)
        print('container.manager.core.db:', self.container.manager.core.db)
        print('container.manager.core.config:', self.container.manager.core.config)
        print('container.manager.core.model:', self.container.manager.core.model)
        print('=' * 40)

    # This function will be called when the extension is disabled or
    # when gPodder shuts down. You can use this to destroy/delete any
    # objects that you created in on_load().
    def on_unload(self):
        logger.info('Extension is being unloaded.')

    def on_ui_object_available(self, name, ui_object):
        """
        Called by gPodder when ui is ready.
        """
        if name == 'gpodder-gtk':
            self.gpodder = ui_object

    def on_create_menu(self):
        return [("Say Hello", self.say_hello_cb)]

    def say_hello_cb(self):
        self.gpodder.notification("Hello Extension", "Message", widget=self.gpodder.main_window)


# Concurrency Warning: use gpodder.util.Popen() instead of subprocess.Popen()
#
# When using subprocess.Popen() to spawn a long-lived external command,
# such as ffmpeg, be sure to include the "close_fds=True" argument.
#
# https://docs.python.org/3/library/subprocess.html#subprocess.Popen
#
# This is especially important for extensions responding to
# on_episode_downloaded(), which runs whenever a download finishes.
#
# Otherwise that process will inherit ALL file descriptors gPodder
# happens to have open at the moment (like other active downloads).
# Those files will remain 'in-use' until that process exits, a race
# condition which prevents gPodder from renaming or deleting them on Windows.
#
# Caveat: On Windows, you cannot set close_fds to true and also
# redirect the standard handles (stdin, stdout or stderr). To collect
# output/errors from long-lived external commands, it may be necessary
# to create a (temp) log file and read it afterward.
