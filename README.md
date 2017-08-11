
## Financials
This code parses EDGAR for XBRL financial statement data, and writes the 
following items to financials/data/[quarter]:

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
| bs_assets | Assets |
| bs_cash | Cash |
| bs_currentassets | Current assets |
| bs_ppenet | Net property, plant and equipment |
| bs_ppegross | Gross property, plant and equipment |
| bs_currentliabilities | Current liabilities |
| bs_longtermdebt | Long term debt |
| bs_equity | Equity |
| is_sales | Sales (revenue) |
| is_cogs | Cost of goods sold |
| is_grossprofit | Gross profit |
| is_research | Research and development expense |
| is_sga | Sales, general and administrative expenses |
| is_opexpenses | Operating expenses |
| is_ebitda | EBITDA |
| is_incometax | Income taxes paid |
| is_netincome | Net income |
| is_opincome | Operating income |
| cf_operating | Net cash provided by/used in operating activities |
| cf_depreciation | Depreciation |
| cf_investing | Net cash provided by/used in investing activities |
| cf_ppe | Payments to acquire property, plant and equipment |
| cf_financing | Net cash provided by/used in financing activities |
| cf_dividends | Payments of dividends |
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

