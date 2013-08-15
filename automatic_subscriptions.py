#!/usr/bin/python

# This script will periodically check the foundation_db and automatically
# subscribe new Foundation members to the relevant mailing list. (foundation-announce)
# Author: Andrea Veri <av@gnome.org>

import MySQLdb
import subprocess
import os

file = open('/home/admin/secret/anonvoting','r')
lines = file.readlines()

for line in lines:
        if line.find("mysql_password") > -1:
                dirty_password = line.split()
                anonvoting_password = str(dirty_password)

                sanitize_file=["\'","(",")","$mysql_password","=","[","]","\"",";"]
                for i in range(len(sanitize_file)):
                        anonvoting_password = anonvoting_password.replace(sanitize_file[i],"")
file.close()

db = MySQLdb.connect(host="drawable-back",
                     user="anonvoting",
                     passwd=anonvoting_password,
                     db="foundation")
cur = db.cursor() 

cur.execute("SELECT email from foundationmembers WHERE TO_DAYS(last_renewed_on)=To_DAYS(NOW()); SELECT email from foundationmembers WHERE TO_DAYS(first_added)=To_DAYS(NOW())")
result=cur.fetchall()

def subscribe_new_members():
		f = open ('/tmp/new_subscribers', 'w' )
		for row in result:
    			f.write (str(row[0]) + "\n")
		f.close()

		if os.path.getsize('/tmp/new_subscribers') == 0:
			os.remove('/tmp/new_subscribers')
		else:
			subscribe = subprocess.Popen(['/usr/lib/mailman/bin/add_members', '-a', 'n', '-r', '/tmp/new_subscribers', 'foundation-announce'])
			subscribe.wait()
			os.remove('/tmp/new_subscribers')

subscribe_new_members()
