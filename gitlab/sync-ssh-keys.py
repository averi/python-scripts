#!/usr/bin/python

import sys
sys.path.append('/home/admin/bin')

from gnome_ldap_utils import *
from gitlab import *

execfile('/home/admin/secret/freeipa')

glu = Gnome_ldap_utils(LDAP_GROUP_BASE, LDAP_HOST, LDAP_USER_BASE, 'cn=Directory Manager', ldap_password)
gitlab = Gitlab('gitlab.gnome.org', GITLAB_PRIVATE_TOKEN)

gnomecvs_members = glu.get_uids_from_group('gnomecvs')

for id, username in gitlab.list_ldap_users().iteritems():
    ssh_key = glu.get_attributes_from_ldap(username, 'ipaSshPubKey')
    gitlab.add_ssh_keys(ssh_key, id)

#for username in gitlab.list_group_members('GNOME'):
#    if username not in gnomecvs_members:
#        print '%s is NOT part of the gnomecvs LDAP group' % username
