
# Use a logger for debug output - this will be managed by gPodder
import logging
logger = logging.getLogger(__name__)

# Provide some metadata that will be displayed in the gPodder GUI
__title__ = 'Hello World Extension'
__description__ = 'Explain in one sentence what this extension does.'
__only_for__ = 'gtk, cli, qml'
__authors__ = 'Thomas Perl <m@thp.io>'

class gPodderExtension:
    # The extension will be instantiated the first time it's used
    # You can do some sanity checks here and raise an Exception if
    # you want to prevent the extension from being loaded..
    def __init__(self, container):
        self.container = container

    # This function will be called when the extension is enabled or
    # loaded. This is when you want to create helper objects or hook
    # into various parts of gPodder.
    def on_load(self):
        logger.info('Extension is being loaded.')
        print '='*40
        print 'container:', self.container
        print 'container.manager:', self.container.manager
        print 'container.config:', self.container.config
        print 'container.manager.core:', self.container.manager.core
        print 'container.manager.core.db:', self.container.manager.core.db
        print 'container.manager.core.config:', self.container.manager.core.config
        print 'container.manager.core.model:', self.container.manager.core.model
        print '='*40

    # This function will be called when the extension is disabled or
    # when gPodder shuts down. You can use this to destroy/delete any
    # objects that you created in on_load().
    def on_unload(self):
        logger.info('Extension is being unloaded.')

