# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
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
#  libconverter.py -- [any]-to-mp3 conversion library
#  thomas perl <thp@perli.net>   20070318
#
#


import re
import os
import os.path
import types
import subprocess

from gpodder import util
from gpodder.liblogger import log

class FileConverter:
    percentage_match = re.compile('(\d+)%')

    def __init__( self, decoder_command, decoder_arguments):
        self.encoder_command = 'lame --nohist /dev/stdin "%s"'
        self.decoder_command = ' '.join( ( decoder_command, decoder_arguments ))

    def convert( self, input_filename, output_filename, callback = None):
        input_command = self.decoder_command % input_filename
        output_command = self.encoder_command % output_filename

        command = '%s | %s' % ( input_command, output_command )

        process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        stdout = process.stdout
        s = stdout.read(80)
        while s:
            if callback:
                for result in self.percentage_match.finditer(s):
                    try:
                        callback(result.group(1).strip())
                    except:
                        log('Cannot call callback for status percentage.', sender=self)
            s = stdout.read(80)

        return process.wait() == 0

class ConverterCollection( types.DictType):
    def add_converter( self, extension, command, arguments):
        if util.find_command(command) is not None:
            log( 'Found "%s", will try to convert ".%s" files.' % ( command, extension ), sender = self)
            self[extension.lower()] = FileConverter( command, arguments)
        else:
            log( 'Could not find "%s", ".%s" files cannot be converted.' % ( command, extension ), sender = self)

    def has_converter(self, extension):
        if util.find_command('lame') is not None:
            extension = extension.lower()
            if len(extension) == 0:
                log('Cannot find a converter without extension.', sender=self)
                return False
            if extension[0] == '.':
                extension = extension[1:]
            return self.has_key(extension)
        else:
            log('Please install the "lame" package to convert files.', sender=self)
            return False

    def convert( self, input_filename, output_filename = None, callback = None):
        extension = os.path.splitext( input_filename)[1][1:]
        if extension.lower() not in self:
            return None

        if not output_filename:
            output_filename = os.path.splitext( input_filename)[0]+'.mp3'
        
        if not self[extension.lower()].convert( input_filename, output_filename, callback):
            return None

        return output_filename
        

converters = ConverterCollection()

# Add known converter applications
converters.add_converter( 'ogg', 'oggdec', '--quiet --output=/dev/stdout "%s"')

