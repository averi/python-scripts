#!/usr/bin/python

import os
import sys
import pwd
import grp
import time
from optparse import OptionParser

usage = "usage: %prog [-f|-d] [options] path"
parser = OptionParser(usage)


parser.add_option("-f", "--files",
                  action="store_true", dest="files",
                  help="Provides a list of files on the specified path"
                  )
parser.add_option("-d", "--dirs",
                  action="store_true", dest="dirs",
                  help="Provides a list of directories on the specified path"
                  )
parser.add_option("-l", "--long-list",
                  action="store_true", dest="long_list",
                  help="Shows owner, group, filesize, mode for each file or directory listed."
                  " Requires either -f or -d."
                  )
parser.add_option("--fpath",
                  action="store_true", dest="full_path",
                  help="Specifies whether an absolute path should be printed. "
                  " Requires either -f or -d."
                  )
parser.add_option("--hidden",
                  action="store_true", dest="hidden",
                  help="Shows hidden files, requires either -f or -d"
                  )

(options, args) = parser.parse_args()

if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)

def pyls():
    if len(args) == 0:
        path = os.getcwd()
    elif len(args) == 1:
        path = args[0]
    else:
        print 'More than one path specified, exiting'
        sys.exit(1)

    # Return the optarse help listing when --hidden and
    # -l are included as single options on the command line
    if (options.hidden or options.long_list or options.full_path) and not (options.files or options.dirs):
        parser.error('The --hidden, -l and --fpath options require either -f or -d, check --help')
        sys.exit(1)

    directories_list = []
    hidden_directories_list = []
    files_list = []
    hidden_files_list = []

    try:
        files = os.listdir(path)
    except OSError as e:
        print 'FAILURE, wrong path specified on the command line: OS Error n. {0}: {1}'.format(e.errno, e.strerror)
        sys.exit(1)

    if options.dirs and not options.files:
        for file in files:
            if os.path.isdir(os.path.join(path, file)) and not options.hidden:
                if not file.startswith('.'):
                    directories_list.append(file)
            elif os.path.isdir(os.path.join(path, file)) and options.hidden:
                if file.startswith('.'):
                    hidden_directories_list.append(file)

        if not options.hidden:
            for file in directories_list:
                if options.long_list and not options.full_path:
                    print_file_stats(path, file)
                if options.long_list and options.full_path:
                    print_file_stats(path, file, full_path=True)
                elif not (options.long_list or options.full_path):
                    print file

        if options.hidden:
            for file in hidden_directories_list:
                if options.long_list and not options.full_path:
                    print_file_stats(path, file)
                elif options.long_list and options.full_path:
                    print_file_stats(path, file, full_path=True)
                elif options.full_path and not options.long_list:
                    print os.path.join(path, file)
                else:
                    print file

    elif options.files and not options.dirs:
        try:
            if len(files) == 0:
                print 'No files were found on path %s' % path
                sys.exit(1)
            else:
                for file in files:
                    fpath = os.path.join(path, file)

                    if os.path.isfile(fpath) and not is_hidden(file):
                        files_list.append(file)
                    elif os.path.isfile(fpath) and is_hidden(file):
                        hidden_files_list.append(file)

                if options.hidden:
                    for file in hidden_files_list:
                        if options.long_list and not options.full_path:
                            print_file_stats(path, file)
                        elif options.long_list and options.full_path:
                            print_file_stats(path, file, full_path=True)
                        elif options.full_path and not options.long_list:
                            print os.path.join(path, file)
                        else:
                            print file
                elif not options.hidden and options.full_path and not options.long_list:
                    for file in files_list:
                        print os.path.join(path, file)
                elif not options.hidden and (options.full_path and options.long_list):
                    for file in files_list:
                            print_file_stats(path, file, full_path=True)
                elif not options.hidden:
                    for file in files_list:
                        if options.long_list:
                            print_file_stats(path, file)
                        else:
                            print file
        except OSError as e:
            print 'FAILURE: OS Error n. {0}: {1}'.format(e.errno, e.strerror)
            sys.exit(1)
    elif not (options.files or options.dirs):
        print "No -f or -d flags specified, check --help for more details"
    else:
        print "You can't mix the -f and -d flags, check --help for more information"
        sys.exit(1)

def is_hidden(filename):
    if filename.startswith('.'):
        return True

def print_file_stats(path, filename, full_path=False):

    stat_details = os.stat(os.path.join(path, filename))

    uid = stat_details.st_uid
    gid = stat_details.st_gid
    filesize = stat_details.st_size
    mode = stat_details.st_mode
    lastmodified = time.gmtime(stat_details.st_mtime)
    mtime = time.strftime('%d %b %H.%M', lastmodified)

    username = pwd.getpwuid(uid)[0]
    group = grp.getgrgid(gid)[0]

    if os.path.isdir(os.path.join(path, filename)):
        _hard_links = hard_links(os.path.join(path, filename))
        mode = oct(mode)[3:]

        if full_path == False:
            print '%s %s %s %s %s %s %s' % (mode, _hard_links, username, group, filesize, mtime, filename)
        else:
            print '%s %s %s %s %s %s %s' % (mode, _hard_links, username, group, filesize, mtime, os.path.join(path, filename))            
    else:
        mode = oct(mode)[4:]

        if full_path == False:
            print '%s %s %s %s %s %s' % (mode, username, group, filesize, mtime, filename)
        else:
            print '%s %s %s %s %s %s' % (mode, username, group, filesize, mtime, os.path.join(path, filename))

    return username, group, filesize, mode, mtime

# This function is only meant for directory listings.
# Hard links (second field on ls -l output) is a sum
# of the subdirectories of the target plus the target itself
# and its parent directory.
def hard_links(path):

    total = []

    for subdir in os.listdir(os.path.join(path)):
        if os.path.isdir(os.path.join(path, subdir)):
            total.append(subdir)

    return len(total) + 2

pyls()
