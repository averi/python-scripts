#!/usr/bin/python

import ldap
import ldap.filter
import string
import smtplib
import sys
import os
import ldap.modlist as modlist
from email.MIMEText import MIMEText

LDAP_GROUP_BASE='cn=groups,cn=accounts,dc=gnome,dc=org'
LDAP_USER_BASE='cn=users,cn=accounts,dc=gnome,dc=org'


execfile('/home/admin/secret/freeipa')

try:
    l = ldap.open('localhost')
    l.simple_bind("cn=Directory Manager", ldap_password)
except ldap.LDAPError, e:
        print >>sys.stderr, e
        sys.exit(1)


def _parse_members_from_group(group):

    filter = ldap.filter.filter_format('(&(objectClass=posixgroup)(cn=%s))', (group, ))
    results = l.search_s(LDAP_GROUP_BASE, ldap.SCOPE_SUBTREE, filter, ('memberUid', ))

    members = set()

    for _, attr in results:
        members.update(attr['memberUid'])


    return members


def _get_attributes_from_ldap(userid, attr):
    filter = ldap.filter.filter_format('(uid=%s)', (userid, ))
    results = l.search_s(LDAP_USER_BASE, ldap.SCOPE_SUBTREE, filter, ('uid', attr, ))

    if len(results) > 0:
        return results[0][1][attr][0]
    else:
        return None


def gen_passwd(length=12, chars=string.letters + string.digits):
    urandom = open("/dev/urandom")
    # ensure even distribution of randomly selected characters
    m = 255 - 255 % len(chars)

    buf = ''
    pos = 0
    pwd = ''
    while len(pwd) < length:
        if pos == len(buf):
            buf = urandom.read(length * 2)
            pos = 0
        v = ord(buf[pos])
        pos += 1

        if v > m:
            continue
        pwd += chars[v % len(chars)]

    urandom.close()

    return pwd


def check_existing_password(userid):
    accountsteam =  _parse_members_from_group('accounts')
    sysadminteam =  _parse_members_from_group('sysadmin')

    if _get_attributes_from_ldap(userid, 'uid') == None:
       print 'The specified UID does not exist, please get in contact with the GNOME Accounts Team to know more'
       sys.exit(1)

    if userid in (accountsteam or sysadminteam):
       print 'You are not allowed to reset your password, please contact the GNOME Sysadmin Team to know why'
       sys.exit(1)

    update_password(userid)


def update_password(userid):
    getattr_name = _get_attributes_from_ldap(userid, 'cn')
    getattr_mail = _get_attributes_from_ldap(userid, 'mail')

    newpassword = {'userPassword': gen_passwd()}

    replace_password = [(ldap.MOD_REPLACE, 'userPassword', newpassword['userPassword'])]
    l.modify_s('uid=%s,cn=users,cn=accounts,dc=gnome,dc=org' % userid, replace_password)


    send_password_to_user(getattr_name, getattr_mail, newpassword['userPassword'])


def send_password_to_user(name, email, password):
    form_letter = """
Hello %s, your password has been reset successfully. Your temporary password is

%s

Please login at https://account.gnome.org and update your password as soon as possible!

With cordiality,

the GNOME Accounts Team""" % (name, password)

    try:
        msg = MIMEText(form_letter)
        msg['Subject'] = "Your GNOME password has been reset"
        msg['From']    = "noreply@gnome.org"
        msg['To']      = "%s" % (email)
        msg['Reply-To']  = "accounts@gnome.org"
        server = smtplib.SMTP("localhost")
        server.sendmail(msg['From'], msg['To'], msg.as_string())
        server.quit()
        print "Successfully sent your password to the registered email address being %s" % (email)
    except smtplib.SMTPException:
        print "ERROR: I wasn't able to send the email correctly, please check /var/log/maillog!"

my_userid = os.getenv('SUDO_USER')
check_existing_password(my_userid)
