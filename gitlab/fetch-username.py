#!/usr/bin/python

import gitlab
import os

execfile('/home/admin/secret/gitlab_ro')

gl = gitlab.Gitlab('https://gitlab.gnome.org', GITLAB_PRIVATE_RO_TOKEN, api_version=4)

def fetch_username():

    user = os.environ['GL_USERNAME']
    user = gl.users.list(username='%s' % user)
    user = user[0]

    identity_found = False
    if len(user.attributes['identities']) > 0:
      for index, _ in enumerate(user.attributes['identities']):
          provider = user.attributes['identities'][index]['provider']
          if provider == 'ldapmain':
              username = user.attributes['identities'][index]['extern_uid'].split(',')[0].replace('uid=', '')

              identity_found = True
      if not identity_found:
              username = user.attributes['username']
    else:
              username = user.attributes['username']

    print username

fetch_username()
