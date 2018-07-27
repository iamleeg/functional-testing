#
# Pints functional testing module.
#
# This file is part of Pints Functional Testing.
#  Copyright (c) 2017-2018, University of Oxford.
#  For licensing information, see the LICENSE file distributed with the Pints
#  functional testing software package.
#
from __future__ import absolute_import, division
from __future__ import print_function, unicode_literals

import os
import re
import sys
import time
import logging


# Set up logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.info('Loading Pints Functional Testing.')


# Define directories to use
DIR_PFUNK = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DIR_LOG = os.path.join(DIR_PFUNK, 'logs')
DIR_RESULT = os.path.join(DIR_PFUNK, 'results')
DIR_PLOT = os.path.join(DIR_PFUNK, 'plot')
DIR_PINTS_REPO = os.path.join(DIR_PFUNK, 'pints')
DIR_PINTS_MODULE = os.path.join(DIR_PINTS_REPO, 'pints')


# Ensure log- and result directories exist
if not os.path.isdir(DIR_LOG):
    log.info('Creating log dir: ' + DIR_LOG)
    os.makedirs(DIR_LOG)
if not os.path.isdir(DIR_RESULT):
    log.info('Creating result dir: ' + DIR_RESULT)
    os.makedirs(DIR_RESULT)
if not os.path.isdir(DIR_PLOT):
    log.info('Creating plot dir: ' + DIR_PLOT)
    os.makedirs(DIR_PLOT)


# Date formatting
DATE_FORMAT = '%Y-%m-%d-%H:%M:%S'

def date(when=None):
    if when:
        return time.strftime(DATE_FORMAT, when)
    else:
        return time.strftime(DATE_FORMAT)


# Test and plot name format (in regex form)
NAME_FORMAT = re.compile(r'^[a-zA-Z]\w*$')


# Python version
PYTHON_VERSION = sys.version.replace('\n', '')


#
# Start importing sub modules
#

# Always import io and git
from . import io
from . import git


# Pints version and repo
PINTS_COMMIT = PINTS_VERSION = None

def prepare_pints():
    """ Makes sure Pints is up to date. Should be run before testing. """
    global PINTS_COMMIT, PINTS_VERSION

    # Ensure pints is up to date
    if PINTS_COMMIT is None:
        git.pints_refresh()
        PINTS_COMMIT = git.pints_hash()

    # Get Pints version from local repo
    if PINTS_VERSION is None:
        sys.path.insert(0, DIR_PINTS_REPO)
        import pints
        assert pints.__path__[0] == DIR_PINTS_MODULE
        PINTS_VERSION = pints.version(formatted=True)


# Import test class
from .test import FunctionalTest

# Import plot classes
from .plot import FunctionalTestPlot, SingleTestPlot

