#!/usr/bin/python

import mysql.connector

id = 0

number_of = raw_input("How many columns are you willing to create? ")
type = raw_input("What type of MySQL columns? Valid Values are int, float, varchar. Enter value: ")

types = ['int', 'float', 'varchar']

if type in types:
    pass
else:
    print 'You should enter either int, float or varchar'


def query_database_with(query):

    db = mysql.connector.connect(host="localhost",
        user = "",
        passwd = "",
        db = "",
        charset='utf8')

    cur = db.cursor()
    cur.execute(query)
    db.commit()

    cur.close()


while True:
    if id <= int(number_of):
        if type == 'varchar' or type == 'varchar(60)':
            column_name = 'test_column_varchar'
            type = 'varchar(60)'
        elif type == 'float' or type == 'float(10,2)':
            column_name = 'test_column_float'
            type = 'float(10,2)'
        elif type == 'int':
            column_name = 'test_column_int'

        id += 1

        _list = [column_name, str(id)]

        column_name = '_'.join(_list)

        query_database_with('alter table table_test add column %s %s;' % (column_name, type))
        print 'Column name: %s. Type: %s. Created.' % (column_name, type)

        _list = []
        column_name = ''
    else:
       break
