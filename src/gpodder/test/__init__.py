# -*- coding: utf-8 -*-
#
# gpodder.test - Run doctests and unittests for gPodder modules (2009-02-25)
# Copyright (c) 2006-2013, Thomas Perl <m@thp.io>
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


import doctest
import unittest
import sys

try:
    # Unused here locally, but we import it to be able to give an early
    # warning about this missing dependency in order to avoid bogus errors.
    import minimock
except ImportError as e:
    print("""
    Error: Unit tests require the "minimock" module (python-minimock).
    Please install it before running the unit tests.
    """, file=sys.stderr)
    sys.exit(2)

# Main package and test package (for modules in main package)
package = 'gpodder'
test_package = '.'.join((package, 'test'))

suite = unittest.TestSuite()
coverage_modules = []


# Modules (in gpodder) for which doctests exist
# ex: Doctests embedded in "gpodder.util", coverage reported for "gpodder.util"
doctest_modules = ['gpodder.util', 'jsonconfig', 'podcastparser']

for module in doctest_modules:
    doctest_mod = __import__(module, fromlist=[module])

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
    print("""
    HTML Test Report will be written to %s
    """ % REPORT_FILENAME)
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
        print("""
        No coverage reporting done (Python module "coverage" is missing)
        Please install the python-coverage package to get coverage reporting.
        """, file=sys.stderr)

