# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2018 The gPodder Team
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


#
#  gpodder.query - Episode Query Language (EQL) implementation (2010-11-29)
#

import datetime
import re

import gpodder


class Matcher(object):
    """Match implementation for EQL

    This class implements the low-level matching of
    EQL statements against episode objects.
    """

    def __init__(self, episode):
        self._episode = episode

    def match(self, term):
        try:
            # case-sensitive search in haystack, or both title and description if no haystack
            def S(needle, haystack=None):
                if haystack is not None:
                    return (needle in haystack)
                if needle in self._episode.title:
                    return True
                return (needle in self._episode._text_description)

            # case-insensitive search in haystack, or both title and description if no haystack
            def s(needle, haystack=None):
                needle = needle.casefold()
                if haystack is not None:
                    return (needle in haystack.casefold())
                if needle in self._episode.title.casefold():
                    return True
                return (needle in self._episode._text_description.casefold())

            # case-sensitive regular expression search in haystack, or both title and description if no haystack
            def R(needle, haystack=None):
                regexp = re.compile(needle)
                if haystack is not None:
                    return regexp.search(haystack)
                if regexp.search(self._episode.title):
                    return True
                return regexp.search(self._episode._text_description)

            # case-insensitive regular expression search in haystack, or both title and description if no haystack
            def r(needle, haystack=None):
                regexp = re.compile(needle, re.IGNORECASE)
                if haystack is not None:
                    return regexp.search(haystack)
                if regexp.search(self._episode.title):
                    return True
                return regexp.search(self._episode._text_description)

            return bool(eval(term, {'__builtins__': None, 'S': S, 's': s, 'R': R, 'r': r}, self))
        except Exception as e:
            return False

    def __getitem__(self, k):
        episode = self._episode

        # Adjectives (for direct usage)
        if k == 'new':
            return (episode.state == gpodder.STATE_NORMAL and episode.is_new)
        elif k in ('downloaded', 'dl'):
            return episode.was_downloaded(and_exists=True)
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
        elif k == 'paused':
            return (episode.download_task is not None
                and episode.download_task.status in (episode.download_task.PAUSED, episode.download_task.PAUSING))
        elif k == 'failed':
            return (episode.download_task is not None and episode.download_task.status == episode.download_task.FAILED)

        # Nouns (for comparisons)
        if k in ('megabytes', 'mb'):
            return episode.file_size / (1024 * 1024)
        elif k == 'title':
            return episode.title
        elif k == 'description':
            return episode._text_description
        elif k == 'since':
            return (datetime.datetime.now() - datetime.datetime.fromtimestamp(episode.published)).days
        elif k == 'age':
            return episode.age_in_days()
        elif k in ('minutes', 'min'):
            return episode.total_time / 60
        elif k in ('remaining', 'rem'):
            return (episode.total_time - episode.current_position) / 60
        elif k == 'podcast':
            return episode.channel.title
        elif k == 'section':
            return episode.channel.section
        elif k == 'url':
            return episode.url
        elif k == 'link':
            return episode.link
        elif k == 'filename':
            return episode.download_filename

        raise KeyError(k)


class EQL(object):
    """A Query in EQL

    Objects of this class represent a query on episodes
    using EQL. Example usage:

    >>> q = EQL('downloaded and megabytes > 10')
    >>> # q.filter(channel.get_all_episodes())

    >>> # EQL('new and video').match(episode)

    Regular expression queries are also supported:

    >>> q = EQL('/^The.*/')

    >>> q = EQL('/community/i')

    Normal string matches are also supported:

    >>> q = EQL('"S04"')

    >>> q = EQL("'linux'")

    The lowercase s() and r() functions perform
    case-insensitive string and regular expression
    matches:

    >>> q = EQL("s('linux')")

    >>> q = EQL("r('^the.*')")

    The uppercase S() and R() functions perform
    case-sensitive string and regular expression
    matches:

    >>> q = EQL("S('Linux')")

    >>> q = EQL("R('^The.*')")

    The S, s, R, and r functions search both
    title and description by default. Passing
    'title' or 'description' in second parameter
    refines the search:

    >>> q = EQL("s('in title', title)")

    >>> q = EQL("s('in description', description)")

    Normal EQL queries can be mixed with RegEx
    or string matching using the S, s, R and r
    functions:

    >>> # EQL('downloaded and r("The.*")')
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
                self._query = None

    def match(self, episode):
        if self._query is None:
            return False

        if self._regex:
            return re.search(self._query, episode.title, self._flags) is not None
        elif self._string:
            return self._query in episode.title.lower() or self._query in episode._text_description.lower()

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
