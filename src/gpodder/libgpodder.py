# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
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
#  libgpodder.py -- gpodder configuration
#  thomas perl <thp@perli.net>   20051030
#
#

import gtk
import gtk.gdk
import thread
import threading
import urllib
import shutil
import xml.dom.minidom

import gpodder
from gpodder import util
from gpodder import opml
from gpodder import config
from gpodder import dumbshelve
from gpodder.dbsqlite import db

import os
import os.path
import glob
import types
import subprocess
import sys

from liblogger import log

import shlex

_ = gpodder.gettext


class gPodderLib(object):
    def __init__( self):
        log('Creating gPodderLib()', sender=self)
        gpodder_dir = os.path.expanduser(os.path.join('~', '.config', 'gpodder'))
        if gpodder.interface == gpodder.MAEMO:
            old_dir = '/media/mmc2/gpodder/'
            if os.path.exists(os.path.join(old_dir, 'channels.opml')) and not os.path.exists(os.path.join(gpodder_dir, 'channels.opml')):
                # migrate from old (0.13.0 and earlier) gpodder maemo versions
                # to the current one by moving config files from mmc2 to $HOME
                util.make_directory(gpodder_dir)
                for filename in ('channels.opml', 'database.sqlite', 'gpodder.conf'):
                    try:
                        shutil.move(os.path.join(old_dir, filename), os.path.join(gpodder_dir, filename))
                    except:
                        log('Cannot move %s from %s to %s!', filename, old_dir, gpodder_dir, sender=self, traceback=True)
                if os.path.exists(os.path.join(old_dir, 'downloads')):
                    log('Moving old downloads')
                    # move old download location to new one
                    for folder in glob.glob(os.path.join(old_dir, 'downloads', '*')):
                        try:
                            shutil.move(folder, os.path.join(old_dir, os.path.basename(folder)))
                        except:
                            log('Cannot move %s to %s!', folder, old_dir, sender=self, traceback=True)
                    try:
                        os.rmdir(os.path.join(old_dir, 'downloads'))
                    except:
                        log('Cannot remove old folder %s!', os.path.join(old_dir, 'downloads'), traceback=True)

        util.make_directory(gpodder_dir)

        self.tempdir = gpodder_dir
        self.channel_settings_file = os.path.join(gpodder_dir, 'channelsettings.pickle.db')

        self.channel_opml_file = os.path.join(gpodder_dir, 'channels.opml')
        self.channel_xml_file = os.path.join(gpodder_dir, 'channels.xml')

        if os.path.exists(self.channel_xml_file) and not os.path.exists(self.channel_opml_file):
            log('Trying to migrate channel list (channels.xml => channels.opml)', sender=self)
            self.migrate_channels_xml()

        self.config = config.Config( os.path.join( gpodder_dir, 'gpodder.conf'))

        if gpodder.interface == gpodder.MAEMO:
            # Detect changing of SD cards between mmc1/mmc2 if a gpodder
            # folder exists there (allow moving "gpodder" between SD cards or USB)
            # Also allow moving "gpodder" to home folder (e.g. rootfs on SD)
            if not os.path.exists(self.config.download_dir):
                log('Downloads might have been moved. Trying to locate them...', sender=self)
                for basedir in ['/media/mmc1', '/media/mmc2']+glob.glob('/media/usb/*')+['/home/user']:
                    dir = os.path.join(basedir, 'gpodder')
                    if os.path.exists(dir):
                        log('Downloads found in: %s', dir, sender=self)
                        self.config.download_dir = dir
                        break
                    else:
                        log('Downloads NOT FOUND in %s', dir, sender=self)

        # We need to make a seamless upgrade, so by default the video player is not specified
        # so the first time this application is run it will detect this and set it to the same 
        # as the audio player.  This keeps gPodder functionality identical to that prior to the 
        # upgrade.   The user can then set a specific video player if they so wish.	
        if self.config.videoplayer == 'unspecified':
            self.config.videoplayer = self.config.player	

        self.bluetooth_available = util.bluetooth_available()

        self.gpodder_dir = gpodder_dir
        not db.setup({ 'database': os.path.join(gpodder_dir, 'database.sqlite'), 'gl': self })

    def migrate_to_sqlite(self, add_callback, status_callback, load_channels, get_localdb):
        """
        Migrates from the 0.11.3 data storage format
        to the new SQLite-based storage format.

        add_callback should accept one parameter:
            + url (the url for a channel to be added)

        status_callback should accept two parameters:
            + percentage (a float, 0..100)
            + message (current status message, a string)

        load_channels should return the channel list

        get_localdb should accept one parameter:
            + channel (a channel object)
            and should return a list of episodes
        """
        if os.path.exists(self.channel_opml_file):
            channels = opml.Importer(gl.channel_opml_file).items
        else:
            channels = []

        p = 0.0

        # 0..40% -> import channels
        if len(channels):
            p_step = 40.0/len(channels)
            for c in channels:
                log('Importing %s', c['url'], sender=self)
                status_callback(p, _('Adding podcast: %s') % c['title'])
                add_callback(c['url'])
                p += p_step
        else:
            p = 40.0

        # 40..50% -> import localdb
        channels = load_channels()
        if len(channels):
            p_step = 10.0/len(channels)
            for channel in channels:
                status_callback(p, _('Loading LocalDB for %s') % channel.title)
                if os.path.exists(channel.index_file):
                    episodes = get_localdb(channel)
                else:
                    episodes = []
                if len(episodes):
                    p_step_2 = p_step/len(episodes)
                    for episode in episodes:
                        ### status_callback(p, _('Adding episode: %s') % episode.title)
                        # This, or all episodes will be marked as new after import.
                        episode.is_played = True
                        if (episode.file_exists()):
                            episode.mark(state=db.STATE_DOWNLOADED)
                        episode.save()
                        p += p_step_2
                    # flush the localdb updates for this channel
                    status_callback(p, _('Writing changes to database'))
                else:
                    p += p_step
        else:
            p += 10.0
            
        # 50..65% -> import download history
        download_history = HistoryStore(os.path.join(self.gpodder_dir, 'download-history.txt'))
        if len(download_history):
            p_step = 15.0/len(download_history)
            for url in download_history:
                ### status_callback(p, _('Adding to history: %s') % url)
                db.mark_episode(url, state=db.STATE_DELETED)
                p += p_step
        else:
            p += 15.0

        # 65..90% -> fix up all episode statuses
        channels = load_channels()
        if len(channels):
            p_step = 25.0/len(channels)
            for channel in channels:
                status_callback(p, _('Migrating settings for %s') % channel.title)
                ChannelSettings.migrate_settings(channel)
                status_callback(p, _('Fixing episodes in %s') % channel.title)
                all_episodes = channel.get_all_episodes()
                if len(all_episodes):
                    p_step_2 = p_step/len(all_episodes)
                    for episode in all_episodes:
                        ### status_callback(p, _('Checking episode: %s') % episode.title)
                        if episode.state == db.STATE_DELETED and episode.file_exists():
                            episode.mark(state=db.STATE_DOWNLOADED, is_played=False)
                        # episode.fix_corrupted_state()
                        p += p_step_2
                else:
                    p += p_step
        else:
            p += 25.0

        # 90..95% -> import playback history
        playback_history = HistoryStore(os.path.join(self.gpodder_dir, 'playback-history.txt'))
        if len(playback_history):
            p_step = 5.0/len(playback_history)
            for url in playback_history:
                ### status_callback(p, _('Playback history: %s') % url)
                db.mark_episode(url, is_played=True)
                p += p_step
        else:
            p += 5.0
            
        # 95..100% -> import locked history
        locked_history = HistoryStore(os.path.join(self.gpodder_dir, 'lock-history.txt'))
        if len(locked_history):
            p_step = 5.0/len(locked_history)
            for url in locked_history:
                ### status_callback(p, _('Locked history: %s') % url)
                db.mark_episode(url, is_locked=True)
                p += p_step
        else:
            p += 5.0

    def migrate_channels_xml(self):
        """Migrate old (gPodder < 0.9.5) channels.xml to channels.opml

        This function does a one-time conversion of the old
        channels.xml file format to the new (supported by
        0.9.5, the default on 0.10.0) channels.opml format.
        """
        def channels_xml_iter(filename='channels.xml'):
            for e in xml.dom.minidom.parse(filename).getElementsByTagName('url'):
                yield ''.join(n.data for n in e.childNodes if n.nodeType==n.TEXT_NODE)
        
        def create_outline(doc, url):
            outline = doc.createElement('outline')
            for w in (('title', ''), ('text', ''), ('xmlUrl', url), ('type', 'rss')):
                outline.setAttribute(*w)
            return outline
        
        def export_opml(urls, filename='channels.opml'):
            doc = xml.dom.minidom.Document()
            opml = doc.createElement('opml')
            opml.setAttribute('version', '1.1')
            doc.appendChild(opml)
            body = doc.createElement('body')
            for url in urls:
                body.appendChild(create_outline(doc, url))
            opml.appendChild(body)
            open(filename,'w').write(doc.toxml(encoding='utf-8'))
        
        try:
            export_opml(channels_xml_iter(self.channel_xml_file), self.channel_opml_file)
            shutil.move(self.channel_xml_file, self.channel_xml_file+'.converted')
            log('Successfully converted channels.xml to channels.opml', sender=self)
        except:
            log('Cannot convert old channels.xml to channels.opml', traceback=True, sender=self)
        
    def get_device_name( self):
        if self.config.device_type == 'ipod':
            return _('iPod')
        elif self.config.device_type in ('filesystem', 'mtp'):
            return _('MP3 player')
        else:
            log( 'Warning: Called get_device_name() when no device was selected.', sender = self)
            return '(unknown device)'

    def find_partial_files(self):
        return glob.glob(os.path.join(self.downloaddir, '*', '*.partial'))

    def clean_up_downloads(self, delete_partial=False):
        # Clean up temporary files left behind by old gPodder versions
        temporary_files = glob.glob('%s/*/.tmp-*' % self.downloaddir)

        if delete_partial:
            temporary_files += glob.glob('%s/*/*.partial' % self.downloaddir)

        for tempfile in temporary_files:
            util.delete_file(tempfile)

        # Clean up empty download folders and abandoned download folders
        download_dirs = glob.glob(os.path.join(self.downloaddir, '*'))
        for ddir in download_dirs:
            if os.path.isdir(ddir) and not db.channel_foldername_exists(os.path.basename(ddir)):
                globr = glob.glob(os.path.join(ddir, '*'))
                if len(globr) == 0 or (len(globr) == 1 and globr[0].endswith('/cover')):
                    log('Stale download directory found: %s', os.path.basename(ddir), sender=self)
                    shutil.rmtree(ddir, ignore_errors=True)

    def get_download_dir( self):
        util.make_directory( self.config.download_dir)
        return self.config.download_dir

    def set_download_dir( self, new_downloaddir):
        if self.config.download_dir != new_downloaddir:
            log( 'Moving downloads from %s to %s', self.config.download_dir, new_downloaddir)
            try:
                # Fix error when moving over disk boundaries
                if os.path.isdir( new_downloaddir) and not os.listdir( new_downloaddir):
                    os.rmdir( new_downloaddir)

                shutil.move( self.config.download_dir, new_downloaddir)
            except NameError:
                log( 'Fixing a bug in shutil. See http://bugs.python.org/issue2549')
                errno = subprocess.call(["rm", "-rf", self.config.download_dir])
                if errno <> 0:
                    log( 'Error while deleting %s: rm returned error %i', self.config.download_dir, errno) 
                    return
            except Exception, exc:
                log( 'Error while moving %s to %s: %s',self.config.download_dir, new_downloaddir, exc)
                return

        self.config.download_dir = new_downloaddir

    downloaddir = property(fget=get_download_dir,fset=set_download_dir)
    
    def send_subscriptions(self):
        try:
            subprocess.Popen(['xdg-email', '--subject', _('My podcast subscriptions'),
                                           '--attach', self.channel_opml_file])
        except:
            return False
        
        return True

    def streaming_possible(self):
        return self.config.player and self.config.player != 'default'

    def playback_episode(self, episode):
        filename = episode.local_filename(create=False)

        if filename is None:
            filename = episode.url

        db.mark_episode(episode.url, is_played=True)

        file_type = episode.file_type()
        if file_type == 'video' and self.config.videoplayer and \
                self.config.videoplayer != 'default':
            player = self.config.videoplayer
        elif file_type == 'audio' and self.config.player and \
                self.config.player != 'default':
            player = self.config.player
        else:
            # System default open action for the file
            return (util.gui_open(filename), player)

        command_line = shlex.split(util.format_desktop_command(player, filename).encode('utf-8'))
        log( 'Command line: [ %s ]', ', '.join( [ '"%s"' % p for p in command_line ]), sender = self)
        try:
            subprocess.Popen( command_line)
        except:
            return ( False, command_line[0] )
        return ( True, command_line[0] )



class HistoryStore( types.ListType):
    """
    DEPRECATED - Only used for migration to SQLite
    """

    def __init__( self, filename):
        self.filename = filename
        try:
            self.read_from_file()
        except:
            log( 'Creating new history list.', sender = self)

    def read_from_file( self):
        for line in open( self.filename, 'r'):
            self.append( line.strip())

    def save_to_file( self):
        if len( self):
            fp = open( self.filename, 'w')
            for url in self:
                fp.write( url + "\n")
            fp.close()
            log( 'Wrote %d history entries.', len( self), sender = self)

    def add_item( self, data, autosave = True):
        affected = 0
        if data and type( data) is types.ListType:
            # Support passing a list of urls to this function
            for url in data:
                affected = affected + self.add_item( url, autosave = False)
        else:
            if data not in self:
                log( 'Adding: %s', data, sender = self)
                self.append( data)
                affected = affected + 1

        if affected and autosave:
            self.save_to_file()

        return affected

    def del_item( self, data, autosave = True):
        affected = 0
        if data and type( data) is types.ListType:
            # Support passing a list of urls to this function
            for url in data:
                affected = affected + self.del_item( url, autosave = False)
        else:
            if data in self:
                log( 'Removing: %s', data, sender = self)
                self.remove( data)
                affected = affected + 1

        if affected and autosave:
            self.save_to_file()

        return affected


class ChannelSettings(object):
    """
    DEPRECATED - Only used for migration to SQLite
    """
    SETTINGS_TO_MIGRATE = ('sync_to_devices', 'override_title', 'username', 'password')
    storage = None

    @classmethod
    def migrate_settings(cls, channel):
        url = channel.url
        settings = {}

        if cls.storage is None:
            if os.path.exists(gl.channel_settings_file):
                cls.storage = dumbshelve.open_shelve(gl.channel_settings_file)

        # We might have failed to open the shelve if we didn't have a settings
        # file in the first place (e.g., the user just deleted the database and
        # reimports everything from channels.opml).
        if cls.storage is not None:
            if isinstance(url, unicode):
                url = url.encode('utf-8')
            if cls.storage.has_key(url):
                settings = cls.storage[url]

            if settings:
                log('Migrating settings for %s', url)
            for key in cls.SETTINGS_TO_MIGRATE:
                if settings.has_key(key):
                    log('Migrating key %s', key)
                    setattr(channel, key, settings[key])


# Global, singleton gPodderLib object
gl = gPodderLib()


