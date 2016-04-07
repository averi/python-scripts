#!/usr/bin/python

import MySQLdb
import ldap
import ldap.filter
import calendar
import time
import getpass
import grp
import sys
import subprocess
import socket
import os
from optparse import OptionParser

LDAP_USER_BASE='ou=people,dc=gnome,dc=org'
LDAP_GROUP_BASE='ou=groups,dc=gnome,dc=org'

usage = "usage: %prog [options] arg"
parser = OptionParser(usage)

parser.add_option("--print-current-members", action="store_true", default=False,
                  help="Generates a list of the current active Foundation Members")
parser.add_option("--sync-resources",
                  action="store_true", default=False,
                  help="Syncs data between the Foundation's DB and LDAP, includes "
                       "@gnome.org alias creations")
parser.add_option("--due-expiration",
                  action="store_true", default=False,
                  help="Generates a list of all the current Foundation members with "
                        "their membershing going to expire within 3 months from "
                        "today. Requires either the --three-months or --six-months flags.")
parser.add_option("--three-months",
                  action="store_true", default=False,
                  help="Generates a list of the members with their membership going "
                       "to expire in 3 months from today")
parser.add_option("--six-months",
                  action="store_true", default=False,
                  help="Generates a list of the members with their membership going "
                       "to expire in 6 months from today")
parser.add_option("--remove-old-foundation-members",
                  action="store_true", default=False,
                  help="Remove old entries from the Foundation database in the case "
                       "an old member did not renew the membership for at least two years")
parser.add_option("--automatic-subscriptions",
                  action="store_true", default=False,
                  help="Automatically subscribes new Foundation members to the foundation-announce "
                       "mailing list. To be executed on smtp.gnome.org")

(options, args) = parser.parse_args()

if options.sync_resources:
        file = open('/home/admin/secret/ldap','r')
        lines = file.readlines()

        for line in lines:
            if line.find("ldap_password") > -1:
                dirty_password = line.split()
               	ldap_password = str(dirty_password)

                sanitize_file=["ldap_password","=","\"","'","[","]"]
                for i in range(len(sanitize_file)):
                    ldap_password = ldap_password.replace(sanitize_file[i],"")
                    file.close()

        try:
            l = ldap.open('ldap.gnome.org')
            l.simple_bind("cn=Manager,dc=gnome,dc=org", ldap_password)
        except ldap.LDAPError, e:
            print >>sys.stderr, e
            sys.exit(1)


def query_database_with(query):
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


    db = MySQLdb.connect(host="range-back",
    user = "anonvoting",
    passwd = anonvoting_password,
    db = "foundation",
    charset='utf8')

    cur = db.cursor()
    cur.execute(query)
    db.commit()

    result = cur.fetchall()
    return result

    cur.close()

def _get_group_from_ldap(group):

    filter = ldap.filter.filter_format('(&(objectClass=posixGroup)(cn=%s))', (group, ))
    results = l.search_s(LDAP_GROUP_BASE, ldap.SCOPE_SUBTREE, filter, ('memberUid', ))

    members = set()
    for entry in results:
        id = entry[0]
        attr = entry[1]

        members.update(attr['memberUid'])

    return members

def get_uids_from_group(group):
    people = _get_group_from_ldap(group)

    return people

def emeritus_members():
    emeritus_members_list = query_database_with("SELECT userid from foundationmembers where emeritus = '1';")

    for row in emeritus_members_list:
        return str(row[0])


def main():
    if options.print_current_members:
        print_current_members()

    if options.due_expiration and not (options.three_months or options.six_months):
        print "Error: the --due-expiration flag requires either the --three-months or the --six-months options"
    elif options.due_expiration and options.three_months or options.six_months:
        print_due_expiration()

    if options.sync_resources:
        sync_foundation_db_with_ldap()

    if options.remove_old_foundation_members:
        remove_old_foundation_members()

    if options.automatic_subscriptions:
        subscribe_new_members()

def remove_old_foundation_members():
    user = getpass.getuser()
    group = grp.getgrnam(user)
    groups_list = group[3]

    if 'membctte' not in groups_list:
        sys.exit("You are not part of the membctte group, exiting...")

    confirmation = raw_input("Are you sure you want to delete old entries from the database? Type 'yes' or 'no' --> ")
    if confirmation in ['yes', 'Yes', 'YES']:
        query_database_with("DELETE from foundationmembers WHERE last_renewed_on < DATE_SUB(CURDATE(), INTERVAL 4 YEAR);")
    elif confirmation in ['no', 'No', 'NO']:
        sys.exit('Exiting...')
    else:
        sys.exit("You did not type either 'yes' or 'no', exiting...")

def print_current_members():
    current_members = query_database_with('select firstname, lastname, last_renewed_on from foundationmembers WHERE ((curdate() - interval 2 year) <= `foundationmembers`.`last_renewed_on`);')
    for row in current_members:
        print row[0] + ' ' + row[1] + ' ' + str(row[2])


def print_due_expiration():
    now = time.time()

    due_expiration = {}
    last_renewed = query_database_with('select firstname, lastname, last_renewed_on from foundationmembers WHERE ((curdate() - interval 2 year) <= `foundationmembers`.`last_renewed_on`);')

    for member in last_renewed:
        timestamp = calendar.timegm(time.strptime(str(member[2]), "%Y-%m-%d"))
        name = member[0] + ' ' + member[1]
        due_expiration[name] = timestamp

    for name, timestamp in due_expiration.iteritems():
        if not timestamp < now - 90 * 24 * 60 * 60 and options.three_months:
            timestamp = time.gmtime(timestamp)
            timestamp = time.strftime("%Y-%m-%d", timestamp)
            print name, timestamp

        if now - 180 * 24 * 60 * 60 < timestamp and timestamp < now - 90 * 24 * 60 * 60 and options.six_months:
            timestamp = time.gmtime(timestamp)
            timestamp = time.strftime("%Y-%m-%d", timestamp)
            print name, timestamp


def sync_user_to_ldap_foundation(username):
    add_members = [(ldap.MOD_ADD, 'memberUid', username)]
    l.modify_s('cn=foundation,ou=groups,dc=gnome,dc=org', add_members)


def sync_user_to_ldap_mailusers(username):
    add_members = [(ldap.MOD_ADD, 'memberUid', username)]
    l.modify_s('cn=mailusers,ou=groups,dc=gnome,dc=org', add_members)


def sync_foundation_db_with_ldap():
    foundationmembers = query_database_with('SELECT userid from electorate;')
    emeritus_members_list = emeritus_members()
    mailusers = (get_uids_from_group('mailusers'))
    foundation = (get_uids_from_group('foundation'))

    for row in foundationmembers:
        if row[0] is not None and row[0] != '':
            if row[0] not in mailusers:
                print 'Adding %s into the mailusers LDAP group' % (str(row[0]))
                (sync_user_to_ldap_mailusers(str(row[0])))
            if row[0] not in foundation:
                print 'Adding %s into the foundation LDAP group' % (str(row[0]))
                (sync_user_to_ldap_foundation(str(row[0])))

    if row[0] is not None and row[0] != '':
        if emeritus_members_list not in mailusers:
            (sync_user_to_ldap_mailusers(emeritus_members_list))


def subscribe_new_members():
    if socket.gethostname() != 'restaurant.gnome.org':
        sys.exit("This function should only be used on restaurant.gnome.org")

    queries = ["SELECT email from foundationmembers WHERE TO_DAYS(last_renewed_on)=To_DAYS(NOW());",
               "SELECT email from foundationmembers WHERE TO_DAYS(first_added)=To_DAYS(NOW());"]

    f = open('/tmp/new_subscribers', 'w')

    for query in queries:
        new_members = query_database_with(query)

        for row in new_members:
            f.write (str(row[0]) + "\n")

    f.close()

    if os.path.getsize('/tmp/new_subscribers') == 0:
        os.remove('/tmp/new_subscribers')
    else:
        subscribe = subprocess.Popen(['/usr/lib/mailman/bin/add_members', '-a', 'n', '-r', '/tmp/new_subscribers', 'foundation-announce'])
        subscribe.wait()
        os.remove('/tmp/new_subscribers')


if __name__ == "__main__":
        main()
