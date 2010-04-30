# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Loads and executes user hooks.

Hooks are python scripts in ~/.config/gpodder/hooks. Each script
must define a class named "gPodderHooks", otherwise it will be ignored.

The hooks class defines several callbacks that will be called by the
gPodder application at certain points. See the methods defined below
for a list on what these callbacks are and the parameters they take.

For an example extension see doc/dev/examples/hooks.py
"""

import glob
import imp
import os
import functools

import gpodder

from gpodder.liblogger import log


def call_hooks(func):
    """Decorator to create handler functions in HookManager

    Calls the specified function in all user extensions that define it.
    """
    method_name = func.__name__

    @functools.wraps(func)
    def handler(self, *args, **kwargs):
        for filename, module in self.modules:
            try:
                callback = getattr(module, method_name, None)
                if callback is not None:
                    callback(*args, **kwargs)
            except Exception, e:
                log('Error in %s, function %s: %s', filename, method_name, \
                        e, traceback=True, sender=self)
        func(self, *args, **kwargs)

    return handler


class HookManager(object):
    # The class name that has to appear in a hook module
    HOOK_CLASS = 'gPodderHooks'

    def __init__(self):
        """Create a new hook manager"""
        self.modules = []

        for filename in glob.glob(os.path.join(gpodder.home, 'hooks', '*.py')):
          try:
              module = self._load_module(filename)
              if module is not None:
                  self.modules.append((filename, module))
                  log('Module loaded: %s', filename, sender=self)
          except Exception, e:
              log('Error loading %s: %s', filename, e, sender=self)

    def has_modules(self):
        """Check whether this manager manages any modules

        Returns True if there is at least one module that is
        managed by this manager, or False if no modules are
        loaded (in this case, the hook manager can be deactivated).
        """
        return bool(self.modules)

    def _load_module(self, filepath):
        """Load a Python module by filename

        Returns an instance of the HOOK_CLASS class defined
        in the module, or None if the module does not contain
        such a class.
        """
        basename, extension = os.path.splitext(os.path.basename(filepath))
        module = imp.load_module(basename, file(filepath, 'r'), os.path.dirname(filepath), (extension, 'r', imp.PY_SOURCE))
        hook_class = getattr(module, HookManager.HOOK_CLASS, None)

        if hook_class is None:
            return None
        else:
            return hook_class()

    # Define all known handler functions here, decorate them with the
    # "call_hooks" decorator to forward all calls to hook scripts that have
    # the same function defined in them. If the handler functions here contain
    # any code, it will be called after all the hooks have been called.

    @call_hooks
    def on_podcast_updated(self, podcast):
        """Called when a podcast feed was updated

        This hook will be called even if there were no new episodes.

        @param podcast: A gpodder.model.PodcastChannel instance
        """
        pass

    @call_hooks
    def on_podcast_save(self, podcast):
        """Called when a podcast is saved to the database

        This hooks will be called when the user edits the metadata of
        the podcast or when the feed was updated.

        @param podcast: A gpodder.model.PodcastChannel instance
        """
        pass

    @call_hooks
    def on_episode_save(self, episode):
        """Called when an episode is saved to the database

        This hook will be called when a new episode is added to the
        database or when the state of an existing episode is changed.

        @param episode: A gpodder.model.PodcastEpisode instance
        """
        pass

    @call_hooks
    def on_file_copied_to_filesystem(self, device, from_file, to_file):
        """Called when an episode is copied to the MP3PlayerDevice device

        This hook will be called when a new episode is added to the
        MP3PlayerDevice device.

        @param device: A gpodder.sync.MP3PlayerDevice instance
        @param from_file: Path to the original file that needs to be copied
        @param to_file: Path to the destination file that needs to be copied
        """
        pass

    @call_hooks
    def on_file_copied_to_ipod(self, device, from_file):
        """Called when an episode is copied to the iPodDevice device

        This hook will be called when a new episode is added to the
        iPodDevice device.

        @param device: A gpodder.sync.iPodDevice instance
        @param from_file: Path to the original file that needs to be copied
        """
        pass

    @call_hooks
    def on_file_copied_to_mtp(self, device, from_file, to_file):
        """Called when an episode is copied to the MTPDevice device

        This hook will be called when a new episode is added to the
        MTPDevice device.

        @param device: A gpodder.sync.MTPDevice instance
        @param from_file: Path to the original file that needs to be copied
        @param to_file: Path to the destination file that needs to be copied
        """
        pass

