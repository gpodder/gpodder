#!/usr/bin/python
# summary.py - Text-based visual translation completeness summary
# Thomas Perl <thp@gpodder.org>, 2009-01-03
#
# Usage: make statistics | python summary.py
#

import sys
import re
import math
import glob
import os
import subprocess

width = 40

class Language(object):
    def __init__(self, language, translated, fuzzy, untranslated):
        self.language = language
        self.translated = int(translated)
        self.fuzzy = int(fuzzy)
        self.untranslated = int(untranslated)

    def get_translated_ratio(self):
        return float(self.translated)/float(self.translated+self.fuzzy+self.untranslated)

    def get_fuzzy_ratio(self):
        return float(self.fuzzy)/float(self.translated+self.fuzzy+self.untranslated)

    def get_untranslated_ratio(self):
        return float(self.untranslated)/float(self.translated+self.fuzzy+self.untranslated)

    def __cmp__(self, other):
        return cmp(self.get_translated_ratio(), other.get_translated_ratio())

languages = []

COUNTS_RE = '((\d+) translated message[s]?)?(, (\d+) fuzzy translation[s]?)?(, (\d+) untranslated message[s]?)?\.'

for filename in glob.glob('*.po'):
    language, _ = os.path.splitext(filename)
    msgfmt = subprocess.Popen(['msgfmt', '--statistics', filename],
            stderr=subprocess.PIPE)
    _, stderr = msgfmt.communicate()

    match = re.match(COUNTS_RE, stderr).groups()
    languages.append(Language(language, match[1] or '0', match[3] or '0', match[5] or '0'))

print ''
for language in sorted(languages):
    tc = '#'*(int(math.floor(width*language.get_translated_ratio())))
    fc = '~'*(int(math.floor(width*language.get_fuzzy_ratio())))
    uc = ' '*(width-len(tc)-len(fc))

    print ' %5s [%s%s%s] -- %3.0f %% translated' % (language.language, tc, fc, uc, language.get_translated_ratio()*100)

print """
  Total translations: %s
""" % (len(languages))

