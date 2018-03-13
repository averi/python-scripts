#!/usr/bin/python

class Gnome_ldap_utils:

    def __init__(self, LDAP_GROUP_BASE, LDAP_HOST, LDAP_USER_BASE, LDAP_USER, LDAP_PASSWORD):
        import ldap
        import sys

        self.LDAP_GROUP_BASE = LDAP_GROUP_BASE
        self.LDAP_USER_BASE = LDAP_USER_BASE
        self.LDAP_USER = LDAP_USER
        self.LDAP_PASSWORD = LDAP_PASSWORD
        self.LDAP_HOST = LDAP_HOST

        try:
            self.conn = ldap.open(self.LDAP_HOST)
            self.conn.simple_bind(self.LDAP_USER, self.LDAP_PASSWORD)
        except ldap.LDAPError, e:
            print >>sys.stderr, e
            sys.exit(1)

    def get_group_from_ldap(self, group):
        import ldap.filter

        filter = ldap.filter.filter_format('(&(objectClass=posixGroup)(cn=%s))', (group, ))
        results = self.conn.search_s(self.LDAP_GROUP_BASE, ldap.SCOPE_SUBTREE, filter, ('member', ))

        members = set()

        for _, attr in results:
            for userid in attr['member']:
                splitentry = userid.split(',')
                singleentry = splitentry[0]
                splitteduid = singleentry.split('=')
                uid = splitteduid[1]

                members.add(uid)

        return members

    def get_attributes_from_ldap(self, uid, attr, *attrs):
        import ldap.filter

        results = []

        filter = ldap.filter.filter_format('(uid=%s)', (uid, ))
        if len(attrs) > 0:
            attrs = list(attrs)
            attrs.insert(0, 'uid')
            attrs.insert(1, attr)
            _result = self.conn.search_s(self.LDAP_USER_BASE, ldap.SCOPE_SUBTREE, filter, (attrs))

            for arg in attrs:
                try:
                    results.append(_result[0][1][arg][0])
                except KeyError:
                    results.append(None)
        else:
            result = self.conn.search_s(self.LDAP_USER_BASE, ldap.SCOPE_SUBTREE, filter, ('uid', attr, ))

        if len(results) > 0:
            return results
        elif len(result) > 0:
            try:
                return result[0][1][attr][0]
            except KeyError:
                return None
        else:
            return None

    def get_uids_from_group(self, group, excludes=[]):
        people = self.get_group_from_ldap(group)

        if len(excludes) > 0:
            for person in excludes:
                people.discard(person)

        return people

    def replace_ldap_password(self, userid, password):
        import ldap

        replace_password = [(ldap.MOD_REPLACE, 'userPassword', password)]
        self.conn.modify_s('uid=%s,%s' % (userid, self.LDAP_USER_BASE), replace_password)

    def add_user_to_ldap_group(self, userid, group):
        import ldap

        add_members = [(ldap.MOD_ADD, 'member', 'uid=%s,%s' % (userid, self.LDAP_USER_BASE))]
        self.conn.modify_s('cn=%s,%s' % (group, self.LDAP_GROUP_BASE), add_members)

    def remove_user_from_ldap_group(self, userid, group):
        import ldap

        remove_members = [(ldap.MOD_DELETE, 'member', 'uid=%s,%s' % (userid, self.LDAP_USER_BASE))]
        self.conn.modify_s('cn=%s,%s' % (group, self.LDAP_GROUP_BASE), remove_members)

    def add_or_update_description(self, userid, comment, add=False, update=False):
        import sys
        import ldap

        if add and not update:
            update_comment = [(ldap.MOD_ADD, 'description', comment)]
            self.conn.modify_s('uid=%s,%s' % (userid, self.LDAP_USER_BASE), update_comment)
        elif update and not add:
            update_comment = [(ldap.MOD_REPLACE, 'description', comment)]
            self.conn.modify_s('uid=%s,%s' % (userid, self.LDAP_USER_BASE), update_comment)
        else:
            sys.exit(1)
