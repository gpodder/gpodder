# -*- coding: utf-8 -*-
#
# Example user extension.

from gpodder.liblogger import log

class Extension:
    def __init__(self):
        log('Example extension is initializing.')

    def on_channel_updated(self, channel):
        """
        Called when a channel feed was updated, whether or not there were
        new episodes.
        """
        log(u'on_channel_updated(%s)' % channel.title)

    def on_channel_save(self, channel):
        """
        Called when a channel is saved to the database, e.g. when the user
        edits the description, or the feed was updated.
        """
        log(u'on_channel_save(%s)' % channel.title)

    def on_episode_save(self, episode):
        """
        Called when an episode is added to the database or its state was
        changed (e.g., the enclosure was downloaded).
        """
        log(u'on_episode_save(%s)' % episode.title)
