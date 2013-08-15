#!/usr/bin/python
# This script will parse the f-19-key-milestones.tjx file and retrieve three relevant
# dates: Alpha Release Public Availability, Beta Release Public Availability and Final Release Public Availability.
# Author: Andrea Veri <av@gnome.org>

from xml.etree import ElementTree
import requests
import sys
import gzip
import os

# The old good urllib way.
# import urllib
# urllib.urlretrieve('http://fedorapeople.org/groups/schedule/f-19/f-19-key-milestones.tjx', 'f-19-key-milestones.tjx')

r = requests.get('http://fedorapeople.org/groups/schedule/f-19/f-19-key-milestones.tjx')

if r.status_code == 404:
	print "Can't download the file, are you sure it exists?"
	sys.exit()
else:
	with open("f-19-key-milestones.tjx", "wb") as data:
   		 data.write(r.content)
	localFile = 'f-19-key-milestones.tjx'

# We could have done the same as above with subprocess.
#    import subprocess
#    with open('f-19-key-milestones.xml', 'w') as output:
#         server = subprocess.Popen(['zcat', 'f-19-key-milestones.tjx'], stdout=output)
#         server.communicate()

tree = ElementTree.parse(localFile)
root = tree.getroot()
for elem in tree.iterfind('taskList/task/task/task/task[@id="f19.TestingPhase.alpha.alpha_drop"]/taskScenario/start'):
	alpha_tag = elem.tag
        alpha_attr = elem.attrib

for elem in tree.iterfind('taskList/task/task/task/task[@id="f19.TestingPhase.beta.beta_drop"]/taskScenario/start'):
	beta_tag = elem.tag
        beta_attr = elem.attrib

for elem in tree.iterfind('taskList/task/task/task[@id="f19.LaunchPhase.final"]/taskScenario/start'):
	final_tag = elem.tag
        final_attr = elem.attrib

def sanitize_output(element):
	string = ' '.join('{0}{1}'.format(key, val) for key, val in sorted(element.items()))
	blacklist = ["humanReadable"]
	for i in range(len(blacklist)):
		string = string.replace(blacklist[i],"")
	blacklist = ["-"]
	for i in range(len(blacklist)):
		string = string.replace(blacklist[i]," ")
	return string

alpha = sanitize_output(alpha_attr)
beta = sanitize_output(beta_attr)
final = sanitize_output(final_attr)

output = """Release schedule dates:
            Alpha Release Public Availability: %s
            Beta Release Public Availability: %s
	    Final Release Public Availability (GA): %s""" % (alpha, beta, final)

print output
