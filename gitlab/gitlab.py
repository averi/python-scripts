#!/usr/bin/python

class Gitlab:
    def __init__(self, api_url, api_token, api_version=4):
        import sys

        self.api_url = api_url
        self.api_token = api_token
        self.headers = {'PRIVATE-TOKEN': self.api_token}

        if api_version == 4:
            self.api_url = 'https://%s/api/v4' % self.api_url
        elif api_version == 3:
            self.api_url = 'https://%s/api/v3' % self.api_url
        else:
            print 'api_version is either 4 or 3'
            sys.exit(1)

    def list_ldap_users(self, api_call='users?per_page=200', users={}):
        import urllib2
        import json

        self.api_call = api_call

        url = '%s/%s' % (self.api_url, self.api_call)
        req = urllib2.Request(url, headers=self.headers)

        response = urllib2.urlopen(req)
        data = json.load(response)

        the_page = response.info().getheader('link')
        next_url = the_page.split(';')[0].replace('<','').replace('>','')
        is_last = the_page.split(';')[1].split(',')[0].replace('rel=','').replace('"','').replace(' ','')

        if is_last != 'next':
            is_last  = the_page.split(';')[2].split(',')[0].replace('rel=','').replace('"','').replace(' ','')
            next_url = the_page.split(';')[1].split(',')[1].replace('<','').replace('>','').replace(' ', '')

        for user in data:
            for index, _ in enumerate(user['identities']):
                 if user['identities'][index]['provider'] == 'ldapmain':
                     users[user['id']] = user['identities'][index]['extern_uid'].split(',')[0].replace('uid=', '')

        if is_last == 'next':
            url = next_url
            url = url.strip(self.api_url)

            self.list_ldap_users(url)

        return users

    def add_ssh_keys(self, ssh_key, user_id):
        import urllib2
        import json

        title = 'Imported from account.gnome.org'
        ssh_key_dump = json.dumps({'id': user_id, 'key': ssh_key, 'title': title })
        self.headers['Content-Type'] = 'application/json'
        url = self.api_url + '/users/%i/keys' % user_id

        req = urllib2.Request(url, ssh_key_dump, headers=self.headers)

        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError:
            print 'Key for username with id %i is registered already' % (user_id)

    def list_group_members(self, group, members=[]):
        import urllib2
        import json

        url = self.api_url + '/groups/%s/members' % group
        req = urllib2.Request(url, headers=self.headers)
        response = urllib2.urlopen(req)
        data = json.load(response)

        for member in data:
            url = self.api_url + ('/users?username=%s' % member['username'])
            req = urllib2.Request(url, headers=self.headers)
            response = urllib2.urlopen(req)
            f = json.load(response)

            for user in f:
                if user['username'] == 'root':
                    pass
                else:
                    for index, _ in enumerate(user['identities']):
                         if user['identities'][index]['provider'] == 'ldapmain':
                            members.append(user['identities'][index]['extern_uid'].split(',')[0].replace('uid=', ''))

        return members
