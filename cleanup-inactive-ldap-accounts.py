#!/usr/bin/python

from __future__ import print_function
import datetime
import os
import sys
import calendar
import time
import socket
import smtplib

from optparse import OptionParser
from email.MIMEText import MIMEText

from gnome_ldap_utils import *

execfile('/home/admin/secret/freeipa')

glu = Gnome_ldap_utils(LDAP_GROUP_BASE, LDAP_HOST, LDAP_USER_BASE, 'cn=Directory Manager', ldap_password)

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

infrastructure_folders = 'archive', 'cgit', 'empty-description', 'repositories.txt', 'repositories.doap', 'moved_to_gitlab'
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


def add_remove_comment_to_user(username, group):
    new_comment = 'Removed from group %s by cleanup-inactive-ldap-accounts at %s.' % (group, datetime.date.today())

    ldap_fields = glu.get_attributes_from_ldap(username, 'cn', 'description', 'mail')
    current_comment = ldap_fields[2]
    name = ldap_fields[1]
    mail = ldap_fields[3]

    if current_comment is None:
        comment = new_comment

        glu.add_or_update_description(username, comment, add=True)
    else:
        comment = '%s. %s' % (current_comment, new_comment)

        glu.add_or_update_description(username, comment, update=True)

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


excludes = ['root', 'sysadmin', 'gitadmin', 'translations',
            'gitadmin', 'otaylor', 'puiterwijk', 'av']

gnomecvs_users = (glu.get_uids_from_group('gnomecvs', excludes))
ftpadmin_users = (glu.get_uids_from_group('ftpadmin', excludes))

for gnomecvs_user in gnomecvs_users:
    if not user_is_current(gnomecvs_user):
        if options.verbose:
            print ("Removing user %s from gnomecvs" % gnomecvs_user, end='\n')

        glu.remove_user_from_ldap_group(gnomecvs_user, 'gnomecvs')
        add_remove_comment_to_user(gnomecvs_user, 'gnomecvs')

for ftpadmin_user in ftpadmin_users:
    if not user_is_current(ftpadmin_user):
        if options.verbose:
            print ("Removing user %s from ftpadmin" % ftpadmin_user, end='\n')

        glu.remove_user_from_ldap_group(ftpadmin_user, 'ftpadmin')
        add_remove_comment_to_user(gnomecvs_user, 'ftpadmin')
