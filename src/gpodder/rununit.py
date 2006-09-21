#!/usr/bin/python

import sys
sys.path = ['./src/gpodder','../src/gpodder', ] + sys.path
import glob
import unittest
from test import test_support
from test_channel_list import ChannelListTestCase, ChannelListDelTestCase

def test_main():
    """Runs all the unittest in the current directory"""
    test_support.run_unittest(ChannelListTestCase,
                              ChannelListDelTestCase)


if __name__ == '__main__':
    test_main()
