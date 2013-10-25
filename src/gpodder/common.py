#
# gpodder.common - Common helper functions for all UIs (2012-08-16)
# Copyright (c) 2012, 2013, Thomas Perl <m@thp.io>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.
#


import gpodder

from gpodder import util

import glob
import os

import logging
logger = logging.getLogger(__name__)


def clean_up_downloads(directory, delete_partial=False):
    """Clean up temporary files left behind by old gPodder versions

    delete_partial - If True, also delete in-progress downloads
    """
    temporary_files = glob.glob('%s/*/.tmp-*' % directory)

    if delete_partial:
        temporary_files += glob.glob('%s/*/*.partial' % directory)

    for tempfile in temporary_files:
        util.delete_file(tempfile)


def find_partial_downloads(directory, channels, start_progress_callback, progress_callback, finish_progress_callback):
    """Find partial downloads and match them with episodes

    directory - Download directory
    channels - A list of all model.PodcastChannel objects
    start_progress_callback - A callback(count) when partial files are searched
    progress_callback - A callback(title, progress) when an episode was found
    finish_progress_callback - A callback(resumable_episodes) when finished
    """
    # Look for partial file downloads
    partial_files = glob.glob(os.path.join(directory, '*', '*.partial'))
    count = len(partial_files)
    resumable_episodes = []
    if count:
        start_progress_callback(count)
        candidates = [f[:-len('.partial')] for f in partial_files]
        found = 0

        for channel in channels:
            for episode in channel.episodes:
                filename = episode.local_filename(create=False, check_only=True)
                if filename in candidates:
                    found += 1
                    progress_callback(episode.title, float(found)/count)
                    candidates.remove(filename)
                    partial_files.remove(filename+'.partial')

                    if os.path.exists(filename):
                        # The file has already been downloaded;
                        # remove the leftover partial file
                        util.delete_file(filename+'.partial')
                    else:
                        resumable_episodes.append(episode)

                if not candidates:
                    break

            if not candidates:
                break

        for f in partial_files:
            logger.warn('Partial file without episode: %s', f)
            util.delete_file(f)

        finish_progress_callback(resumable_episodes)
    else:
        clean_up_downloads(directory, True)

def get_expired_episodes(channels, config):
    for channel in channels:
        for index, episode in enumerate(channel.get_episodes(gpodder.STATE_DOWNLOADED)):
            # Never consider archived episodes as old
            if episode.archive:
                continue

            # Download strategy "Only keep latest"
            if (channel.download_strategy == channel.STRATEGY_LATEST and
                    index > 0):
                logger.info('Removing episode (only keep latest strategy): %s',
                        episode.title)
                yield episode
                continue

            # Only expire episodes if the age in days is positive
            if config.episode_old_age < 1:
                continue

            # Never consider fresh episodes as old
            if episode.age_in_days() < config.episode_old_age:
                continue

            # Do not delete played episodes (except if configured)
            if not episode.is_new:
                if not config.auto_remove_played_episodes:
                    continue

            # Do not delete unfinished episodes (except if configured)
            if not episode.is_finished():
                if not config.auto_remove_unfinished_episodes:
                    continue

            # Do not delete unplayed episodes (except if configured)
            if episode.is_new:
                if not config.auto_remove_unplayed_episodes:
                    continue

            yield episode

