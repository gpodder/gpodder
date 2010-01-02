# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2010 Thomas Perl and the gPodder Team
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

import sys

import gpodder

from gpodder import sync
from gpodder.model import PodcastChannel

_ = gpodder.gettext

def synchronize_device(db, config):
    device = sync.open_device(config)
    if device is None:
        print >>sys.stderr, _('No device configured.')
        return False

    def msg(s):
        print >>sys.stderr, s

    device.register('status', msg)
    callback_progress = lambda i, n: msg(_('Synchronizing: %d of %d') % (i, n))
    device.register('progress', callback_progress)

    if device.open():
        channels = [c for c in PodcastChannel.load_from_db(db, \
                config.download_dir) if c.sync_to_devices]

        for channel in channels:
            episodes = [e for e in channel.get_downloaded_episodes() \
                    if e.was_downloaded(and_exists=True)]
            device.add_tracks(episodes)

        db.commit()
        device.close()
        print >>sys.stderr, _('Device synchronized successfully.')
        return True
    else:
        print >>sys.stderr, _('Error: Cannot open device!')
        return False

