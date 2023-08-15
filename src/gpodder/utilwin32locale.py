# -*- coding: utf-8 -*-
#
# Copyright © 2007-2010 Dieter Verfaillie <dieterv@optionexplicit.be>
#
# This file is part of elib.intl.
#
# elib.intl is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# elib.intl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with elib.intl. If not, see <http://www.gnu.org/licenses/>.


'''
This code is adapted from the elib.intl module available on GitHub at
https://github.com/dieterv/elib.intl, commit 49d5797 on 1 Sep 2017.

It has been stripped down to the necessary code for UI localization
using Gtk.Builder in gPodder on Windows (msys2) and adapted to python 3.

The elib.intl module provides enhanced internationalization (I18N) services for
your Python modules and applications.

This module adds the following on Microsoft Windows systems:

 - automatic detection of the current screen language (not necessarily the same
   as the installation language) provided by MUI packs,
 - makes sure internationalized C libraries which internally invoke gettext() or
   dcgettext() can properly locate their message catalogs. This fixes a known
   limitation in gettext's Windows support when using eg. gtk.builder or gtk.glade.

See http://www.gnu.org/software/gettext/FAQ.html#windows_setenv for more
information.
'''


__version__ = '0.0.3'
__docformat__ = 'restructuredtext'


import gettext
import locale
import os
import sys
from logging import getLogger

logger = getLogger(__name__)


def _localefromlcid(lcid):
    '''
    :param lcid: Microsoft Windows LCID
    :returns: name of the supported gPodder locale or ISO 639-1 language code for a given lcid. If there is no
              ISO 639-1 language code assigned to the language specified by lcid,
              the ISO 639-2 language code is returned. If the language specified
              by lcid is unknown in the ISO 639-x database, None is returned.

    More information can be found on the following websites:
        - List of ISO 639-1 and ISO 639-2 language codes: http://www.loc.gov/standards/iso639-2/
        - List of language identifiers: https://msdn.microsoft.com/library/windows/desktop/dd318693(v=vs.85).aspx
    '''
    mapping = {1078: 'af',  # Afrikaans - South Africa
               1052: 'sq',  # Albanian - Albania
               1118: 'am',  # Amharic - Ethiopia
               1025: 'ar',  # Arabic - Saudi Arabia
               5121: 'ar',  # Arabic - Algeria
               15361: 'ar',  # Arabic - Bahrain
               3073: 'ar',  # Arabic - Egypt
               2049: 'ar',  # Arabic - Iraq
               11265: 'ar',  # Arabic - Jordan
               13313: 'ar',  # Arabic - Kuwait
               12289: 'ar',  # Arabic - Lebanon
               4097: 'ar',  # Arabic - Libya
               6145: 'ar',  # Arabic - Morocco
               8193: 'ar',  # Arabic - Oman
               16385: 'ar',  # Arabic - Qatar
               10241: 'ar',  # Arabic - Syria
               7169: 'ar',  # Arabic - Tunisia
               14337: 'ar',  # Arabic - U.A.E.
               9217: 'ar',  # Arabic - Yemen
               1067: 'hy',  # Armenian - Armenia
               1101: 'as',  # Assamese
               2092: 'az',  # Azeri (Cyrillic)
               1068: 'az',  # Azeri (Latin)
               0x042D: 'eu',  # Basque
               1059: 'be',  # Belarusian
               1093: 'bn',  # Bengali (India)
               2117: 'bn',  # Bengali (Bangladesh)
               5146: 'bs',  # Bosnian (Bosnia/Herzegovina)
               1026: 'bg',  # Bulgarian
               1109: 'my',  # Burmese
               0x0403: 'ca',  # Catalan
               1116: 'chr',  # Cherokee - United States
               # we have only one zh_CN.po translation. Applying to all.
               2052: 'zh_CN',  # Chinese - People's Republic of China
               4100: 'zh_CN',  # Chinese - Singapore
               1028: 'zh_CN',  # Chinese - Taiwan
               3076: 'zh_CN',  # Chinese - Hong Kong SAR
               5124: 'zh_CN',  # Chinese - Macao SAR
               1050: 'hr',  # Croatian
               4122: 'hr',  # Croatian (Bosnia/Herzegovina)
               # we have cs and cs_CZ translations. cs_CZ seems more up to date
               0x0405: 'cs_CZ',  # Czech
               0x0406: 'da',  # Danish
               1125: 'dv',  # Divehi
               1043: 'nl',  # Dutch - Netherlands
               0x0813: 'nl',  # Dutch - Belgium
               1126: 'bin',  # Edo
               1033: 'en',  # English - United States
               2057: 'en',  # English - United Kingdom
               3081: 'en',  # English - Australia
               10249: 'en',  # English - Belize
               4105: 'en',  # English - Canada
               9225: 'en',  # English - Caribbean
               15369: 'en',  # English - Hong Kong SAR
               16393: 'en',  # English - India
               14345: 'en',  # English - Indonesia
               6153: 'en',  # English - Ireland
               8201: 'en',  # English - Jamaica
               17417: 'en',  # English - Malaysia
               5129: 'en',  # English - New Zealand
               13321: 'en',  # English - Philippines
               18441: 'en',  # English - Singapore
               7177: 'en',  # English - South Africa
               11273: 'en',  # English - Trinidad
               12297: 'en',  # English - Zimbabwe
               1061: 'et',  # Estonian
               1080: 'fo',  # Faroese
               0x0429: 'fa_IR',  # Persian - Iran
               1124: 'fil',  # Filipino
               0x040B: 'fi',  # Finnish
               0x040C: 'fr',  # French - France
               2060: 'fr',  # French - Belgium
               11276: 'fr',  # French - Cameroon
               3084: 'fr',  # French - Canada
               9228: 'fr',  # French - Democratic Rep. of Congo
               12300: 'fr',  # French - Cote d'Ivoire
               15372: 'fr',  # French - Haiti
               5132: 'fr',  # French - Luxembourg
               13324: 'fr',  # French - Mali
               6156: 'fr',  # French - Monaco
               14348: 'fr',  # French - Morocco
               58380: 'fr',  # French - North Africa
               8204: 'fr',  # French - Reunion
               10252: 'fr',  # French - Senegal
               4108: 'fr',  # French - Switzerland
               7180: 'fr',  # French - West Indies
               1122: 'fy',  # Frisian - Netherlands
               1127: None,  # TODO: Fulfulde - Nigeria
               1071: 'mk',  # FYRO Macedonian
               2108: 'ga',  # Gaelic (Ireland)
               1084: 'gd',  # Gaelic (Scotland)
               0x0456: 'gl',  # Galician
               1079: 'ka',  # Georgian
               0x0407: 'de',  # German - Germany
               3079: 'de',  # German - Austria
               5127: 'de',  # German - Liechtenstein
               4103: 'de',  # German - Luxembourg
               2055: 'de',  # German - Switzerland
               0x0408: 'el',  # Greek
               1140: 'gn',  # Guarani - Paraguay
               1095: 'gu',  # Gujarati
               1128: 'ha',  # Hausa - Nigeria
               1141: 'haw',  # Hawaiian - United States
               0x040D: 'he',  # Hebrew
               1081: 'hi',  # Hindi
               0x040E: 'hu',  # Hungarian
               1129: None,  # TODO: Ibibio - Nigeria
               1039: 'is',  # Icelandic
               1136: 'ig',  # Igbo - Nigeria
               0x0421: 'id_ID',  # Indonesian
               1117: 'iu',  # Inuktitut
               0x0410: 'it',  # Italian - Italy
               2064: 'it',  # Italian - Switzerland
               1041: 'ja',  # Japanese
               1099: 'kn',  # Kannada
               1137: 'kr',  # Kanuri - Nigeria
               2144: 'ks',  # Kashmiri
               1120: 'ks',  # Kashmiri (Arabic)
               0x043F: 'kk',  # Kazakh
               1107: 'km',  # Khmer
               1111: 'kok',  # Konkani
               0x0412: 'ko_KR',  # Korean
               1088: 'ky',  # Kyrgyz (Cyrillic)
               1108: 'lo',  # Lao
               1142: 'la',  # Latin
               1062: 'lv',  # Latvian
               1063: 'lt',  # Lithuanian
               1086: 'ms',  # Malay - Malaysia
               2110: 'ms',  # Malay - Brunei Darussalam
               1100: 'ml',  # Malayalam
               1082: 'mt',  # Maltese
               1112: 'mni',  # Manipuri
               1153: 'mi',  # Maori - New Zealand
               1102: 'mr',  # Marathi
               1104: 'mn',  # Mongolian (Cyrillic)
               2128: 'mn',  # Mongolian (Mongolian)
               1121: 'ne',  # Nepali
               2145: 'ne',  # Nepali - India
               0x0414: 'nb',  # Norwegian (Bokmￃﾥl)
               0x0814: 'nn',  # Norwegian (Nynorsk)
               1096: 'or',  # Oriya
               1138: 'om',  # Oromo
               1145: 'pap',  # Papiamentu
               1123: 'ps',  # Pashto
               0x0415: 'pl',  # Polish
               0x0416: 'pt_BR',  # Portuguese - Brazil
               0x0816: 'pt',  # Portuguese - Portugal
               1094: 'pa',  # Punjabi
               2118: 'pa',  # Punjabi (Pakistan)
               1131: 'qu',  # Quecha - Bolivia
               2155: 'qu',  # Quecha - Ecuador
               3179: 'qu',  # Quecha - Peru
               1047: 'rm',  # Rhaeto-Romanic
               0x0418: 'ro',  # Romanian
               2072: 'ro',  # Romanian - Moldava
               0x0419: 'ru',  # Russian
               2073: 'ru',  # Russian - Moldava
               1083: 'se',  # Sami (Lappish)
               1103: 'sa',  # Sanskrit
               1132: 'nso',  # Sepedi
               3098: 'sr',  # Serbian (Cyrillic)
               2074: 'sr',  # Serbian (Latin)
               1113: 'sd',  # Sindhi - India
               2137: 'sd',  # Sindhi - Pakistan
               1115: 'si',  # Sinhalese - Sri Lanka
               1051: 'sk',  # Slovak
               1060: 'sl',  # Slovenian
               1143: 'so',  # Somali
               1070: 'wen',  # Sorbian
               0x0C0A: 'es',  # Spanish - Spain (Modern Sort)
               0x040A: 'es',  # Spanish - Spain (Traditional Sort)
               11274: 'es',  # Spanish - Argentina
               16394: 'es',  # Spanish - Bolivia
               13322: 'es',  # Spanish - Chile
               9226: 'es',  # Spanish - Colombia
               5130: 'es',  # Spanish - Costa Rica
               7178: 'es',  # Spanish - Dominican Republic
               12298: 'es',  # Spanish - Ecuador
               17418: 'es',  # Spanish - El Salvador
               4106: 'es',  # Spanish - Guatemala
               18442: 'es',  # Spanish - Honduras
               58378: 'es',  # Spanish - Latin America
               0x080A: 'es_MX',  # Spanish - Mexico
               19466: 'es',  # Spanish - Nicaragua
               6154: 'es',  # Spanish - Panama
               15370: 'es',  # Spanish - Paraguay
               10250: 'es',  # Spanish - Peru
               20490: 'es',  # Spanish - Puerto Rico
               21514: 'es',  # Spanish - United States
               14346: 'es',  # Spanish - Uruguay
               8202: 'es',  # Spanish - Venezuela
               1072: None,  # TODO: Sutu
               1089: 'sw',  # Swahili
               0x041D: 'sv',  # Swedish
               2077: 'sv',  # Swedish - Finland
               1114: 'syr',  # Syriac
               1064: 'tg',  # Tajik
               1119: None,  # TODO: Tamazight (Arabic)
               2143: None,  # TODO: Tamazight (Latin)
               1097: 'ta',  # Tamil
               1092: 'tt',  # Tatar
               1098: 'te',  # Telugu
               1054: 'th',  # Thai
               2129: 'bo',  # Tibetan - Bhutan
               1105: 'bo',  # Tibetan - People's Republic of China
               2163: 'ti',  # Tigrigna - Eritrea
               1139: 'ti',  # Tigrigna - Ethiopia
               1073: 'ts',  # Tsonga
               1074: 'tn',  # Tswana
               # we have tr and tr_TR translations. tr seems more complete
               0x041F: 'tr',  # Turkish
               1090: 'tk',  # Turkmen
               1152: 'ug',  # Uighur - China
               0x0422: 'uk',  # Ukrainian
               1056: 'ur',  # Urdu
               2080: 'ur',  # Urdu - India
               2115: 'uz',  # Uzbek (Cyrillic)
               1091: 'uz',  # Uzbek (Latin)
               1075: 've',  # Venda
               1066: 'vi',  # Vietnamese
               1106: 'cy',  # Welsh
               1076: 'xh',  # Xhosa
               1144: 'ii',  # Yi
               1085: 'yi',  # Yiddish
               1130: 'yo',  # Yoruba
               1077: 'zu'}  # Zulu

    return mapping[lcid]


def _getscreenlanguage():
    '''
    :returns: the locale for this session.

    If the LANGUAGE environment variable is set, it's value overrides the
    screen language detection. Otherwise the screen language is determined by
    the currently selected Microsoft Windows MUI language pack or the Microsoft
    Windows installation language.

    Works on Microsoft Windows 2000 and up.
    '''
    # Start with nothing
    lang = None

    # Check the LANGUAGE environment variable
    lang = os.getenv('LANGUAGE')

    if lang is None:
        # Start with nothing
        lcid = None

        try:
            from ctypes import windll
            lcid = windll.kernel32.GetUserDefaultUILanguage()
        except:
            logger.warning('Failed to get current screen language with \'GetUserDefaultUILanguage\'')
        finally:
            if lcid is None:
                lang = 'C'
            else:
                lang = _localefromlcid(lcid)

            logger.info('Windows screen language is \'%s\' (lcid %s)', lang, lcid)

    return lang


def install(domain, localedir):
    '''
    :param domain: translation domain
    :param localedir: locale directory
    '''
    # prep locale system
    locale.setlocale(locale.LC_ALL, '')

    # on windows systems, set the LANGUAGE environment variable
    if sys.platform == 'win32' or sys.platform == 'nt':
        os.environ['LANGUAGE'] = _getscreenlanguage()

    # initialize Python's gettext interface
    gettext.bindtextdomain(domain, localedir)

    # on windows systems, initialize libintl
    if sys.platform == 'win32' or sys.platform == 'nt':
        from ctypes import cdll
        libintl = cdll.LoadLibrary('libintl-8.dll')
        libintl.bindtextdomain(domain.encode('mbcs'), localedir.encode('mbcs'))

        del libintl
