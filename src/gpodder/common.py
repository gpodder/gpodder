# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2018 The gPodder Team
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
#

# gpodder.common - Common helper functions for all UIs
# Thomas Perl <thp@gpodder.org>; 2012-08-16


import glob
import logging
import os

import gpodder
from gpodder import util

logger = logging.getLogger(__name__)


def clean_up_downloads(delete_partial=False):
    """Clean up temporary files left behind by old gPodder versions

    delete_partial - If True, also delete in-progress downloads
    """
    temporary_files = glob.glob('%s/*/.tmp-*' % gpodder.downloads)

    if delete_partial:
        temporary_files += glob.glob('%s/*/*.partial' % gpodder.downloads)
        # youtube-dl creates .partial.* files for adaptive formats
        temporary_files += glob.glob('%s/*/*.partial.*' % gpodder.downloads)

    for tempfile in temporary_files:
        util.delete_file(tempfile)


def find_partial_downloads(channels, start_progress_callback, progress_callback, final_progress_callback, finish_progress_callback):
    """Find partial downloads and match them with episodes

    channels - A list of all model.PodcastChannel objects
    start_progress_callback - A callback(count) when partial files are searched
    progress_callback - A callback(title, progress) when an episode was found
    finish_progress_callback - A callback(resumable_episodes) when finished
    """
    # Look for partial file downloads, ignoring .partial.* files created by youtube-dl
    partial_files = glob.glob(os.path.join(gpodder.downloads, '*', '*.partial'))
    count = len(partial_files)
    resumable_episodes = []
    start_progress_callback(count)
    if count:
        candidates = [f[:-len('.partial')] for f in partial_files]
        found = 0

        for channel in channels:
            for episode in channel.get_all_episodes():
                filename = episode.local_filename(create=False, check_only=True)
                if filename in candidates:
                    found += 1
                    progress_callback(episode.title, found / count)
                    candidates.remove(filename)
                    partial_files.remove(filename + '.partial')

                    if os.path.exists(filename):
                        # The file has already been downloaded;
                        # remove the leftover partial file
                        util.delete_file(filename + '.partial')
                    else:
                        resumable_episodes.append(episode)

                if not candidates:
                    break

            if not candidates:
                break

        final_progress_callback()

        for f in partial_files:
            logger.warning('Partial file without episode: %s', f)
            util.delete_file(f)

    # never delete partial: either we can't clean them up because we offer to
    # resume download or there are none to delete in the first place.
    clean_up_downloads(delete_partial=False)
    finish_progress_callback(resumable_episodes)


def get_expired_episodes(channels, config):
    for channel in channels:
        for index, episode in enumerate(channel.get_episodes(gpodder.STATE_DOWNLOADED)):
            # Never consider archived episodes as old
            if episode.archive:
                continue

            # Download strategy "Only keep latest"
            if (channel.download_strategy == channel.STRATEGY_LATEST
                    and index > 0):
                logger.info('Removing episode (only keep latest strategy): %s',
                        episode.title)
                yield episode
                continue

            # Only expire episodes if the age in days is positive
            if config.auto.cleanup.days < 1:
                continue

            # Never consider fresh episodes as old
            if episode.age_in_days() < config.auto.cleanup.days:
                continue

            # Do not delete played episodes (except if configured)
            if not episode.is_new:
                if not config.auto.cleanup.played:
                    continue

            # Do not delete unfinished episodes (except if configured)
            if not episode.is_finished():
                if not config.auto.cleanup.unfinished:
                    continue

            # Do not delete unplayed episodes (except if configured)
            if episode.is_new:
                if not config.auto.cleanup.unplayed:
                    continue

            yield episode
