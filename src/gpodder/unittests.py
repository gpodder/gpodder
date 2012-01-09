# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2012 Thomas Perl and the gPodder Team
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
import sys

try:
    # Unused here locally, but we import it to be able to give an early
    # warning about this missing dependency in order to avoid bogus errors.
    import minimock
except ImportError, e:
    print >>sys.stderr, """
    Error: Unit tests require the "minimock" module (python-minimock).
    Please install it before running the unit tests.
    """
    sys.exit(2)

# Which package and which modules in the package should be tested?
package = 'gpodder'
modules = ['util']
coverage_modules = []

suite = unittest.TestSuite()

for module in modules:
    m = __import__('.'.join((package, module)), fromlist=[module])
    coverage_modules.append(m)
    suite.addTest(doctest.DocTestSuite(m))

runner = unittest.TextTestRunner(verbosity=2)

try:
    import coverage
except ImportError:
    coverage = None

if __name__ == '__main__':
    if coverage is not None:
        coverage.erase()
        coverage.start()

    result = runner.run(suite)

    if not result.wasSuccessful():
        sys.exit(1)

    if coverage is not None:
        coverage.stop()
        coverage.report(coverage_modules)
        coverage.erase()
    else:
        print >>sys.stderr, """
        No coverage reporting done (Python module "coverage" is missing)
        Please install the python-coverage package to get coverage reporting.
        """

