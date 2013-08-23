# -*- coding: utf-8 -*-
#
# gpodder.compat.schema - Database schema update and migration facility
# Copyright (c) 2011-2013, Thomas Perl <m@thp.io>
# Copyright (c) 2012, Daniel Schaal <farbing@web.de>
# Copyright (c) 2012, Bernd Schlapsi <brot@gmx.info>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.
#


from sqlite3 import dbapi2 as sqlite

import time
import shutil

import logging
logger = logging.getLogger(__name__)

from gpodder import model

PodcastColumns = model.PodcastChannel.__schema__
EpisodeColumns = model.PodcastEpisode.__schema__

CURRENT_VERSION = 5


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
        """)
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
        sync_to_mp3_player INTEGER NOT NULL DEFAULT 1
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
    except Exception as e:
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
        row = dict(list(zip(columns, row)))
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
        row = dict(list(zip(columns, row)))
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

