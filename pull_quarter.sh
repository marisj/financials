#!/bin/bash
# =========================================================================
#    
#         FILE:  pull_quarter.sh
# 
#        USAGE:  pull_quarter.sh 2009/QTR1
#
#  DESCRIPTION:  Parses quarterly EDGAR index for XBRL financial statements.
#                Saves data to finanicals/data/.
#                Saves previous periods to financials/data/history/.         
#    
#      OPTIONS:  ---
#        NOTES:  ---
#      CREATED:  2017-07-27
#     REVISION:  ---
#
# =========================================================================
quarter=$1
python pull_quarter.py ${quarter}
