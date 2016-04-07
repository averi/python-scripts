#!/usr/bin/python

import os
import ConfigParser
import subprocess
import shlex
import shutil
import sys
from optparse import OptionParser

usage = "usage: %prog -c configuration_file [-i/-l] [-i/package_name]"
parser = OptionParser(usage)

parser.add_option("-c", "--config-file",
                  action="store", type ="string", dest="config_file",
                  help="Specify a configuration file"
                  )
parser.add_option("-i", "--install",
                  action="store_true", dest="install",
                  help="Install and sign a package, requires -p"
                  )
parser.add_option("-l", "--list-signatures",
                  action="store_true", dest="list_signatures",
                  help="List RPMs and their signature status on reposdir and subdirectories"
                  )

(options, args) = parser.parse_args()


config = ConfigParser.ConfigParser()

if len(sys.argv) == 1:
    print 'Not enough parameters given, try --help'
    sys.exit(1)

if not options.config_file:
    parser.error('No configuration file specified')
    sys.exit(1)

try:
    config.read(options.config_file)

    gpghome = config.get('main', 'gpghome')
    gpgkeyid = config.get('main', 'gpgkeyid')
    gpgname = config.get('main', 'gpgname')
    reposdir = config.get('main', 'reposdir')
except ConfigParser.Error:
    print "An incorrect configuration file was specified. Make sure the file exists and has a [main] section on its header"
    sys.exit(1)

def list_rpm_files_signature():
    if len(args) > 0:
        print 'No need to specify a package name with the -l option, check --help'
        sys.exit(1)

    for repo in ['el5', 'el6', 'el7']:
        for arch in ['i386', 'x86_64', 'noarch', 'SRPMS']:
            for _file in os.listdir(os.path.join(reposdir, repo, arch)):
                if _file.endswith('.rpm'):
                    if check_valid_signature(os.path.join(reposdir, repo, arch, _file)) is False:
                        print '  %s - NOT SIGNED' % (os.path.join(reposdir, repo, arch, _file)) + '\n'
                    else:
                        print '  %s - SIGNED' % (os.path.join(reposdir, repo, arch, _file)) + '\n'

def check_valid_signature(package):
    command = 'rpmsign -K %s' % package
    command = shlex.split(command)
    rpm_qpi = subprocess.Popen(command, stdout=subprocess.PIPE)
    rpm_qpi.wait()

    for line in rpm_qpi.stdout.readlines():
        splitted_line = line.split(' ')
        if ('NOT' or 'NON') in splitted_line:
            return False

def sign_rpm(package):
    package_name = args[0]

    if not os.path.isfile('/usr/bin/rpmsign'):
        print 'The rpmsign binary is not installed, please install the rpm-sign package'
        sys.exit(1)

    query_user = raw_input("Do you want to sign the %s package? Type YES or NO: " % package_name)

    if query_user == 'YES' or 'yes':

        command = 'rpm -D "%%_signature gpg" -D "%%_gpg_path %s" -D "%%_gpg_name %s" -D "%%__gpg /usr/bin/gpg" --resign %s' % (gpghome, gpgname, package)
        command = shlex.split(command)
        sign = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        sign.wait()

        if sign.returncode == 0:
            print 'Package has been signed with the following key: %s' % gpgkeyid
            print "Run 'cobbler reposync' as root on combobox to regenerate the repositories metadata"
        else:
            error = sign.stderr.readlines()
            report_error = error[1:2]
            print '\n' + 'Package has not been signed, error is: %s' % report_error[0]
    elif query_user == 'NO' or 'no':
        print '\n' + 'The signature of %s has been ABORTED' % filename + '\n'
    else:
        print 'Neither "YES" or "NO" were entered, aborting'

def install_package():
    if len(args) == 0:
        print 'No package name specified, check --help'
        sys.exit(1)
    elif len(args) == 1:
        package = args[0]
    else:
        print 'Please list one package at a time'

    packagename_splitted = package.split('.')

    for repo in ['el5', 'el6', 'el7']:
        for arch in ['i386', 'x86_64', 'noarch', 'SRPMS']:
            if repo in packagename_splitted:
                if arch in packagename_splitted:
                    dest = os.path.join(reposdir, repo, arch)

                    if os.path.isdir(dest) and os.path.isfile(package):
                        print 'Copying %s to %s' % (package, dest) + '\n'
                        shutil.copy(package, dest)

                        newdest = os.path.join(dest, package)
                        if os.path.isfile(newdest):
                            print '%s has been copied, now signing it' % package + '\n'
                            sign_rpm(newdest)
                    else:
                        print "Either %s or the RPM file you want to install couldn't be found" % dest
                        sys.exit(1)

def main():

    if options.install:
        install_package()

    if options.list_signatures:
        list_rpm_files_signature()

if __name__ == "__main__":
    main()
