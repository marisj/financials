#!/bin/bash
# =========================================================================
#    
#         FILE:  build_annual.sh
# 
#        USAGE:  build_annual.sh [YYYY] [outputpath]
#
#  DESCRIPTION:  Parses quarterly output files for annual data.
#                Saves annual data to outputpath.      
#    
#      OPTIONS:  ---
#        NOTES:  ---
#      CREATED:  2017-07-30
#     REVISION:  ---
#
# =========================================================================
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Missing parameters"
    exit
fi

year=$1
outputpath=$2
datapath="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd )"/data

rm -f $outputpath
echo "focus|ticker|cik|zip|form|formdate|filedate|acceptance|accession|\
name|bs_assets|bs_cash|bs_currentassets|bs_ppenet|bs_ppegross|\
bs_currentliabilities|bs_liabilities|bs_longtermdebtnoncurrent|\
bs_longtermdebtcurrent|bs_equity|is_sales|is_cogs|\
is_grossprofit|is_research|is_sga|is_opexpenses|is_ebitda|\
is_incometax|is_netincome|is_opincome|cf_operating|cf_depreciation|\
cf_investing|cf_financing|cf_dividends|cf_cashchange" > $outputpath

for infile in ${datapath}/${year}*Q*; do
    awk -F\| '(index($5, "10-K") != 0)' $infile >> $outputpath
done


