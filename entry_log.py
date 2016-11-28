#!/usr/bin/env python3

"""TODO:

1) Split distinct classes/refactor for more efficient code reuse
2) Create Test suite for coverage
"""

from collections import OrderedDict
import datetime

import inspect
import os
import sys

from peewee import *

DATABASE = 'work_log.db'
DATE_FMT = '%d/%m/%Y'
ERR = ''

db = SqliteDatabase(DATABASE)

class BaseModel(Model):

    class Meta:
        database = db

class User(BaseModel):

    username = CharField(max_length=255, unique=True, primary_key=True)

    class Meta:

        order_by = ('username',)

class Entry(BaseModel):

    employee = ForeignKeyField(User)
    title = CharField(max_length=255, default='(Your entry title)')
    _date = DateTimeField(default=datetime.date.today)
    duration = IntegerField(default=0)
    notes = TextField(default='(Your notes here)')

    @property
    def date(self):
        return self._date
    
    @date.setter
    def date(self, date_str='today'):

        today = datetime.date.today()

        if not date_str or date_str == 'today':

            self._date = today

        else:
            if '-' in date_str:
                raise ValueError("Your date format must be [mm/dd/YYYY].")

            val_list = reversed([int(val) for val in date_str.split('/')])

            self._date = datetime.date(*val_list)

def initialize():
    db.connect()
    db.create_tables([Entry,User], safe=True)

def menu_loop(menu, err):

    print(DATABASE)

    choice = None

    bck_msg = "Enter 'q' to quit"

    while choice not in ('q', 'x'):
        clear()

        if err:
            print('*** ERROR: {} ***'.format(err))

        if inspect.stack()[1][3] == 'search_entries':
            bck_msg = "Enter 'X' to exit to main menu."

        for key,val in menu.items():
            print("{}) {}".format(key, val.__doc__))
        choice = input("Action ({}): ".format(bck_msg)).lower().strip()
        
        if choice in menu:
            clear()
            menu[choice](err)

def create_entry(err=None):
    """Create a new entry."""

    prompts = OrderedDict([
        ('employee', "Enter the employee's full name: "),
        ('title', "Enter a title for the entry: "),
        ('date', "Enter a date [dd/mm/yyyy] or leave empty for today: "),
        ('duration', 'Enter the time (in minutes): '),
        ('notes', 'Enter any notes for the entry (press ctrl+d when done):')
    ])

    new_entry = Entry(employee=User(), duration=0)

    with db.atomic() as txn:

        for att, prompt in prompts.items():
            
            while True:

                display_entry(new_entry, err)

                # if entering notes, allow for multiple line entry
                if att == 'notes':
                    print(prompt)
                    new_val = sys.stdin.read().strip()

                else:
                    new_val = input(prompt).strip().lower()

                # if entering a username, either get an existing user or create
                # a new one (usernames must be unique)
                if att == 'employee':
                    user, created = User.get_or_create(username=new_val)
                    new_val = user

                # allow for error message display if setting an attribute is
                # unsuccessful
                try:
                    setattr(new_entry, att, new_val)
                except (ValueError, TypeError) as error:
                    err = str(error)
                    continue

                new_entry.save()
                break

        if input("Save entry? [Y/n]") == 'n':

            txn.rollback()

        else:
            txn.commit()



def search_entries(err=None):
    """Search existing entries"""
    menu_loop(search_menu, err)
    # can be searched by date, duration, or keyword
    pass

def search_by_date(err=None):
    """Search by Date"""

    entries = Entry.select().order_by(Entry._date.desc())

    dates = sorted(set([entry.date for entry in entries]))

    display_dates(dates, err)

    print("To view entries either:")
    print("  1) Enter a date [dd/mm/yyyy] from above or")
    print("  2) Enter two dates (separated by space) to view entries within a range")
    #import pdb; pdb.set_trace()
    query = input().strip().split()

    try:
        query[0] = datetime.datetime.strptime(query[0], DATE_FMT).date()
        if len(query) > 1:
            query[1] = datetime.datetime.strptime(query[1], DATE_FMT).date()
    except Exception as e:
        err = str(e)
        return

    # query will either be single item list or 2 list items

    if len(query) > 2:
        # improper format
        err = "You may only search one or two dates."
        return

    view_entries(err, ('date', query))

def search_by_employee(err=None):
    """Search by Employee"""

    print("Enter an employee name (or part of one):")

    name_search = input().strip()

    try:
        employees = User.select().where(User.username.contains(name_search))
    except UserDoesNotExist as e:
        err = str(e)
        return

    if len(employees) > 1:
        for idx, e in enumerate(employees):
            print("{}) {}".format(idx+1, e.username))

        print('Two or more employees found. Enter a number above to continue.')

        try:
            selection = int(input().strip())
        except TypeError as te:
            err = str(te)
            return

        query = employees[selection - 1]

    view_entries(err, ('employee', query))

def search_by_keyword(err=None):
    """Search by Keyword"""
    pass

def view_entries(err=None, query=None):
    # query can be tuple with type and query itself
    # queries are already sanitized/validated to be correct
        # e.g. ('date range', (date1, date2))
        # e.g. ('keyword', 'string to search')
        # e.g. ('duration', int(44))

    entries = Entry.select()

    if query:
         entries = filter_entries(entries, *query)

    if not entries:
        err = "No Entries found for that criteria."
        return

    option = ''
    idx = 0

    #import pdb; pdb.set_trace()
    
    while option != 'q':

        display_entry(entries[idx], err)

        if idx < len(entries)-1 :
            print('n) next entry')
        if idx != 0:
            print('p) previous entry')

        print('e) edit entry')
        print('d) delete entry')
        print('q) back to search menu')

        option = input('Action: ')

        if (idx == len(entries)-1 and option == 'n') or (idx == 0 and option == 'p'):
            err = "You've reached the end of the found entries."
        elif option == 'n':
            idx += 1
            err = ''
        elif option == 'p':
            idx -= 1
            err = ''
        elif option == 'e':
            update_entry(entries[idx], err)
            break
        elif option == 'd':
            delete_entry(entries[idx])
            break

def filter_entries(entries, query_type, query_params):
    filter_entries = []

    if query_type == 'date':
        if len(query_params) == 2:
            filtered_entries = entries.where(
                query_params[0] <= Entry._date <= query_params[1])
        else:
            filtered_entries = entries.where(Entry._date == query_params[0])

    elif query_type == 'employee':
        filtered_entries = entries.where(Entry.employee == query_params)

    elif query_type == 'keyword':
        filtered_entries = entries.where(Entry.notes.contains(query_params))

    return filtered_entries

def update_entry(entry, err):

    prompts = OrderedDict([
        ('employee', "Enter the employee's full name: "),
        ('title', "Enter a title for the entry: "),
        ('date', "Enter a date [dd/mm/yyyy] or leave empty for today: "),
        ('duration', 'Enter the time (in minutes): '),
        ('notes', 'Enter any notes for the entry (press ctrl+d when done):')
    ])

    with db.atomic() as txn:

        for att, prompt in prompts.items():

            while True:
                
                display_entry(entry, err)

                # cycle through prompts checkking for confirmation to edit

                response = input("UPDATE {}? [y/N] ".format(att.upper())).strip()

                if response.lower() == 'y':
                    clear()
                    print("CURRENT {}:".format(att.upper()))
                    print(getattr(entry, att))
                    print()

                    if att == 'notes':
                        print(prompt)
                        new_val = sys.stdin.read().strip()

                    else:
                        new_val = input(prompt).strip().lower()

                    if att == 'employee':
                        user, created = User.get_or_create(username=new_val)
                        new_val = user

                    try:
                        setattr(entry, att, new_val)
                    except (ValueError, TypeError) as error:
                        err = str(error)
                        continue

                    entry.save()

                break

        display_entry(entry, err)

        if input('Save Updates? [y/N]').strip().lower() == 'y':

            txn.commit()

        else:

            txn.rollback()

def delete_entry(entry):

    display_entry(entry)

    if input('Delete this entry? [y/N] ') == 'y':

        entry.delete_instance()

    else:

        return

def display_entry(entry, err=None):

    clear()

    ts = entry.date.strftime(DATE_FMT)
    duration_td = datetime.timedelta(minutes=int(entry.duration))
    header_data = [entry.title.title(), ts, duration_td]
    header_str = 'TITLE: {0}     DATE: {1}     DURATION: {2}'.format(*header_data)

    print('=' * len(header_str))
    print(header_str)
    print('=' * len(header_str) + '\n')

    if entry.employee.username:
        print('\tEMPLOYEE: {}\n'.format(entry.employee.username.title()))
    else:
        print('\tEMPLOYEE: {}\n'.format(entry.employee.username))

    print('\tNOTES: {}\n'.format(entry.notes))
    print('=' * len(header_str))

    if err:
        print('*** ERROR: {} ***'.format(err))

def display_dates(date_list, err=None):
    
    for date in date_list:
        print(date.strftime(DATE_FMT))

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

main_menu = OrderedDict([
    ('c', create_entry),
    ('s', search_entries)
])

search_menu = OrderedDict([
    ('d', search_by_date),
    ('r', search_by_employee),
    ('k', search_by_keyword)
])

def main():
    initialize()
    menu_loop(main_menu, ERR)

if __name__ == '__main__':
    
    main()











