#!/usr/bin/python

import sys
import gitlab

sys.path.append('/home/admin/bin')
sys.path.append('/home/admin/bin/git')
import gnome_ldap_utils
import semi_rdf

from xml.sax import SAXParseException

execfile('/home/admin/secret/freeipa')
execfile('/home/admin/secret/gitlab_rw')

glu = gnome_ldap_utils.Gnome_ldap_utils(LDAP_GROUP_BASE, LDAP_HOST, LDAP_USER_BASE, 'cn=Directory Manager', ldap_password)
gl = gitlab.Gitlab('https://gitlab.gnome.org', GITLAB_PRIVATE_RW_TOKEN, api_version=4)

DOAP = "http://usefulinc.com/ns/doap#"
GNOME = "http://api.gnome.org/doap-extensions#"

ldapusers = gl.users.list(all=True)
ldapusers_dict = {}
gnomecvs_members = glu.get_uids_from_group('gnomecvs')
group = gl.groups.get(8)
gnomeusers = group.members.list(all=True)
gnomeusers_dict = {}
projects = group.projects.list(all=True)

for user in ldapusers:
    for index, _ in enumerate(user.attributes['identities']):
        if user.attributes['identities'][index]['provider'] == 'ldapmain':
            ldapusers_dict[user.attributes['identities'][index]['extern_uid'].split(',')[0].replace('uid=', '')] = user.attributes['id']

for person in gnomeusers:
    # Slower but needed as group.member.get(id) does not return all the attributes we need
    user = gl.users.get(person.attributes['id'])
    for index, _ in enumerate(user.attributes['identities']):
        if user.attributes['identities'][index]['provider'] == 'ldapmain':
            gnomeusers_dict[user.attributes['identities'][index]['extern_uid'].split(',')[0].replace('uid=', '')] = user.attributes['id']

for username, id in ldapusers_dict.iteritems():
    ssh_key = glu.get_attributes_from_ldap(username, 'ipaSshPubKey')

    if ssh_key is not None:
        user = gl.users.get(id)
        try:
            user.keys.create({'title': 'Imported from account.gnome.org', 'key': ssh_key})

            print 'Key for username with id %i has been added' % id
        except gitlab.exceptions.GitlabCreateError as e:
            if e.response_code == 400:
                pass

        try:
            # An else statement would be ideal here in terms of performances but
            # not all the users that logged in into Gitlab using the LDAP auth
            # backend are part of the gnomecvs group while the opposite is always true
            # as gnomecvs is effectively an LDAP POSIX group.
            if username in gnomecvs_members:
                group.members.create({'user_id': id,
                                      'access_level': gitlab.DEVELOPER_ACCESS})

                print 'Username with id %i has been added to the GNOME group' % id
        except gitlab.exceptions.GitlabCreateError as e:
            if e.response_code == 409:
                pass

for username, id in gnomeusers_dict.iteritems():
    if username not in gnomecvs_members:
        # Hardcode the list of GNOME group owners here
        if username in ('csoriano-gitlab-admin-account', 'gitlab-bugzilla-migration'):
            pass
        else:
            group.members.delete(id)

            print 'Username with id %i has been removed from the GNOME group' % id

maints = dict()
for project in projects:
    project_name = project.attributes['path']
    uids = []

    try:
        nodes = semi_rdf.read_rdf('https://gitlab.gnome.org/GNOME/%s/raw/master/%s.doap' % (project_name, project_name))
    except SAXParseException:
        nodes = ''

    for node in nodes:
      if node.name != (DOAP, "Project"):
        continue

      for maint in node.find_properties((DOAP, u'maintainer')):
        if not isinstance(maint, semi_rdf.Node):
          continue

        uid = maint.find_property((GNOME, u'userid'))
        if not isinstance(uid, basestring):
          continue

        uid = str(uid)
        uids.append(uid)

        maints[project_name] = uids

for project in maints:
    proj = gl.projects.get('GNOME/%s' % project)
    for user in maints[project]:
        if user in gnomeusers_dict:
            userid = gnomeusers_dict[user]
            try:
                proj.members.create({'user_id': userid, 'access_level':
                                     gitlab.MASTER_ACCESS})

                print 'Landed master level access to %s against repository %s' % (user, project)
            except gitlab.exceptions.GitlabCreateError as e:
                if e.response_code == 409:
                    member = proj.members.get(userid)
                    if member.attributes['access_level'] != 40:
                        proj.members.delete(userid)
                        proj.members.create({'user_id': userid, 'access_level':
                                         gitlab.MASTER_ACCESS})

                        print 'Landed master level access to %s against repository %s' % (user, project)

    members = proj.members.list()
    members_dict = {}

    for member in members:
        identity_found = False
        user = gl.users.get(member.attributes['id'])

        if len(user.attributes['identities']) > 0:
            for index, _ in enumerate(user.attributes['identities']):
                provider = user.attributes['identities'][index]['provider']
                if provider == 'ldapmain':
                    members_dict[user.attributes['identities'][index]['extern_uid'].split(',')[0].replace('uid=', '')] = user.attributes['id']
                    identity_found = True

            if not identity_found:
                members_dict[user.attributes['username']] = user.attributes['id']
        else:
            members_dict[user.attributes['username']] = user.attributes['id']

    for member in members_dict:
        if member not in maints[project]:
            _member = proj.members.get(members_dict[member])
            if _member.attributes['access_level'] == 40:
                proj.members.delete(members_dict[member])

                print 'Dropped master level access to %s against repository %s as maintainer entry is missing on the DOAP file' % (member, project)
            elif _member.attributes['access_level'] == 20:
                pass
            else:
                proj.members.delete(members_dict[member])

                print 'Dropped level access %s, this means user %s was added manually on project %s, that is not necessary as permissions are inherited from the GNOME group by default' % (_member.attributes['access_level'], member, project)
