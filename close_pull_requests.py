#! /usr/bin/env python

import argparse
import ConfigParser
import github
import yaml
import sys
import os

from urllib2 import urlopen, Request
import simplejson as json
import string

from optparse import OptionParser

usage = "usage: %prog [options]"
parser = OptionParser(usage)

parser.add_option("-v", "--verbose",
                  action="store_true", dest="verbose", default=False,
                  help="Turn on debugging output")

(options, args) = parser.parse_args()


config_file = '/home/admin/secret/github.oauth'
projects_yaml = '/tmp/repositories.yaml'
github_url = 'https://api.github.com/orgs/GNOME/repos?per_page=100'
excludes_file = '/home/admin/github.excludes'
github_organization = 'gnome'
repositories = []

if not os.path.isfile(excludes_file):
    print 'No excludes file could be found at %s' % excludes_file
    sys.exit(1)
else:
    execfile(excludes_file)

GITHUB_SECURE_CONFIG = os.environ.get('GITHUB_SECURE_CONFIG',
                                      '%s' % config_file)

secure_config = ConfigParser.ConfigParser()
secure_config.read(GITHUB_SECURE_CONFIG)

MESSAGE = """Thank you for contributing to %(project)s!

%(project)s uses Bugzilla for code review.

If you have never contributed to GNOME before make sure you have read the
getting started documentation:
http://www.gnome.org/get-involved

Otherwise please visit
https://wiki.gnome.org/Newcomers
and follow the instructions there to upload your change to Bugzilla.
"""

TEMPLATE = string.Template("""
- project: $project_name
  options:
    - $has_pull_requests
""")


def fetch_repositories(url):
    url = str(url)

    if not os.path.isfile(config_file):
        print 'No configuration file could be found at %s' % config_file
        sys.exit(1)

    if secure_config.has_option("github", "oauth_token"):
        auth_token = secure_config.get("github", "oauth_token")
    else:
        print 'Make sure %s has a github section and an oauth_token key/value pair' % config_file
        sys.exit(1)

    req = Request(url)
    req.add_header('Authorization', 'token %s' % auth_token)    
    response = urlopen(req)
    content = response.read()
    parsed_json = json.loads(content)

    the_page = response.info().getheader('link')
    next_url = the_page.split(';')[0].replace('<','').replace('>','')
    is_last = the_page.split(';')[1].split(',')[0].replace('rel=','').replace('"','').replace(' ','')

    for repository in parsed_json:
        repo_name = repository['name']
        if options.verbose:
            print 'Appending %s to the repositories list' % repo_name
   
        repositories.append(repo_name)

    if is_last == 'next':
        url = next_url

        fetch_repositories(url)

    with open('%s' % projects_yaml, 'w') as repo_list:
        for repo in repositories:
            repo = str(repo)

            if repo in excludes:
                has_pull_requests='has-no-pull-requests'
                repo_list.write(TEMPLATE.substitute(project_name = repo, has_pull_requests=has_pull_requests))
            else:
                has_pull_requests='has-pull-requests'
                repo_list.write(TEMPLATE.substitute(project_name = repo, has_pull_requests=has_pull_requests))


def close_pull_requests():

    pull_request_text = MESSAGE

    ghub = github.Github(secure_config.get("github", "oauth_token"))
    org = ghub.get_organization(github_organization)

    with open('%s' % projects_yaml, 'r') as yaml_file:
        for section in yaml.load(yaml_file):
            project = section['project']

            if 'options' in section and section['options'][0] == 'has-no-pull-requests':
                if options.verbose:
                    print 'EXCLUDES: Project %s has been excluded' % project

            # Make sure we're supposed to close pull requests for this project
            if 'options' in section and section['options'][0] == 'has-pull-requests':
                repo = org.get_repo(project)

                # Close each pull request
                pull_requests = repo.get_pulls("open")
                for req in pull_requests:
                    vars = dict(project=project)
                    issue_data = {"url": repo.url + "/issues/" + str(req.number)}
                    issue = github.Issue.Issue(requester=req._requester,
                                               headers={},
                                               attributes=issue_data,
                                               completed=True)
                    issue.create_comment(pull_request_text % vars)
                    req.edit(state="closed")

if __name__ == "__main__":
    fetch_repositories(github_url)

    close_pull_requests()
