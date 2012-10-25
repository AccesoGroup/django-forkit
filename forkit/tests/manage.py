#!/usr/bin/env python
import sys
import traceback
from os.path import abspath, dirname, join
from os import environ
from django.core.management import execute_manager
import imp

try:
    import settings
except ImportError, e:
    print '\033[1;33m'
    print "Apparently you don't have the file settings.py yet."
    print
    print "=" * 20
    print "original traceback:"
    print "=" * 20
    print
    traceback.print_exc(e)
    print '\033[0m'
    sys.exit(1)

sys.path.insert(0, abspath(join(dirname(__file__), "../../")))

if __name__ == "__main__":
    execute_manager(settings)