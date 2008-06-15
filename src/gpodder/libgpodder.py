# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2008 Thomas Perl and the gPodder Team
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

import os
import os.path
import glob
import types
import subprocess
import sys

from liblogger import log

import shlex

if gpodder.interface == gpodder.MAEMO:
    import osso

class gPodderLib(object):
    def __init__( self):
        log('Creating gPodderLib()', sender=self)
        if gpodder.interface == gpodder.MAEMO:
            gpodder_dir = '/media/mmc2/gpodder/'
            self.osso_c = osso.Context('gpodder_osso_sender', '1.0', False)
        else:
            gpodder_dir = os.path.expanduser('~/.config/gpodder/')
        util.make_directory( gpodder_dir)

        self.tempdir = gpodder_dir
        self.feed_cache_file = os.path.join(gpodder_dir, 'feedcache.pickle.db')
        self.channel_settings_file = os.path.join(gpodder_dir, 'channelsettings.pickle.db')
        self.episode_metainfo_file = os.path.join(gpodder_dir, 'episodemetainfo.pickle.db')

        self.channel_opml_file = os.path.join(gpodder_dir, 'channels.opml')
        self.channel_xml_file = os.path.join(gpodder_dir, 'channels.xml')

        if os.path.exists(self.channel_xml_file) and not os.path.exists(self.channel_opml_file):
            log('Trying to migrate channel list (channels.xml => channels.opml)', sender=self)
            self.migrate_channels_xml()

        self.config = config.Config( os.path.join( gpodder_dir, 'gpodder.conf'))
        util.make_directory(self.config.bittorrent_dir)

        # We need to make a seamless upgrade, so by default the video player is not specified
        # so the first time this application is run it will detect this and set it to the same 
        # as the audio player.  This keeps gPodder functionality identical to that prior to the 
        # upgrade.   The user can then set a specific video player if they so wish.	
        if self.config.videoplayer == 'unspecified':
            self.config.videoplayer = self.config.player	

        self.__download_history = HistoryStore( os.path.join( gpodder_dir, 'download-history.txt'))
        self.__playback_history = HistoryStore( os.path.join( gpodder_dir, 'playback-history.txt'))
        self.__locked_history = HistoryStore( os.path.join( gpodder_dir, 'lock-history.txt'))

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
        elif self.config.device_type == 'filesystem':
            return _('MP3 player')
        else:
            log( 'Warning: Called get_device_name() when no device was selected.', sender = self)
            return '(unknown device)'

    def format_filesize(self, bytesize, digits=2):
        return util.format_filesize(bytesize, self.config.use_si_units, digits)

    def clean_up_downloads( self, delete_partial = False):
        # Clean up temporary files left behind by old gPodder versions
        if delete_partial:
            temporary_files = glob.glob( '%s/*/.tmp-*' % ( self.downloaddir, ))
            for tempfile in temporary_files:
                util.delete_file( tempfile)

        # Clean up empty download folders
        download_dirs = glob.glob( '%s/*' % ( self.downloaddir, ))
        for ddir in download_dirs:
            if os.path.isdir( ddir):
                globr = glob.glob( '%s/*' % ( ddir, ))
                if not globr and ddir != self.config.bittorrent_dir:
                    log( 'Stale download directory found: %s', os.path.basename( ddir))
                    try:
                        os.rmdir( ddir)
                        log( 'Successfully removed %s.', ddir)
                    except:
                        log( 'Could not remove %s.', ddir)

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
            except:
                log( 'Error while moving %s to %s.', self.config.download_dir, new_downloaddir)
                return

        self.config.download_dir = new_downloaddir

    downloaddir = property(fget=get_download_dir,fset=set_download_dir)

    def history_mark_downloaded( self, url, add_item = True):
        if add_item:
            self.__download_history.add_item( url)
        else:
            self.__download_history.del_item( url)

    def history_mark_played( self, url, add_item = True):
        if add_item:
            self.__playback_history.add_item( url)
        else:
            self.__playback_history.del_item( url)

    def history_mark_locked( self, url, add_item = True):
        if add_item:
            self.__locked_history.add_item( url)
        else:
            self.__locked_history.del_item( url)

    def history_is_downloaded( self, url):
        return (url in self.__download_history)

    def history_is_played( self, url):
        return (url in self.__playback_history)

    def history_is_locked( self, url):
        return (url in self.__locked_history)
    
    def send_subscriptions(self):
        try:
            subprocess.Popen(['xdg-email', '--subject', _('My podcast subscriptions'),
                                           '--attach', self.channel_opml_file])
        except:
            return False
        
        return True

    def playback_episode( self, channel, episode):
        self.history_mark_played( episode.url)
        filename = episode.local_filename()

        if gpodder.interface == gpodder.MAEMO and not self.config.maemo_allow_custom_player:
            # Use the built-in Nokia Mediaplayer here
            filename = filename.encode('utf-8')
            osso_rpc = osso.Rpc(self.osso_c)
            service = 'com.nokia.mediaplayer'
            path = '/com/nokia/mediaplayer'
            osso_rpc.rpc_run(service, path, service, 'mime_open', ('file://'+filename,))
            return (True, service)

        # Determine the file type and set the player accordingly.  
        file_type = util.file_type_by_extension(util.file_extension_from_url(episode.url))

        if file_type == 'video':
            player = self.config.videoplayer
        elif file_type == 'audio':
            player = self.config.player
        else:
            log('Non-audio or video file type, using xdg-open for %s', filename, sender=self)
            player = 'xdg-open'
 
        command_line = shlex.split(util.format_desktop_command(player, filename).encode('utf-8'))
        log( 'Command line: [ %s ]', ', '.join( [ '"%s"' % p for p in command_line ]), sender = self)
        try:
            subprocess.Popen( command_line)
        except:
            return ( False, command_line[0] )
        return ( True, command_line[0] )

    def invoke_torrent( self, url, torrent_filename, target_filename):
        self.history_mark_played( url)

        if self.config.use_gnome_bittorrent:
            if util.find_command('gnome-btdownload') is None:
                log( 'Cannot find "gnome-btdownload". Please install gnome-bittorrent.', sender = self)
                return False

            command = 'gnome-btdownload "%s" --saveas "%s"' % ( torrent_filename, os.path.join( self.config.bittorrent_dir, target_filename))
            log( command, sender = self)
            os.system( '%s &' % command)
            return True
        else:
            # Simply copy the .torrent with a suitable name
            try:
                target_filename = os.path.join( self.config.bittorrent_dir, os.path.splitext( target_filename)[0] + '.torrent')
                shutil.copyfile( torrent_filename, target_filename)
                return True
            except:
                log( 'Torrent copy failed: %s => %s.', torrent_filename, target_filename)

        return False

    def ext_command_thread(self, notification, command_line):
        """
        This is the function that will be called in a separate
        thread that will call an external command (specified by
        command_line). In case of problem (i.e. the command has
        not been found or there has been another error), we will
        call the notification function with two arguments - the
        first being the error message and the second being the
        title to be used for the error message.
        """
 
        log("(ExtCommandThread) Excuting command Line [%s]", command_line)
    
        p = subprocess.Popen(command_line, shell=True, stdout=sys.stdout, stderr=sys.stderr)
        result = p.wait()
 
        if result == 127:
            title = _('User command not found')
            message = _('The user command [%s] was not found.\nPlease check your user command settings in the preferences dialog.' % command_line)
            notification(message, title)
        elif result == 126:
            title = _('User command permission denied')
            message = _('Permission denied when trying to execute user command [%s].\nPlease check that you have permissions to execute this command.' % command_line)
            notification(message, title)
        elif result > 0 :
            title = _('User command returned an error')
            message = _('The user command [%s] returned an error code of [%d]' % (command_line,result))
            notification(message, title)

        log("(ExtCommandThread) Finished command line [%s] result [%d]",command_line,result)


class HistoryStore( types.ListType):
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


# Global, singleton gPodderLib object
gl = gPodderLib()

