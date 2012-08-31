#!/usr/bin/env python
import sys
from os.path import dirname, abspath, splitext
from os import listdir
from optparse import OptionParser

where_am_i = dirname(abspath(__file__))

sys.path.insert(0, where_am_i)

# adding eggs to path
files = listdir(where_am_i)

for file in files:
    name, extension = splitext(file)
    if extension == ".egg":
        sys.path.insert(0, file)


from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASE_ENGINE='sqlite3',
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'TEST_NAME': ':memory:',
            },
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
        ],
        ROOT_URLCONF='',
        DEBUG=False,
    )

from django_nose import NoseTestSuiteRunner


def runtests(*test_args, **kwargs):
    if not test_args:
        test_args = ['tests']

    kwargs.setdefault('interactive', False)

    test_runner = NoseTestSuiteRunner(**kwargs)

    failures = test_runner.run_tests(test_args)
    sys.exit(failures)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--verbosity', dest='verbosity', action='store', default=1, type=int)
    parser.add_options(NoseTestSuiteRunner.options)
    (options, args) = parser.parse_args()

    runtests(*args, **options.__dict__)
