#!/usr/bin/python
# Author: Andrea Veri <av@gnome.org>
# Target host: palette.gnome.org
# Description: script to automatize new Prosody user creation at jabber.gnome.org.

import random
import string
import pexpect
from email.mime.text import MIMEText
import smtplib
import sys
import os

if os.getuid() != 0:
    sys.exit("The script has to be run as root")


def create_prosody_account():

    print 'Please enter the JID for the new user and the email to send instructions to,'
    print 'additionally make sure the JID matches the LDAP UID for the user requesting the account'
    username = raw_input('Desired username: ')
    email = raw_input('Email to send instructions to: ')

    s = string.lowercase+string.digits
    random_password = ''.join(random.sample(s, 10))

    child = pexpect.spawn ('prosodyctl adduser %s@jabber.gnome.org' % (username))
    child.expect ('Enter new password: ')
    child.sendline ('%s' % random_password)
    child.expect ('Retype new password: ')
    child.sendline ('%s' % random_password)
    child.expect(pexpect.EOF)
    child.close()

    if child.exitstatus == 1:
       raise Exception("There was an error creating the Prosody account, please check logs!")

    message = """
Hi,

as requested, your Jabber account at GNOME.org has  been created, the details:

User: %s@jabber.gnome.org
Password: %s

Please update the password as soon as you can by using the Gajim
client. Unfortunately this feature is not yet available on Empathy. See
https://bugzilla.gnome.org/show_bug.cgi?id=576999 for more details. """ % (username, random_password)

    try:
        msg = MIMEText(message)
        msg['Subject'] = "Your Jabber account at GNOME.org"
        msg['From']    = "accounts@gnome.org"
        msg['To']      = "%s" % (email)
        server = smtplib.SMTP("localhost")
        server.sendmail (msg['From'], msg['To'], msg.as_string())
        server.quit ()
        print "Successfully sent email to %s" % (email)
    except smtplib.SMTPException:
        print "ERROR: I wasn't able to send the email correctly, please check /var/log/maillog!"


create_prosody_account()
