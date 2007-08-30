# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (C) 2005-2007 Thomas Perl <thp at perli.net>
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
import popen2
import os
import os.path

class FileConverter:
    percentage_match = re.compile('(\d+)%')

    def __init__( self, decoder_command):
        self.encoder_command = 'lame --nohist /dev/stdin "%s"'
        self.decoder_command = decoder_command

    def convert( self, input_filename, output_filename, callback = None):
        input_command = self.decoder_command % input_filename
        output_command = self.encoder_command % output_filename

        command = '%s | %s' % ( input_command, output_command )

        process = popen2.Popen4( command)
        stdout = process.fromchild
        s = stdout.read( 80)
        while s:
            if callback:
                for str in self.percentage_match.finditer( s):
                    callback( str.group( 1).strip())
            s = stdout.read( 80)

        return process.wait() == 0

class ConverterCollection:
    def __init__( self):
        self.dict = {}

    def add_converter( self, extension, command):
        self.dict[extension.lower()] = FileConverter( command)

    def has_converter( self, extension):
        return self.dict.has_key( extension.lower())

    def convert( self, input_filename, output_filename = None, callback = None):
        extension = os.path.splitext( input_filename)[1][1:]
        if extension.lower() not in self.dict:
            return None

        if not output_filename:
            output_filename = os.path.splitext( input_filename)[0]+'.mp3'
        
        if not self.dict[extension.lower()].convert( input_filename, output_filename, callback):
            return None

        return output_filename
        

converters = ConverterCollection()

# Add known converter applications
converters.add_converter( 'ogg', 'oggdec --quiet --output=/dev/stdout "%s"')

