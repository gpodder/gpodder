import unittest
from test import test_support

from libgpodder import ChannelList
from libpodcasts import podcastChannel

class ChannelListTestCase(unittest.TestCase):

    # Only use setUp() and tearDown() if necessary

    def setUp(self):
        self.cur_list = ChannelList()


    def test_add_chan_as_chan(self):
        cur_chan = podcastChannel('http://www.osnews.com/files/podcast.xml')
        self.cur_list.append(cur_chan)
        self.failUnlessEqual(len(self.cur_list), 1)
        self.failUnless(isinstance(self.cur_list[0], podcastChannel))
        
    def test_add_chan_by_url(self):
        self.cur_list.append('http://www.osnews.com/files/podcast.xml')
        self.failUnlessEqual(len(self.cur_list), 1)
        self.failUnless(isinstance(self.cur_list[0], podcastChannel))

    def test_add_invalid_channel(self):
        self.cur_list.append('invalid url')
        self.failUnlessEqual(len(self.cur_list), 0)

    def test_add_dupe(self):
        cur_chan = podcastChannel('http://www.osnews.com/files/podcast.xml')
        self.cur_list.append(cur_chan)
        self.cur_list.append('http://www.osnews.com/files/podcast.xml')
        self.failUnlessEqual(len(self.cur_list), 1)

        
def test_main():
    test_support.run_unittest(ChannelListTestCase)

if __name__ == '__main__':
    test_main()
