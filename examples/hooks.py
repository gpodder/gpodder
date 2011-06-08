# -*- coding: utf-8 -*-
# Example hooks script for gPodder.
# To use, copy it as a Python script into $GPODDER_HOME/Hooks/mySetOfHooks.py
# (The default value of $GPODDER_HOME is ~/gPodder/ on Desktop installations)
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

    def on_episode_downloaded(self, episode):
        log(u'on_episode_downloaded(%s)' % episode.title)

    def on_episode_save(self, episode):
        log(u'on_episode_save(%s)' % episode.title)

    def on_episodes_context_menu(self, episodes):
        log(u'on_episodes_context_menu(%d episodes)', % len(episodes))

