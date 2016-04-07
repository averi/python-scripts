#!/usr/bin/python

import mysql.connector
import calendar
import time
import ldap
import ldap.filter

LDAP_USER_BASE='cn=users,cn=accounts,dc=gnome,dc=org'
LDAP_GROUP_BASE='cn=groups,cn=accounts,dc=gnome,dc=org'

ldap_password = ''

try:
    l = ldap.open('localhost')
    l.simple_bind("cn=Directory Manager", ldap_password)
except ldap.LDAPError, e:
    print >>sys.stderr, e
    sys.exit(1)

def _get_group_from_ldap(group):

    filter = ldap.filter.filter_format('(&(objectClass=ipausergroup)(cn=%s))', (group, ))
    results = l.search_s(LDAP_GROUP_BASE, ldap.SCOPE_SUBTREE, filter, ('member', ))

    members = set()
    for entry in results:
        id = entry[0]
        attr = entry[1]

        members.update(attr['member'])

    return members

def get_uids_from_group(group):
    people = _get_group_from_ldap(group)

    return people


def query_database_with(query):

    db = mysql.connector.connect(host="localhost",
    user = "foundation",
    passwd = "",
    db = "foundation",
    charset='utf8')

    cur = db.cursor()
    cur.execute(query)

    result = cur.fetchall()
    return result

    cur.close()

def sync_userid_to_freeipa():
    sync_members = {}
    last_renewed = query_database_with('select userid, first_added from foundationmembers;')

    for member in last_renewed:
        attribute = member[1]
        userid = member[0]
        sync_members[userid] = attribute
        print userid, attribute

def sync_attributes_to_freeipa():
    sync_members = {}
    get_members = query_database_with("select userid, first_added from foundationmembers")

    for member in get_members:
        attribute = member[1]
        userid = member[0]
        sync_members[userid] = attribute

        if userid is not None and userid != '':
            add_firstadded = [(ldap.MOD_ADD, 'FirstAdded', str(attribute))]
            l.modify_s('uid=%s,cn=users,cn=accounts,dc=gnome,dc=org' % str(userid), add_firstadded) 

def sync_changed_to_freeipa():
    sync_members = {}
    get_members = query_database_with("select userid, last_renewed_on from foundationmembers;")

    for member in get_members:
        attribute = member[1]
        userid = member[0]
        sync_members[userid] = attribute
     
        if userid is not None and userid != '':
            add_firstadded = [(ldap.MOD_ADD, 'LastRenewedOn', str(attribute))]
            l.modify_s('uid=%s,cn=users,cn=accounts,dc=gnome,dc=org' % str(userid), add_firstadded)
            print 'Adding %s' % str(userid)

sync_attributes_to_freeipa()
sync_changed_to_freeipa()
