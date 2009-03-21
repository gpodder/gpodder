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
#


# Run Doctests and Unittests for gPodder modules
# 2009-02-25 Thomas Perl <thp@gpodder.org>


import doctest
import unittest
import gettext

# Which package and which modules in the package should be tested?
package = 'gpodder'
modules = ['util', 'libtagupdate']

suite = unittest.TestSuite()

for module in modules:
    m = __import__('.'.join((package, module)), fromlist=[module])
    # Emulate a globally-installed no-op gettext _() function
    if not hasattr(m, '_'):
        setattr(m, '_', lambda x: x)
    suite.addTest(doctest.DocTestSuite(m))

runner = unittest.TextTestRunner(verbosity=2)
runner.run(suite)

