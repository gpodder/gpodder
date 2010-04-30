# -*- coding: utf-8 -*-
# Example hooks script for gPodder.
# To use, copy it as a Python script into ~/.config/gpodder/hooks/mySetOfHooks.py
# See the module "gpodder.hooks" for a description of when each hook
# gets called and what the parameters of each hook are.

import gpodder

from gpodder.liblogger import log

class gPodderHooks(object):
    def __init__(self):
        log('Example extension is initializing.')

    def on_podcast_updated(self, podcast):
        log(u'on_podcast_updated(%s)' % podcast.title)

    def on_podcast_save(self, podcast):
        log(u'on_podcast_save(%s)' % podcast.title)

    def on_episode_save(self, episode):
        log(u'on_episode_save(%s)' % episode.title)

    def on_file_copied_to_filesystem(self, mp3playerdevice, from_file, to_file):
        log(u'on_file_copied_to_filesystem(%s, %s)' % (from_file, to_file))

    def on_file_copied_to_ipod(self, ipoddevice, from_file):
        log(u'on_file_copied_to_ipod(%s)' % from_file)

    def on_file_copied_to_mtp(self, mtpdevice, from_file, to_file):
        log(u'on_file_copied_to_mtp(%s, %s)' % (from_file, to_file))
