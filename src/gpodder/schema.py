# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2016 Thomas Perl and the gPodder Team
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

# gpodder.schema - Database schema update and migration facility
# Thomas Perl <thp@gpodder.org>; 2011-02-01

from sqlite3 import dbapi2 as sqlite

import time
import shutil

import logging
logger = logging.getLogger(__name__)

EpisodeColumns = (
    'podcast_id',
    'title',
    'description',
    'url',
    'published',
    'guid',
    'link',
    'file_size',
    'mime_type',
    'state',
    'is_new',
    'archive',
    'download_filename',
    'total_time',
    'current_position',
    'current_position_updated',
    'last_playback',
    'payment_url',
)

PodcastColumns = (
    'title',
    'url',
    'link',
    'description',
    'cover_url',
    'auth_username',
    'auth_password',
    'http_last_modified',
    'http_etag',
    'auto_archive_episodes',
    'download_folder',
    'pause_subscription',
    'section',
    'payment_url',
    'download_strategy',
    'sync_to_mp3_player',
    'cover_thumb',
)

CURRENT_VERSION = 6


# SQL commands to upgrade old database versions to new ones
# Each item is a tuple (old_version, new_version, sql_commands) that should be
# applied to the database to migrate from old_version to new_version.
UPGRADE_SQL = [
        # Version 2: Section labels for the podcast list
        (1, 2, """
        ALTER TABLE podcast ADD COLUMN section TEXT NOT NULL DEFAULT ''
        """),

        # Version 3: Flattr integration (+ invalidate http_* fields to force
        # a feed update, so that payment URLs are parsed during the next check)
        (2, 3, """
        ALTER TABLE podcast ADD COLUMN payment_url TEXT NULL DEFAULT NULL
        ALTER TABLE episode ADD COLUMN payment_url TEXT NULL DEFAULT NULL
        UPDATE podcast SET http_last_modified=NULL, http_etag=NULL
        """),

        # Version 4: Per-podcast download strategy management
        (3, 4, """
        ALTER TABLE podcast ADD COLUMN download_strategy INTEGER NOT NULL DEFAULT 0
        """),

        # Version 5: Per-podcast MP3 player device synchronization option
        (4, 5, """
        ALTER TABLE podcast ADD COLUMN sync_to_mp3_player INTEGER NOT NULL DEFAULT 1
        """),

        # Version 6: Add thumbnail for cover art
        (5, 6, """
        ALTER TABLE podcast ADD COLUMN cover_thumb BLOB NULL DEFAULT NULL
        """),
]

def initialize_database(db):
    # Create table for podcasts
    db.execute("""
    CREATE TABLE podcast (
        id INTEGER PRIMARY KEY NOT NULL,
        title TEXT NOT NULL DEFAULT '',
        url TEXT NOT NULL DEFAULT '',
        link TEXT NOT NULL DEFAULT '',
        description TEXT NOT NULL DEFAULT '',
        cover_url TEXT NULL DEFAULT NULL,
        auth_username TEXT NULL DEFAULT NULL,
        auth_password TEXT NULL DEFAULT NULL,
        http_last_modified TEXT NULL DEFAULT NULL,
        http_etag TEXT NULL DEFAULT NULL,
        auto_archive_episodes INTEGER NOT NULL DEFAULT 0,
        download_folder TEXT NOT NULL DEFAULT '',
        pause_subscription INTEGER NOT NULL DEFAULT 0,
        section TEXT NOT NULL DEFAULT '',
        payment_url TEXT NULL DEFAULT NULL,
        download_strategy INTEGER NOT NULL DEFAULT 0,
        sync_to_mp3_player INTEGER NOT NULL DEFAULT 1,
        cover_thumb BLOB NULL DEFAULT NULL
    )
    """)

    INDEX_SQL = """
    CREATE UNIQUE INDEX idx_podcast_url ON podcast (url)
    CREATE UNIQUE INDEX idx_podcast_download_folder ON podcast (download_folder)
    """

    for sql in INDEX_SQL.strip().split('\n'):
        db.execute(sql)

    # Create table for episodes
    db.execute("""
    CREATE TABLE episode (
        id INTEGER PRIMARY KEY NOT NULL,
        podcast_id INTEGER NOT NULL,
        title TEXT NOT NULL DEFAULT '',
        description TEXT NOT NULL DEFAULT '',
        url TEXT NOT NULL,
        published INTEGER NOT NULL DEFAULT 0,
        guid TEXT NOT NULL,
        link TEXT NOT NULL DEFAULT '',
        file_size INTEGER NOT NULL DEFAULT 0,
        mime_type TEXT NOT NULL DEFAULT 'application/octet-stream',
        state INTEGER NOT NULL DEFAULT 0,
        is_new INTEGER NOT NULL DEFAULT 0,
        archive INTEGER NOT NULL DEFAULT 0,
        download_filename TEXT NULL DEFAULT NULL,
        total_time INTEGER NOT NULL DEFAULT 0,
        current_position INTEGER NOT NULL DEFAULT 0,
        current_position_updated INTEGER NOT NULL DEFAULT 0,
        last_playback INTEGER NOT NULL DEFAULT 0,
        payment_url TEXT NULL DEFAULT NULL
    )
    """)

    INDEX_SQL = """
    CREATE INDEX idx_episode_podcast_id ON episode (podcast_id)
    CREATE UNIQUE INDEX idx_episode_download_filename ON episode (podcast_id, download_filename)
    CREATE UNIQUE INDEX idx_episode_guid ON episode (podcast_id, guid)
    CREATE INDEX idx_episode_state ON episode (state)
    CREATE INDEX idx_episode_is_new ON episode (is_new)
    CREATE INDEX idx_episode_archive ON episode (archive)
    CREATE INDEX idx_episode_published ON episode (published)
    """

    for sql in INDEX_SQL.strip().split('\n'):
        db.execute(sql)

    # Create table for version info / metadata + insert initial data
    db.execute("""CREATE TABLE version (version integer)""")
    db.execute("INSERT INTO version (version) VALUES (%d)" % CURRENT_VERSION)
    db.commit()


def upgrade(db, filename):
    if not list(db.execute('PRAGMA table_info(version)')):
        initialize_database(db)
        return

    version = db.execute('SELECT version FROM version').fetchone()[0]
    if version == CURRENT_VERSION:
        return

    # We are trying an upgrade - save the current version of the DB
    backup = '%s_upgraded-v%d_%d' % (filename, int(version), int(time.time()))
    try:
        shutil.copy(filename, backup)
    except Exception, e:
        raise Exception('Cannot create DB backup before upgrade: ' + e)

    db.execute("DELETE FROM version")

    for old_version, new_version, upgrade in UPGRADE_SQL:
        if version == old_version:
            for sql in upgrade.strip().split('\n'):
                db.execute(sql)
            version = new_version

    assert version == CURRENT_VERSION

    db.execute("INSERT INTO version (version) VALUES (%d)" % version)
    db.commit()

    if version != CURRENT_VERSION:
        raise Exception('Database schema version unknown')


def convert_gpodder2_db(old_db, new_db):
    """Convert gPodder 2.x databases to the new format

    Both arguments should be SQLite3 connections to the
    corresponding databases.
    """

    old_db = sqlite.connect(old_db)
    new_db_filename = new_db
    new_db = sqlite.connect(new_db)
    upgrade(new_db, new_db_filename)

    # Copy data for podcasts
    old_cur = old_db.cursor()
    columns = [x[1] for x in old_cur.execute('PRAGMA table_info(channels)')]
    for row in old_cur.execute('SELECT * FROM channels'):
        row = dict(zip(columns, row))
        values = (
                row['id'],
                row['override_title'] or row['title'],
                row['url'],
                row['link'],
                row['description'],
                row['image'],
                row['username'] or None,
                row['password'] or None,
                row['last_modified'] or None,
                row['etag'] or None,
                row['channel_is_locked'],
                row['foldername'],
                not row['feed_update_enabled'],
                '',
                None,
                0,
                row['sync_to_devices'],
        )
        new_db.execute("""
        INSERT INTO podcast VALUES (%s)
        """ % ', '.join('?'*len(values)), values)
    old_cur.close()

    # Copy data for episodes
    old_cur = old_db.cursor()
    columns = [x[1] for x in old_cur.execute('PRAGMA table_info(episodes)')]
    for row in old_cur.execute('SELECT * FROM episodes'):
        row = dict(zip(columns, row))
        values = (
                row['id'],
                row['channel_id'],
                row['title'],
                row['description'],
                row['url'],
                row['pubDate'],
                row['guid'],
                row['link'],
                row['length'],
                row['mimetype'],
                row['state'],
                not row['played'],
                row['locked'],
                row['filename'],
                row['total_time'],
                row['current_position'],
                row['current_position_updated'],
                0,
                None,
        )
        new_db.execute("""
        INSERT INTO episode VALUES (%s)
        """ % ', '.join('?'*len(values)), values)
    old_cur.close()

    old_db.close()
    new_db.commit()
    new_db.close()

def check_data(db):
    # All episodes must be assigned to a podcast
    orphan_episodes = db.get('SELECT COUNT(id) FROM episode '
            'WHERE podcast_id NOT IN (SELECT id FROM podcast)')
    if orphan_episodes > 0:
        logger.error('Orphaned episodes found in database')

