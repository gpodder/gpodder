# -*- coding: utf-8 -*-
# Automatically open .torrent files with a BitTorrent client
# Copy this script to ~/.config/gpodder/hooks/ to enable it.
# Thomas Perl <thp@gpodder.org>; 2010-10-11

# Set this to the BitTorrent app of your choice
BITTORRENT_CMD = 'qbittorrent'

import subprocess

class gPodderHooks(object):
    def on_episode_downloaded(self, episode):
        if episode.extension() == '.torrent':
            subprocess.Popen([BITTORRENT_CMD, episode.local_filename(False)])

