# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
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

# gpodder.liblogger - DEPRECATED logging facility
# Thomas Perl, 2011-07-15

# XXX Deprecation warning XXX
# This module is here to support old hooks scripts that have not
# yet been rewritten to utilize the standard 'logging' module.
# Please do not use this DEPRECATED module in new code!
# XXX Deprecation warning XXX

import logging
logger = logging.getLogger('DEPRECATED:' + __name__)

def log(message, *args, **kwargs):
    """DEPRECATED - do not use in new code!"""
    logger.info(message % args, exc_info=True)

