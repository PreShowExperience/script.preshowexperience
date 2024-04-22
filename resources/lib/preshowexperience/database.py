import time
import datetime
import xbmc
import xbmcgui
import xbmcvfs
import os
import shutil

try:
    datetime.datetime.strptime('0', '%H')
except TypeError:
    # Fix for datetime issues with XBMC/Kodi
    class new_datetime(datetime.datetime):
        @classmethod
        def strptime(cls, dstring, dformat):
            return datetime.datetime(*(time.strptime(dstring, dformat)[0:6]))

    # To fix an issue with threading ad strptime
    import _strptime # pylint: disable=W0611

    datetime.datetime = new_datetime

from peewee import *
from peewee import peewee
from . import util
from resources.lib import kodiutil
from . import content

DATABASE_VERSION = 7

fn = peewee.fn
DB = None
DBVersion = None
Song = None
Trivia = None
Slideshow = None                
AudioFormatBumpers = None
RatingsBumpers = None
VideoBumpers = None
RatingSystem = None
Rating = None
Trailers = None

def session(func):
    def inner(*args, **kwargs):
        try:
            DB.connect(reuse_if_open=True)
            with DB.atomic():
                return func(*args, **kwargs)
        finally:
            DB.close()
    return inner

def connect():
    DB.connect(reuse_if_open=True)

def close():
    DB.close()

def dummyCallback(*args, **kwargs):
    pass

def migrateDB(DB, version):
    util.LOG('Migrating database from version {0} to {1}'.format(version, DATABASE_VERSION))
    from peewee.playhouse import migrate
    migrator = migrate.SqliteMigrator(DB)

    if 1 < version < 7:    
        util.LOG('Updating Trivia accessed field')
        migrate.migrate(
            migrator.add_column('Trivia', 'accessed_temp', peewee.DateTimeField(default=datetime.date(2020, 1, 1))),
            migrator.drop_column('Trivia', 'accessed'),
            migrator.rename_column('Trivia', 'accessed_temp', 'accessed'),
            migrator.drop_column('AudioFormatBumpers', 'is3d'),
            migrator.drop_column('Trailers', 'is3D'),
            migrator.drop_column('RatingsBumpers', 'is3d')            
        )
        util.LOG('Removing watched.db & Trivia files')
        dbDir = util.STORAGE_PATH
        watched_db_path = util.pathJoin(dbDir, 'watched.db')
        if util.vfs.exists(watched_db_path):
            xbmcvfs.delete(watched_db_path)
        tmdb_path = util.pathJoin(dbDir, 'tmdb.last')
        if util.vfs.exists(tmdb_path):
            xbmcvfs.delete(tmdb_path)
        imdb_path = util.pathJoin(dbDir, 'imdb.last')
        if util.vfs.exists(imdb_path):
            xbmcvfs.delete(imdb_path)
        xbmcgui.Dialog().ok('PreShow Experience Update', 'PreShow has been updated and requires that your trailer content is updated.')
    return True

def checkDBVersion(DB):
    vm = DBVersion.get_or_create(id=1, defaults={'version': 0})[0]
    if vm.version < DATABASE_VERSION:
        if migrateDB(DB, vm.version):
            vm.update(version=DATABASE_VERSION).execute()

def initialize(path=None, callback=None):
    callback = callback or dummyCallback

    callback(None, 'Creating/updating database...')

    global DB
    global DBVersion
    global Song
    global Trivia
    global Slideshow                    
    global AudioFormatBumpers
    global RatingsBumpers
    global VideoBumpers
    global RatingSystem
    global Rating
    global Trailers

    ###########################################################################################
    # Version
    ###########################################################################################
    dbDir = path or util.STORAGE_PATH
    if not util.vfs.exists(dbDir):
        util.vfs.mkdirs(dbDir)

    dbPath = util.pathJoin(dbDir, 'content.db')
    dbExists = util.vfs.exists(dbPath)

    DB = peewee.SqliteDatabase(dbPath)

    DB.connect()

    class DBVersion(peewee.Model):
        version = peewee.IntegerField(default=0)

        class Meta:
            database = DB

    DBVersion.create_table(fail_silently=True)

    if dbExists:  # Only check version if we had a DB, otherwise we're creating it fresh
        checkDBVersion(DB)

    ###########################################################################################
    # Content
    ###########################################################################################
    class ContentBase(peewee.Model):
        name = peewee.CharField()
        accessed = peewee.DateTimeField(default=datetime.date(2020, 1, 1))
        pack = peewee.TextField(null=True)

        class Meta:
            database = DB

    callback(' - Music')

    class Song(ContentBase):
        rating = peewee.CharField(null=True)
        genre = peewee.CharField(null=True)
        year = peewee.CharField(null=True)

        path = peewee.CharField(unique=True)
        duration = peewee.FloatField(default=0)

    Song.create_table(fail_silently=True)

    callback(' - Tivia')

    class Trivia(ContentBase):
        type = peewee.CharField()

        TID = peewee.CharField(unique=True)

        rating = peewee.CharField(null=True)
        genre = peewee.CharField(null=True)
        year = peewee.CharField(null=True)
        duration = peewee.FloatField(default=0)

        questionPath = peewee.CharField(unique=True, null=True)
        cluePath0 = peewee.CharField(unique=True, null=True)
        cluePath1 = peewee.CharField(unique=True, null=True)
        cluePath2 = peewee.CharField(unique=True, null=True)
        cluePath3 = peewee.CharField(unique=True, null=True)
        cluePath4 = peewee.CharField(unique=True, null=True)
        cluePath5 = peewee.CharField(unique=True, null=True)
        cluePath6 = peewee.CharField(unique=True, null=True)
        cluePath7 = peewee.CharField(unique=True, null=True)
        cluePath8 = peewee.CharField(unique=True, null=True)
        cluePath9 = peewee.CharField(unique=True, null=True)
        answerPath = peewee.CharField(unique=True, null=True)

    Trivia.create_table(fail_silently=True)

    callback(' - Slideshow')
    
    class Slideshow(ContentBase):
        type = peewee.CharField()
        TID = peewee.CharField(unique=True)
        duration = peewee.FloatField(default=0)
        slidePath = peewee.CharField(unique=True, null=True)
        watched = peewee.IntegerField(default=0)

    Slideshow.create_table(fail_silently=True)
    
    callback(' - AudioFormatBumpers')
                              
    class BumperBase(ContentBase):
        isImage = peewee.BooleanField(default=False)
        path = peewee.CharField(unique=True)

    class AudioFormatBumpers(BumperBase):
        format = peewee.CharField()

    AudioFormatBumpers.create_table(fail_silently=True)

    callback(' - RatingsBumpers')

    class RatingsBumpers(BumperBase):
        system = peewee.CharField(default='MPAA')
        style = peewee.CharField(default='Classic')

    RatingsBumpers.create_table(fail_silently=True)

    callback(' - VideoBumpers')

    class VideoBumpers(BumperBase):
        type = peewee.CharField()

        rating = peewee.CharField(null=True)
        genre = peewee.CharField(null=True)
        year = peewee.CharField(null=True)

    VideoBumpers.create_table(fail_silently=True)

    ###########################################################################################
    # Ratings
    ###########################################################################################
    class RatingSystem(peewee.Model):
        name = peewee.CharField()
        context = peewee.CharField(null=True)
        regEx = peewee.CharField()
        regions = peewee.CharField(null=True)

        class Meta:
            database = DB

    RatingSystem.create_table(fail_silently=True)

    class Rating(peewee.Model):
        name = peewee.CharField(unique=True)
        internal = peewee.CharField()
        value = peewee.IntegerField(default=0)
        system = peewee.CharField()

        class Meta:
            database = DB

    Rating.create_table(fail_silently=True)

    ###########################################################################################
    # Trailers Database
    ###########################################################################################
    class TrailerBase(peewee.Model):
        WID = peewee.CharField(unique=True)
        watched = peewee.BooleanField(default=False)
        date = peewee.DateTimeField(default=datetime.date(2020, 1, 1))

        class Meta:
            database = DB

    class Trailers(TrailerBase):
        source = peewee.CharField()
        rating = peewee.CharField(null=True)
        genres = peewee.CharField(null=True)
        title = peewee.CharField()
        release = peewee.DateTimeField(default=datetime.date(2020, 1, 1))
        url = peewee.CharField(null=True)
        userAgent = peewee.CharField(null=True)
        thumb = peewee.CharField(null=True)
        broken = peewee.BooleanField(default=False)
        verified = peewee.BooleanField(default=True)

    Trailers.create_table(fail_silently=True)

    callback(' - Trailers')
    callback(None, 'Database created')

    DB.close()
