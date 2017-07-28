"""
    pull_quarter.py
    ===============

    Usage:

    >>> python pull_quarter.py 2009/QTR1
"""
import sys

from financials.xbrl import XBRL

XBRL().add_quarter(sys.argv[1])