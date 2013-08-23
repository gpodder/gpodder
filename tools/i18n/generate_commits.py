#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# generate_commits.py - Generate Git commits based on Transifex updates (2012-08-16)
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


import re
import glob
import subprocess

filenames = []

process = subprocess.Popen(['git', 'status', '--porcelain'] +
        glob.glob('po/*.po'), stdout=subprocess.PIPE)
stdout, stderr = process.communicate()
for line in stdout.splitlines():
    status, filename = line.strip().split()
    if status == 'M':
        filenames.append(filename)

for filename in filenames:
    in_translators = False
    translators = []
    language = None

    for line in open(filename).read().splitlines():
        if line.startswith('# Translators:'):
            in_translators = True
        elif in_translators:
            match = re.match(r'# ([^<]* <[^>]*>)', line)
            if match:
                translators.append(match.group(1))
            else:
                in_translators = False
        elif line.startswith('"Last-Translator:'):
            match = re.search(r'Last-Translator: ([^<]* <[^>]*>)', line)
            if match:
                translators.append(match.group(1))

        match = re.match(r'"Language-Team: (.+) \(http://www.transifex.com/', line)
        if not match:
            match = re.match(r'"Language-Team: ([^\(]+).*\\n"', line, re.DOTALL)
        if match:
            language = match.group(1).strip()

    if translators and language is not None:
        if len(translators) != 1:
            print '# Warning: %d other translators: %s' % (len(translators) - 1, ', '.join(translators[1:]))
        print 'git commit --author="%s" --message="Updated %s translation" %s' % (translators[0], language, filename)
    else:
        print '# FIXME (could not parse):', '!'*10, filename, '!'*10

