#!/usr/bin/python

import string
import smtplib
import sys
import os

from email.MIMEText import MIMEText
from gnome_ldap_utils import *

execfile('/home/admin/secret/freeipa')

glu = Gnome_ldap_utils(LDAP_GROUP_BASE, LDAP_HOST, LDAP_USER_BASE, 'cn=Directory Manager', ldap_password)


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
    accountsteam =  glu.get_group_from_ldap('accounts')
    sysadminteam =  glu.get_group_from_ldap('sysadmin')

    if glu.get_attributes_from_ldap(userid, 'uid') == None:
       print 'The specified UID does not exist, please get in contact with the GNOME Accounts Team to know more'
       sys.exit(1)

    if userid in (accountsteam or sysadminteam):
       print 'You are not allowed to reset your password, please contact the GNOME Sysadmin Team to know why'
       sys.exit(1)

    update_password(userid)


def update_password(userid):
    getattr_name = glu.get_attributes_from_ldap(userid, 'cn')
    getattr_mail = glu.get_attributes_from_ldap(userid, 'mail')

    newpassword = {'userPassword': gen_passwd()}

    glu.replace_ldap_password(userid, newpassword['userPassword'])

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