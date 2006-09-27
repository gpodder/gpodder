import unittest
from test import test_support

from libgpodder import ChannelList
from libpodcasts import podcastChannel

import StringIO

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

    def test_add_dupe(self):
        cur_chan = podcastChannel('http://www.osnews.com/files/podcast.xml')
        self.cur_list.append(cur_chan)
        self.cur_list.append('http://www.osnews.com/files/podcast.xml')
        self.failUnlessEqual(len(self.cur_list), 1)

    def test_load_from_file(self):
        chan_file = StringIO.StringIO("""<!-- gPodder channel list -->
<channels>
  <channel name="dialoglepodcastdesnouvellestechnologies">
    <url>http://www.cisco.com/global/FR/minisites/2006/dialog/podcast/News_Podcast_20.xml</url>
    <download_dir>/home/informancer/.config/gpodder/downloads/dialoglepodcastdesnouvellestechnologies/dialoglepodcastdesnouvellestechnologies/dialoglepodcastdesnouvellestechnologies/dialoglepodcastdesnouvellestechnologies/</download_dir>
  </channel>
  <channel name="theprojectmanagementpodcast">
    <url>http://home.tiscalinet.ch/cornelius.fichtner/pmpodcast/pmpodcast.xml</url>
    <download_dir>/home/informancer/.config/gpodder/downloads/theprojectmanagementpodcast/theprojectmanagementpodcast/theprojectmanagementpodcast/theprojectmanagementpodcast/</download_dir>
  </channel>
  <channel name="osnewscom">
    <url>http://www.osnews.com/files/podcast.xml</url>
    <download_dir>/home/informancer/.config/gpodder/downloads/osnewscom/osnewscom/osnewscom/osnewscom/</download_dir>
  </channel>
</channels>
""")
        self.cur_list.load_from_file(chan_file)
        self.failUnlessEqual(len(self.cur_list), 3)

    def test_save_to_file(self):
        self.cur_list.append('http://www.osnews.com/files/podcast.xml')
        self.cur_list.append('http://home.tiscalinet.ch/cornelius.fichtner/pmpodcast/pmpodcast.xml')
        chans = StringIO.StringIO()
        self.cur_list.save_to_file(chans)
        chans.seek(0)
        loaded_list = ChannelList()
        loaded_list.load_from_file(chans)
        self.failUnlessEqual(len(loaded_list), 2)

class ChannelListDelTestCase(unittest.TestCase):
    def setUp(self):
        self.cur_list = ChannelList()
        self.cur_list.append('http://www.osnews.com/files/podcast.xml')

    def test_del_by_index(self):
        del self.cur_list[0]
        self.failUnlessEqual(len(self.cur_list), 0)

    def test_del_by_object(self):
        del self.cur_list[self.cur_list[0]]
        self.failUnlessEqual(len(self.cur_list), 0)
        
def test_main():
    test_support.run_unittest(ChannelListTestCase,
                              ChannelListDelTestCase)

if __name__ == '__main__':
    test_main()
