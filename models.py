#!/usr/bin/env python3

from contextlib import contextmanager
import datetime

from peewee import *

#db = SqliteDatabase('work_log.db')

class BaseModel(Model):

    class Meta:
        database = db

class User(BaseModel):

    username = CharField(max_length=255)

class Entry(BaseModel):

    employee = ForeignKeyField(User)
    title = CharField(max_length=255)
    start_timestamp = DateTimeField(default=datetime.datetime.now)
    end_timestamp = DateTimeField()
    notes = TextField()


#@contextmanager
#def initialize(db_name, driver='sqlite', un='root', pw='root'):

#    if driver == 'sqlite':
#        db = SqliteDatabase(db_name) 
#    else:
#        db = MySQLDatabase(db_name, user=un, password=pw)

#    db.connect()

#    yield db

#    db.close()

    
    
