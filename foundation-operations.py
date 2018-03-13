#!/usr/bin/python

import socket
import smtplib
import string
import sys
import os
import datetime as dt

from email.mime.text import MIMEText
from optparse import OptionParser

sys.path.append('/home/admin/bin')
from gnome_ldap_utils import *

usage = "usage: %prog [options]"
parser = OptionParser(usage)

parser.add_option("--send-form-letters",
                  action="store_true", default=False,
                  help="Checks for LastRenewedOn / FirstAdded fields and send "
                       "welcome emails to new or existing Foundation members accordingly")
parser.add_option("--automatic-subscriptions",
                  action="store_true", default=False,
                  help="Automatically subscribes new Foundation members to the foundation-announce "
                       "mailing list. To be executed on smtp.gnome.org")
parser.add_option("--sync-foundation-with-mailusers",
                  action="store_true", default=False,
                  help="Make sure foundation LDAP group members are synced to the mailusers group "
                       "which is then exported through the export-mail.py script")
parser.add_option("--remove-expired-foundation-members",
                  action="store_true", default=False,
                  help="Foundation membership lasts two years, remove expired members from the "
                       "foundation LDAP group")
parser.add_option("--generate-membership-list",
                  action="store_true", default=False,
                  help="Generate and publish the Foundation membership list that will appear at "
                       "https://www.gnome.org/foundation/membership")

(options, args) = parser.parse_args()

if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)

execfile('/home/admin/secret/freeipa')

glu = Gnome_ldap_utils(LDAP_GROUP_BASE, LDAP_HOST, LDAP_USER_BASE, 'cn=Directory Manager', ldap_password)

today = dt.date.today()
foundationmembers = glu.get_uids_from_group('foundation')


def send_renewal_emails():
    _today = str(today)

    for member in foundationmembers:
        ldap_fields = glu.get_attributes_from_ldap(member, 'FirstAdded', 'LastRenewedOn', 'mail', 'cn')

        first_added_attr = ldap_fields[1]
        last_renewed_on_attr = ldap_fields[2]
        mail_attr = ldap_fields[3]
        common_name_attr = ldap_fields[4]
        userid_attr = ldap_fields[0]

        if (first_added_attr and last_renewed_on_attr):
            if (last_renewed_on_attr == _today) and (first_added_attr == _today):
                send_form_letters(new_member_form_letter, mail_attr, common_name_attr, userid_attr)
            elif last_renewed_on_attr == _today:
                send_form_letters(renewal_form_letter, mail_attr, common_name_attr)


def sync_foundation_with_mailusers():
    mailusers = glu.get_uids_from_group('mailusers')

    for member in foundationmembers:
        if member not in mailusers:
            glu.add_user_to_ldap_group(member, 'mailusers')


def remove_expired_memberships_from_foundation():
    import dateutil.relativedelta as relativedelta
    delta_2y = relativedelta.relativedelta(years=2)
    delta_21d = relativedelta.relativedelta(days=21)
    members_list = ''

    for member in foundationmembers:
        ldap_fields = glu.get_attributes_from_ldap(member, 'LastRenewedOn', 'mail', 'cn')

        last_renewed_on_attr = ldap_fields[1]
        last_renewed_on = dt.date(int(last_renewed_on_attr.split('-')[0]), int(last_renewed_on_attr.split('-')[1]), int(last_renewed_on_attr.split('-')[2]))
        mail_attr = ldap_fields[2]
        common_name_attr = ldap_fields[3]

        if today == (last_renewed_on + delta_2y - delta_21d):
           send_form_letters(close_to_expire_membership_form_letter, mail_attr, common_name_attr, last_renewed_on_attr)
        elif (today - delta_2y) == last_renewed_on:
            print "Removing %s from the foundation LDAP group as the membership expired on %s" % (member, last_renewed_on_attr)
            glu.remove_user_from_ldap_group(member, 'foundation')
            send_form_letters(expired_membership_form_letter, mail_attr, common_name_attr, last_renewed_on_attr)

        if (last_renewed_on.year == (today - delta_2y).year) and (last_renewed_on.month == today.month) and (today.day == 15):
           members_list += common_name_attr + ', ' + last_renewed_on_attr + '\n'

    if len(members_list) > 0:
      send_form_letters(renewals_to_foundation_list, 'foundation-list@gnome.org', 'foundation-list', members_list)


def generate_membership_list():
    import json

    result = []

    for member in foundationmembers:
        ldap_fields = glu.get_attributes_from_ldap(member, 'cn', 'LastRenewedOn')
        common_name_attr = ldap_fields[1]
        last_renewed_on_attr = ldap_fields[2]

        d = { 'common_name' : common_name_attr, 'last_renewed_on' : last_renewed_on_attr }
        result.append(d)

    memberslist = json.dumps(result, ensure_ascii=False, encoding='utf8')

    if len(memberslist) > 0:
        import codecs
        membershipfile = codecs.open('/var/www/html/foundation/membershiplist', 'w', 'utf8')
        membershipfile.write(memberslist)
        membershipfile.close()


def send_form_letters(form_letter, email, name, *args):
    year_month = str(today.year) + '-' + str(today.month)

    try:
        if form_letter is new_member_form_letter:
            msg = MIMEText(form_letter.safe_substitute(cn=name,
                           uid=args[0]), 'plain', 'utf8')
        elif form_letter is renewal_form_letter:
            msg = MIMEText(form_letter.safe_substitute(cn=name),
                           'plain', 'utf8')
        elif form_letter in (expired_membership_form_letter, close_to_expire_membership_form_letter):
            msg = MIMEText(form_letter.safe_substitute(cn=name,
                           last_renewed_on_date=args[0]), 'plain', 'utf8')
        elif form_letter is renewals_to_foundation_list:
            msg = MIMEText(form_letter.safe_substitute(expired_members=args[0]),
                           'plain', 'utf8')

        if form_letter is renewals_to_foundation_list:
            msg['Subject'] = "Memberships needing renewal (%s)" % year_month
        else:
            msg['Subject'] = "Your GNOME Foundation Membership"
        msg['From'] = "GNOME Foundation Membership Committee <noreply@gnome.org>"
        msg['To'] = "%s" % (email)
        msg['Reply-To'] = "membership-committee@gnome.org"
        msg['Cc'] = "membership-committee@gnome.org"
        server = smtplib.SMTP("localhost")
        server.sendmail(msg['From'], [msg['To'], msg['Cc']], msg.as_string())
        server.quit()
        print "Successfully sent email to %s with email %s" % (name, email)
    except smtplib.SMTPException:
        print "ERROR: I wasn't able to send the email correctly, please check /var/log/maillog!"


def subscribe_new_members():
    _today = str(today)

    if socket.gethostname() != 'restaurant.gnome.org':
        sys.exit("This function should only be used on restaurant.gnome.org")

    f = open('/tmp/new_subscribers', 'w')

    for member in foundationmembers:
        ldap_fields = glu.get_attributes_from_ldap(member, 'FirstAdded', 'LastRenewedOn', 'uid')
        first_added_attr = ldap_fields[1]
        last_renewed_on_attr = ldap_fields[2]
        uid_attr = ldap_fields[3]
        gnome_alias = '%s@gnome.org' % (uid_attr)

        if first_added_attr == _today:
            f.write(str(gnome_alias) + '\n')
        elif last_renewed_on_attr == _today:
            f.write(str(gnome_alias) + '\n')
        else:
            pass

    f.close()

    if os.path.getsize('/tmp/new_subscribers') == 0:
        os.remove('/tmp/new_subscribers')
    else:
        import subprocess
        subscribe = subprocess.Popen(['/usr/lib/mailman/bin/add_members', '-a', 'n', '-r', '/tmp/new_subscribers', 'foundation-announce'])
        subscribe.wait()
        os.remove('/tmp/new_subscribers')


new_member_form_letter = string.Template("""
Dear $cn,

Congratulations, you are now a member of the GNOME Foundation! Welcome, and
thank you for supporting GNOME. Your name has joined those of the rest of the
Foundation Membership:

   https://www.gnome.org/foundation/membership

As a member of the Foundation, you are able to vote in the elections of the
Board of Directors, and you can also put yourself forward as a candidate for
the Board. There are many other benefits to being a member, including having
your blog on Planet GNOME, a @gnome.org email address, an Owncloud account,
your own blog hosted within the GNOME Infrastructure and the ability to apply
for travel subsidies. A full list of the benefits and the guidelines to obtain
them is available at:

   https://wiki.gnome.org/MembershipCommittee/MembershipBenefits

While all the available benefits can be obtained on demand by looking at the above
URL, @gnome.org email aliases are automatically created within 24 hours from the
arrival of this email on your INBOX. Instructions for correctly setting up your
email alias can be found at the following link:

   https://wiki.gnome.org/AccountsTeam/MailAliasPolicy#Mail_aliases_configuration

If you are interested in managing your Foundation Membership information (including
where your @gnome.org alias is supposed to forward to) and you didn't have a GNOME
Account before today, please get in touch with the GNOME Accounts Team at <accounts@gnome.org>.
Existing GNOME Account owners can reset their password with the following command:

   ssh -l $uid account.gnome.org

And login at:

   https://account.gnome.org

To help you stay informed about GNOME Foundation events, we have subscribed you
to the foundation-announce mailing list, where all the major GNOME Foundation
announcements are sent. It is a low volume list and does not allow subscribers
to post emails. If you would like to read the archives you can do so here:

    https://mail.gnome.org/mailman/listinfo/foundation-announce

We also encourage you to subscribe to the foundation-list mailing
list. It is used to discuss any issue relating to the GNOME Foundation. This is
the place for you to suggest ideas and voice your opinions on issues pertaining
to the GNOME Foundation. To subscribe or read the archives, go to:

    https://mail.gnome.org/mailman/listinfo/foundation-list

We also highly encourage you to introduce yourself to the members by
writing to foundation-list. Please list your contributions and write a
little about yourself, if you like :-)

We have a map of contributors on our wiki. If you want others to be able to find
you, you may add yourself to the list. This might be a good opportunity to find
other contributors in your area:

    https://wiki.gnome.org/GnomeWorldWide

For more information about the GNOME Foundation, visit the GNOME Foundation's
web page at:

    https://www.gnome.org/foundation

Thank you for all your great work as a member of the GNOME community.

Best wishes,

The GNOME Foundation Membership Committee""")

renewal_form_letter = string.Template("""
Dear $cn,

We are pleased to inform you that your GNOME Foundation Membership has
been renewed for two years.

Thank you for your ongoing contributions to GNOME, and for continuing to
support the GNOME Foundation.

You are eligible to become a candidate for election and to vote in the annual
Board of Directors elections held each June before GUADEC. If you were not
already subscribed to the foundation-announce mailing list, you have been
subscribed to this list, where all the major GNOME Foundation announcements are
sent. It is a low volume list and does not allow subscribers to post emails. If
you would like to read the archives you can do so here:

    https://mail.gnome.org/mailman/listinfo/foundation-announce

You are also encouraged to subscribe to the foundation-list mailing list. It is
open to the public (even non-members) and is used to discuss any issue relating
to the GNOME Foundation. This is the place for you to suggest ideas and voice
your opinions on issues pertaining to the GNOME Foundation. To subscribe or
read the archives, go to:

    https://mail.gnome.org/mailman/listinfo/foundation-list

For more information about the GNOME Foundation, visit the GNOME Foundation's
web page at:

    https://www.gnome.org/foundation

Thanks for your contributions to GNOME.

Best wishes,

The GNOME Foundation Membership Committee""")

expired_membership_form_letter = string.Template("""
Dear $cn,

from our records it seems your GNOME Foundation Membership was last renewed
on $last_renewed_on_date (YYYY-MM-DD) and its duration is currently set to be two years.

If you want to continue being a member of the GNOME Foundation please make sure to submit
a renewal request at https://foundation.gnome.org/membership/apply. If you did
so already, please ignore this e-mail and wait for the GNOME Foundation Membership
Committee to get back to you.

More details on when your membership was last renewed can be found on your profile page
at https://account.gnome.org under the 'Last Renewed on date' field.

In the case you feel your contributions would not be enough for the membership
renewal to happen you can apply for the Emeritus status:

  https://wiki.gnome.org/MembershipCommittee/EmeritusMembers

Additionally, please give a look at the Membership benefits:

  https://wiki.gnome.org/MembershipCommittee/MembershipBenefits

Thanks,
  The GNOME Membership and Elections Committee""")

close_to_expire_membership_form_letter = string.Template("""
Dear $cn,

from our records it seems your GNOME Foundation Membership is about to expire within
three (3) weeks starting from today as it was las renewed on $last_renewed_on_date (YYYY-MM-DD).
Membership duration is currently set to be two years.

If you want to continue being a member of the GNOME Foundation please make sure to submit
a renewal request at https://foundation.gnome.org/membership/apply. If you did
so already, please ignore this e-mail and wait for the GNOME Foundation Membership
Committee to get back to you.

More details on when your membership was last renewed can be found on your profile page
at https://account.gnome.org under the 'Last Renewed on date' field.

In the case you feel your contributions would not be enough for the membership
renewal to happen you can apply for the Emeritus status:

  https://wiki.gnome.org/MembershipCommittee/EmeritusMembers

Additionally, please give a look at the Membership benefits:

  https://wiki.gnome.org/MembershipCommittee/MembershipBenefits

Thanks,
  The GNOME Membership and Elections Committee""")

renewals_to_foundation_list = string.Template("""
Hi,

as per point 1.3 of [1], here it comes a list of members in need of a
renew in case they didn't receive their individual e-mail:

First name Last name, (Last renewed on)

$expired_members

The Renewal form can be found at [2].

Cheers,
   GNOME Membership and Elections Committee

[1] https://mail.gnome.org/archives/foundation-list/2011-November/msg00000.html
[2] http://www.gnome.org/foundation/membership/apply/

""")


def main():
    if options.send_form_letters:
        send_renewal_emails()

    if options.automatic_subscriptions:
        subscribe_new_members()

    if options.sync_foundation_with_mailusers:
        sync_foundation_with_mailusers()

    if options.remove_expired_foundation_members:
        remove_expired_memberships_from_foundation()

    if options.generate_membership_list:
        generate_membership_list()


if __name__ == "__main__":
    main()
