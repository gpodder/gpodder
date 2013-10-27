#
# gpodder.query - Episode Query Language (EQL) implementation (2010-11-29)
# Copyright (c) 2010-2013, Thomas Perl <m@thp.io>
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


import gpodder

import re
import datetime

class Matcher(object):
    """Match implementation for EQL

    This class implements the low-level matching of
    EQL statements against episode objects.
    """

    def __init__(self, episode):
        self._episode = episode

    def match(self, term):
        try:
            return bool(eval(term, {'__builtins__': None}, self))
        except Exception as e:
            print(e)
            return False

    def __getitem__(self, k):
        episode = self._episode

        # Adjectives (for direct usage)
        if k == 'new':
            return (episode.state == gpodder.STATE_NORMAL and episode.is_new)
        elif k in ('downloaded', 'dl'):
            return episode.state == gpodder.STATE_DOWNLOADED
        elif k in ('deleted', 'rm'):
            return episode.state == gpodder.STATE_DELETED
        elif k == 'played':
            return not episode.is_new
        elif k == 'downloading':
            return episode.downloading
        elif k == 'archive':
            return episode.archive
        elif k in ('finished', 'fin'):
            return episode.is_finished()
        elif k in ('video', 'audio'):
            return episode.file_type() == k
        elif k == 'torrent':
            return episode.url.endswith('.torrent') or 'torrent' in episode.mime_type

        # Nouns (for comparisons)
        if k in ('megabytes', 'mb'):
            return float(episode.file_size) / (1024*1024)
        elif k == 'title':
            return episode.title
        elif k == 'description':
            return episode.description
        elif k == 'since':
            return (datetime.datetime.now() - datetime.datetime.fromtimestamp(episode.published)).days
        elif k == 'age':
            return episode.age_in_days()
        elif k in ('minutes', 'min'):
            return float(episode.total_time) / 60
        elif k in ('remaining', 'rem'):
            return float(episode.total_time - episode.current_position) / 60

        raise KeyError(k)


class EQL(object):
    """A Query in EQL

    Objects of this class represent a query on episodes
    using EQL. Example usage:

    >>> q = EQL('downloaded and megabytes > 10')

    Regular expression queries are also supported:

    >>> q = EQL('/^The.*/')

    >>> q = EQL('/community/i')

    Normal string matches are also supported:

    >>> q = EQL('"S04"')

    >>> q = EQL("'linux'")
    """

    def __init__(self, query):
        self._query = query
        self._flags = 0
        self._regex = False
        self._string = False

        # Regular expression based query
        match = re.match(r'^/(.*)/(i?)$', query)
        if match is not None:
            self._regex = True
            self._query, flags = match.groups()
            if flags == 'i':
                self._flags |= re.I

        # String based query
        match = re.match("^([\"'])(.*)(\\1)$", query)
        if match is not None:
            self._string = True
            a, query, b = match.groups()
            self._query = query.lower()

        # For everything else, compile the expression
        if not self._regex and not self._string:
            try:
                self._query = compile(query, '<eql-string>', 'eval')
            except Exception as e:
                print(e)
                self._query = None


    def match(self, episode):
        if self._query is None:
            return False

        if self._regex:
            return re.search(self._query, episode.title, self._flags) is not None
        elif self._string:
            return self._query in episode.title.lower()

        return Matcher(episode).match(self._query)

    def filter(self, episodes):
        return list(filter(self.match, episodes))


def UserEQL(query):
    """EQL wrapper for user input

    Automatically adds missing quotes around a
    non-EQL string for user-based input. In this
    case, EQL queries need to be enclosed in ().
    """

    if query is None:
        return None

    if query == '' or (query and query[0] not in "(/'\""):
        return EQL("'%s'" % query)
    else:
        return EQL(query)


