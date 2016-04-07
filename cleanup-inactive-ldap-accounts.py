#!/usr/bin/python

from __future__ import print_function
import datetime
import os
import sys
import calendar
import time
import ldap
import ldap.filter
import socket
from optparse import OptionParser
import smtplib
from email.MIMEText import MIMEText

LDAP_GROUP_BASE='cn=groups,cn=accounts,dc=gnome,dc=org'
LDAP_USER_BASE='cn=users,cn=accounts,dc=gnome,dc=org'

execfile('/home/admin/secret/freeipa')

parser = OptionParser()
parser.add_option("--print-inactive-accounts", action="store_true", default=False,
                  help="Generates a list of inactive accounts by parsing each gnome_pushlog file. The list includes accounts that have been removed already")
parser.add_option("--verbose",
                  action="store_true", dest="verbose", default=False,
                  help="Prints the list of accounts that are getting removed from gnomecvs/ftpbasic as the scripts runs")

(options, args) = parser.parse_args()

if socket.gethostname() != 'git.gnome.org':
    print ("You are not allowed to run this script on a different host than git.gnome.org, exiting...", end='\n')
    sys.exit(1)

infrastructure_folders = 'archive', 'cgit', 'empty-description', 'repositories.txt', 'repositories.doap'
repositories = filter( lambda f: not f.startswith(infrastructure_folders), os.listdir('/git'))
last_pushed_times = {}


for repository in repositories:
    pushlog = open('/git/%s/gnome_pushlog' % repository, 'r')
    for line in pushlog.readlines():
        fields = line.rstrip().split('\t')
        username = fields[3]
        pushtime = calendar.timegm(time.strptime(fields[4], '%a, %d %b %Y %H:%M:%S +0000'))
        if not username in last_pushed_times or pushtime > last_pushed_times[username]:
            last_pushed_times[username] = pushtime

now = time.time()

for user, last_pushed in last_pushed_times.iteritems():
    if last_pushed < now - 2 * 365 * 24 * 60 * 60:
        last_pushed = time.gmtime(last_pushed)
        if options.print_inactive_accounts:
            print ("%s: %s" % (user, time.strftime("%d-%m-%Y", last_pushed)), end='\n')


def user_is_current(username):
     return username in last_pushed_times and last_pushed_times[username] >= now - 2 * 365 * 24 * 60 * 60


try:
    l = ldap.open('account.gnome.org')
    l.simple_bind("cn=Directory Manager", ldap_password)
except ldap.LDAPError, e:
    print >>sys.stderr, e
    sys.exit(1)

# Import the various LDAP functions from the create-auth script.
def _get_group_from_ldap(group):

    filter = ldap.filter.filter_format('(&(objectClass=posixGroup)(cn=%s))', (group, ))
    results = l.search_s(LDAP_GROUP_BASE, ldap.SCOPE_SUBTREE, filter, ('member', ))

    members = set()

    for _, attr in results:
        for userid in attr['member']:
            splitentry = userid.split(',')
            singleentry = splitentry[0]
            splitteduid = singleentry.split('=')
            uid = splitteduid[1]

            members.add(uid)

    return members

def get_uids_from_group(group):
    people = _get_group_from_ldap(group)

    people.discard('root')
    people.discard('sysadmin')
    people.discard('translations')
    people.discard('gitadmin')
    people.discard('otaylor')
    people.discard('puiterwijk')
    people.discard('av')

    return people

def add_remove_comment_to_user(username, group):
    new_comment = 'Removed from group %s by cleanup-inactive-ldap-accounts at %s.' % (group, datetime.date.today())
    filter = ldap.filter.filter_format('(uid=%s)', (username, ))
    results = l.search_s(LDAP_USER_BASE, ldap.SCOPE_SUBTREE, filter, ('uid', 'cn', 'description', 'mail', ))

    if not len(results) > 0:
        # Something went very wrong here...
        return False

    try:
        current_comment = results[0][1]['description'][0]

        has_description = True
    except KeyError:
        has_description = False

    if has_description == False:
        comment = new_comment

        update_comment = [(ldap.MOD_ADD, 'description', comment)]
        l.modify_s('uid=%s,%s' % (username, LDAP_USER_BASE), update_comment)
    elif has_description == True:
        comment = '%s %s' % (current_comment, new_comment)

        update_comment = [(ldap.MOD_REPLACE, 'description', comment)]
        l.modify_s('uid=%s,%s' % (username, LDAP_USER_BASE), update_comment)

    name = results[0][1]['cn'][0]
    mail = results[0][1]['mail'][0]

    form_letter = """
Hello %s, your membership of the group %s has been automatically removed, due to inactivity.

For more information, please see the following email:
https://mail.gnome.org/archives/foundation-list/2014-March/msg00063.html

With cordiality,

the GNOME Accounts Team""" % (name, group)

    try:
        msg = MIMEText(form_letter)
        msg['Subject'] = "Your GNOME group membership expired"
        msg['From']    = "noreply@gnome.org"
        msg['To']      = "%s" % (mail)
        msg['Reply-To']= "accounts@gnome.org"
        server = smtplib.SMTP("localhost")
        server.sendmail(msg['From'], msg['To'], msg.as_string())
        server.quit()
    except smtplib.SMTPException:
        # Too bad, they'll have to contact sysadmin
        pass

    return True


gnomecvs_users = (get_uids_from_group('gnomecvs'))
ftpadmin_users = (get_uids_from_group('ftpadmin'))

for gnomecvs_user in gnomecvs_users:
    if not user_is_current(gnomecvs_user):
        if options.verbose:
            print ("Removing user %s from gnomecvs" % gnomecvs_user, end='\n')
        remove_members = [ (ldap.MOD_DELETE, 'member','uid=%s,%s' % (gnomecvs_user, LDAP_USER_BASE)) ]
        l.modify_s('cn=gnomecvs,%s' % LDAP_GROUP_BASE, remove_members)
        add_remove_comment_to_user(gnomecvs_user, 'gnomecvs')

for ftpadmin_user in ftpadmin_users:
    if not user_is_current(ftpadmin_user):
        if options.verbose:
            print ("Removing user %s from ftpadmin" % ftpadmin_user, end='\n')
        remove_members = [ (ldap.MOD_DELETE, 'member','uid=%s,%s' % (ftpadmin_user, LDAP_USER_BASE)) ]
        l.modify_s('cn=ftpadmin,%s' % LDAP_GROUP_BASE, remove_members)
        add_remove_comment_to_user(gnomecvs_user, 'ftpadmin')
