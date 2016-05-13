#!/usr/bin/python

import whois
from datetime import datetime
from sys import argv,exit

now = datetime.now()

if len(argv) < 2:
    print 'No domain specified on the command line, usage:  '
    print ''
    print '    ./check-domain.py example.net'
    exit(1)

domain = argv[1]
w = whois.whois(domain)

if (w.expiration_date and w.status) == None:
    print 'The domain does not exist, exiting...'
    exit(1)

if type(w.expiration_date) == list:
    w.expiration_date = w.expiration_date[0]
else:
    w.expiration_date = w.expiration_date

domain_expiration_date = str(w.expiration_date.day) + '/' + str(w.expiration_date.month) + '/' + str(w.expiration_date.year)

timedelta = w.expiration_date - now
days_to_expire = timedelta.days

if timedelta.days <= 60 and timedelta.days > 30:
    print 'WARNING: %s is going to expire in %s days, expiration date is set to %s' % (domain, days_to_expire, domain_expiration_date)
    exit(1)
elif timedelta.days <= 30:
    print 'WARNING: %s is going to expire in %s days, expiration date is set to %s' % (domain, days_to_expire, domain_expiration_date)
    exit(2)
else:
    print 'OK, the domain %s is expiring on %s, %s days to go. No need to renew at this moment of time' % (domain, domain_expiration_date, days_to_expire)
    exit(0)
