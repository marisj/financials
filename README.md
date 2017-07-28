
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
| bs.assets | Assets |
| bs.cash | Cash |
| bs.currentassets | Current assets |
| bs.ppenet | Net property, plant and equipment |
| bs.ppegross | Gross property, plant and equipment |
| bs.currentliabilities | Current liabilities |
| bs.longtermdebt | Long term debt |
| bs.equity | Equity |
| is.sales | Sales (revenue) |
| is.cogs | Cost of goods sold |
| is.grossprofit | Gross profit |
| is.research | Research and development expense |
| is.sga | Sales, general and administrative expenses |
| is.opexpenses | Operating expenses |
| is.ebitda | EBITDA |
| is.incometax | Income taxes paid |
| is.netincome | Net income |
| is.opincome | Operating income |
| cf.operating | Net cash provided by/used in operating activities |
| cf.depreciation | Depreciation |
| cf.investing | Net cash provided by/used in investing activities |
| cf.ppe | Payments to acquire property, plant and equipment |
| cf.financing | Net cash provided by/used in financing activities |
| cf.dividends | Payments of dividends |
| cf.cashchange | Change in cash and cash equivalents |


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

