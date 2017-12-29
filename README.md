## Financials
This code writes the following financial statement items to financials/data/[quarter]:

| Field | Description |
| :--- | :--- |
| focus | Fiscal year/period focus |
| ticker | Trading symbol |
| cik | SEC Central Index Key |
| zip | 5-digit ZIP code |
| form | SEC form |
| formdate | Period end date (balance sheet date) |
| filedate | Filing date |
| acceptance | Acceptance datetime (when the filing was made public) |
| accession | SEC accession number |
| name | Company name |
| bs_assets | Total assets |
| bs_cash | Cash |
| bs_currentassets | Current assets |
| bs_ppenet | Net property, plant and equipment |
| bs_ppegross | Gross property, plant and equipment |
| bs_currentliabilities | Current liabilities |
| bs_liabilities | Total liabilities |
| bs_longtermdebtnoncurrent | Long term debt noncurrent |
| bs_longtermdebtcurrent | Long term debt current |
| bs_longtermdebt | Long term debt and capital lease obligations |
| bs_equity | Stockholders' Equity |
| is_sales | Sales (revenue) net |
| is_cogs | Cost of goods sold |
| is_grossprofit | Gross profit |
| is_research | Research and development expense |
| is_sga | Sales, general and administrative expenses |
| is_opexpenses | Operating expenses |
| is_incometax | Income taxes |
| is_netincome | Net income |
| is_opincome | Operating income |
| cf_operating | Net cash provided by/used in operating activities |
| cf_depreciation | Depreciation |
| cf_depreciationamortization | Depreciation and Amortization |
| cf_investing | Net cash provided by/used in investing activities |
| cf_ppe | Gain/loss on sale of property, plant and equipment |
| cf_financing | Net cash provided by/used in financing activities |
| cf_dividends | Cash dividends |
| cf_cashchange | Change in cash and cash equivalents |


## Usage
```
from financials.xbrl import XBRL

XBRL().add_quarter('2009/QTR1')
```
or
```
bash pull_quarter.sh 2009/QTR1
```

## Dependencies
lxml


## License
BSD

