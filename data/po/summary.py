#!/usr/bin/python
# summary.py - Text-based visual translation completeness summary
# Thomas Perl <thp@gpodder.org>, 2009-01-03
#
# Usage: make statistics | python summary.py
#

import sys
import re
import math

width = 40

class Language(object):
    def __init__(self, code, updated, translated, fuzzy, untranslated):
        self.code = code
        self.updated = updated
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

for line in sys.stdin:
    match = re.match('^(..)\.po \(([^)]*)\): ((\d+) translated message[s]?)?(, (\d+) fuzzy translation[s]?)?(, (\d+) untranslated message[s]?)?\.', line).groups()
    languages.append(Language(match[0], match[1], match[3] or '0', match[5] or '0', match[7] or '0'))

print ''
print '                   --== gPodder translation summary == --'
print ''

for language in sorted(languages):
    tc = '#'*(int(math.floor(width*language.get_translated_ratio())))
    fc = '~'*(int(math.floor(width*language.get_fuzzy_ratio())))
    uc = ' '*(width-len(tc)-len(fc))
    
    print ' %s (%s) [%s%s%s] -- %3.0f %% translated' % (language.code, language.updated, tc, fc, uc, language.get_translated_ratio()*100)

print ''
print '   Total translations: %d' % len(languages)
print ''

