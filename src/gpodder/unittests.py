# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2015 Thomas Perl and the gPodder Team
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

# Main package and test package (for modules in main package)
package = 'gpodder'
test_package = '.'.join((package, 'test'))

suite = unittest.TestSuite()
coverage_modules = []


# Modules (in gpodder) for which doctests exist
# ex: Doctests embedded in "gpodder.util", coverage reported for "gpodder.util"
doctest_modules = ['util', 'jsonconfig']

for module in doctest_modules:
    doctest_mod = __import__('.'.join((package, module)), fromlist=[module])

    suite.addTest(doctest.DocTestSuite(doctest_mod))
    coverage_modules.append(doctest_mod)


# Modules (in gpodder) for which unit tests (in gpodder.test) exist
# ex: Tests are in "gpodder.test.model", coverage reported for "gpodder.model"
test_modules = ['model']

for module in test_modules:
    test_mod = __import__('.'.join((test_package, module)), fromlist=[module])
    coverage_mod = __import__('.'.join((package, module)), fromlist=[module])

    suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_mod))
    coverage_modules.append(coverage_mod)

try:
    # If you want a HTML-based test report, install HTMLTestRunner from:
    # http://tungwaiyip.info/software/HTMLTestRunner.html
    import HTMLTestRunner
    REPORT_FILENAME = 'test_report.html'
    runner = HTMLTestRunner.HTMLTestRunner(stream=open(REPORT_FILENAME, 'w'))
    print """
    HTML Test Report will be written to %s
    """ % REPORT_FILENAME
except ImportError:
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

