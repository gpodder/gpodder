#
# test_parser.py: Test Runner for the podcastparser (2012-12-29)
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


import os
import glob
import json
import sys

here = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(here, '..', '..', 'src'))

from gpodder import log
log.setup(verbose=True)

import podcastparser

RSS_FILES = os.path.join(here, 'data', '*.rss')

for rss_filename in glob.glob(RSS_FILES):
    basename, _ = os.path.splitext(rss_filename)
    json_filename = basename + '.json'

    expected = json.load(open(json_filename))
    parsed = podcastparser.parse('file://' + rss_filename, open(rss_filename))

    if expected != parsed:
        print('FAIL:    ', basename)
        print('='*40)
        print('EXPECTED:', json.dumps(expected, indent=2))
        print('='*40)
        print('PARSED:  ', json.dumps(parsed, indent=2))
        print('='*40)
        sys.exit(1)
    else:
        print('OK:      ', basename)

