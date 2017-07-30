"""
    financials.xbrl
    ===============

    Parses 20+ key accounting terms from SEC XBRL filings.

    Balance sheet: 
        assets, cash, current assets, net ppe, gross ppe,
        current liabilities, long term debt, equity

    Income statement: 
        sales, cogs, gross profit, research, sga, operating expenses,
        ebitda, income tax, net income, operating income

    Cash flow statement:
        operating, depreciation, investing, ppe, financing,
        dividends, change in cash/cash equivalents

    copyright: (c) 2017 by Maris Jensen and Ivo Welch.
    license: BSD, see LICENSE for more details.
"""
import os
import urllib2
import datetime
from collections import defaultdict

import lxml.html
from lxml import etree

from financials.helper import *


class XBRL(object):

    def __init__(self):
        self.edgar = 'https://www.sec.gov/Archives/edgar'
        self.forms = [
            '10-K', '10-K/A', '10-KT', '10-KT/A',
            '10-Q', '10-Q/A', '10-QT', '10-QT/A']
        self.context = None
        self.filepath = os.path.join(os.path.realpath('.'), 'data')
        self.datapath = None
        self.history = None
        self.accession = None
        self.annual = None
        self.tree = None

    def get_index(self, url):
        """Returns list of [form type, description, document] for a filing
        and its exhibits.

        :param url: filing index URL
        """
        c = urllib2.urlopen(url)
        tree = lxml.html.parse(c)
        c.close()
        elem = tree.getroot().xpath('//table[@class="tableFile"]/tr')
        tmp = [[x.text_content() for x in tr.xpath('.//td')] for tr in elem]
        return [[x[3], x[1], x[2]] for x in tmp if len(x) == 5 and x[3]]

    def recreate_files(self, qtr):
        """Preps data and history files.

        :param qtr: 'YYYY/QTR2'
        """
        q = qtr.replace('/QTR', 'Q')
        self.datapath = '{}/{}'.format(self.filepath, q)
        try:
            os.remove(self.datapath)
        except OSError:
            pass
        finally:
            with open(self.datapath, 'a') as f:
                f.write('{}\n'.format('|'.join([
                    'focus', 'ticker', 'cik', 'zip', 'form', 'formdate',
                    'filedate', 'acceptance', 'accession', 'name',
                    'bs.assets', 'bs.cash', 'bs.currentassets', 'bs.ppenet', 
                    'bs.ppegross', 'bs.currentliabilities', 'bs.longtermdebt', 
                    'bs.equity', 'is.sales', 'is.cogs', 'is.grossprofit', 
                    'is.research', 'is.sga', 'is.opexpenses', 'is.ebitda', 
                    'is.incometax', 'is.netincome', 'is.opincome', 
                    'cf.operating', 'cf.depreciation', 'cf.investing',
                    'cf.ppe', 'cf.financing', 'cf.dividends', 'cf.cashchange'])))

        self.history = '{}/history/{}'.format(self.filepath, q)
        try:
            os.remove(self.history)
        except OSError:
            pass
        finally:
            with open(self.history, 'a') as f:
                f.write('{}\n'.format('|'.join([
                    'accession', 'field', 'element', 'date', 'value'])))

    def add_quarter(self, qtr):
        """Pulls XBRL financial statement links from quarterly EDGAR index.

        Usage:

        >>> XBRL().add_quarter('2009/QTR1')

        :param qtr: 'YYYY/QTR2'
        """
        self.recreate_files(qtr)
        c = urllib2.urlopen('{}/full-index/{}/xbrl.idx'.format(self.edgar, qtr))
        lines = c.read().split('\n')
        c.close()
        for line in lines[10:]:
            try:
                (cik, name, form, date, filing) = \
                    [x.strip() for x in line.strip().split('|')]
                if form in self.forms:
                    self.parse(cik, name, form, date, filing)
            except ValueError:
                with open(os.path.join(os.path.realpath('.'), 'check.txt'), 'a') as f:
                    f.write('{}\n'.format(line))

    def parse(self, cik, name, form, date, filing, return_all=False):
        """Parses XBRL instance doc. Writes data to financials/data/{quarter}.

        :param cik: SEC Central Index Key
        :param name: self-reported filer name
        :param form: SEC form
        :param date: YYYY-MM-DD
        :param filing: filing ending from index
        :param return_all: True to return list of dicts for full document
        """
        accession = filing.split('/')[-1].replace('.txt', '')
        self.accession = accession
        self.annual = True if 'K' in form else False
        index = '/'.join([self.edgar, 'data', cik, accession.replace('-', ''), 
                          ''.join([accession, '-index.htm'])])
        index_links = self.get_index(index)
        xbrl = [x[2] for x in index_links if x[0].endswith('.INS')]
        if not xbrl:
            xbrl = [x[2] for x in index_links if x[0] == 'XML'] # inline
        if not xbrl:
            with open(os.path.join(os.path.realpath('.'), 'missing.txt'), 'a') as f:
                f.write('{}\n'.format(index))
            return  
        instance = '{}/data/{}/{}/{}'.format(self.edgar, cik, 
                                             accession.replace('-', ''), 
                                             xbrl[0])
        try:
            tree = etree.parse(urllib2.urlopen(instance))
        except etree.XMLSyntaxError:
            tree = etree.parse(urllib2.urlopen(instance),
                               parser=etree.XMLParser(recover=True))

        # pull acceptance datetime and zip
        sgml = index.replace('-index.htm', '.hdr.sgml')
        c = urllib2.urlopen(sgml)
        lines = c.read()
        c.close()
        acceptance = lines.split('<ACCEPTANCE-DATETIME>')[-1].split('<')[0].strip()
        zipcode = format_zip(lines.split('<ZIP>')[-1].split('<')[0].strip())

        # build context refs dict
        defs = defaultdict(dict)
        for x in tree.iter():
            if 'id' in x.attrib:
                for xx in x.iterdescendants():
                    if xx.text and xx.text.strip() and \
                                'identifier' not in str(xx.tag):
                        key = etree.QName(xx.tag).localname.strip()
                        try:
                            possible_dt = xx.text.strip()[:10]
                            val = datetime.datetime.strptime(possible_dt, 
                                                             '%Y-%m-%d').date()
                        except ValueError:
                            val = xx.text.split(':')[-1].strip()
                        defs[x.attrib['id'].strip()][key] = val
                        if xx.attrib and xx.attrib.keys() != ['scheme']:
                            for row in xx.attrib.items():
                                key = row[1].split(':')[-1].strip()
                                val = xx.text.split(':')[-1].strip()
                                defs[x.attrib['id'].strip()][key] = val

        # return list of all elements with context
        if return_all:
            crap = []
            for x in tree.iter(tag=etree.Element):
                if x.text and x.text.strip():
                    if 'xbrl.org' and 'instance' in str(x.tag):
                        pass
                    elif not x.text.startswith('<'):
                        tag = etree.QName(x.tag).localname.strip()
                        val = x.text.split(':')[-1].strip()
                        crap.append(dict(defs[x.attrib.get('contextRef')].items() +
                                         {'tag': tag, 'val': val}.items()))
            data = [x for x in crap if x['tag'] != 'explicitMember']
            return data

        # general
        self.tree = tree
        self.context = defs
        ticker = self.pull('TradingSymbol', None, history=False)
        if ticker is not None:
            ticker = clean_ticker(ticker)
        if ticker is None:
            ticker = clean_ticker(xbrl[0].split('-')[0])
        fiscal_year = self.pull('DocumentFiscalYearFocus', None, history=False)
        fiscal_period = self.pull('DocumentFiscalPeriodFocus', None, history=False)
        if fiscal_year is not None and fiscal_period is not None:
            focus = '{}{}'.format(fiscal_year, fiscal_period)
        else:
            focus = self.datapath.split('/')[-1]
        formdate = self.pull('DocumentPeriodEndDate', None, history=False)

        # balance sheet
        bs_assets = self.pull('Assets', 'bs.assets')

        bs_cash = None 
        for key in ['Cash', 'CashAndCashEquivalentsAtCarryingValue']:
            if bs_cash is None:
                bs_cash = self.pull(key, 'bs.cash')

        bs_currentassets = self.pull('AssetsCurrent', 'bs.currentassets')

        bs_ppenet = self.pull('PropertyPlantAndEquipmentNet', 'bs.ppenet')
        
        bs_ppegross = self.pull('PropertyPlantAndEquipmentGross', 'bs.ppegross')
        
        bs_currentliabilities = self.pull('LiabilitiesCurrent', 
                                          'bs.currentliabilities')

        bs_longtermdebt = self.pull('LongTermDebt', 'bs.longtermdebt')
        if bs_longtermdebt is None:
            tmp = self.pull('LongTermDebtCurrent', None, history=False)
            tmp2 = self.pull('LongTermDebtNoncurrent', None, history=False)
            if tmp is not None and tmp2 is not None:
                bs_longtermdebt = int(tmp) + int(tmp2)
            elif tmp is not None:
                bs_longtermdebt = tmp
            elif tmp2 is not None:
                bs_longtermdebt = tmp2
        if bs_longtermdebt is None:
            tmp = self.pull('DebtInstrumentCarryingAmount', None, history=False)
            tmp2 = self.pull('DebtInstrumentUnamortizedDiscountPremiumNetAbstract',
                             None, history=False)
            if tmp is not None and tmp2 is not None:
                bs_longtermdebt = int(tmp) + int(tmp2)
            elif tmp is not None:
                bs_longtermdebt = tmp 
            elif tmp2 is not None:
                bs_longtermdebt = tmp2
            for key in ['LongtermDebtNetAlternative', 'LongTermLoansFromBank',
                        'LongTermDebtAndCapitalLeaseObligations']:
                if bs_longtermdebt is None:
                    bs_longtermdebt = self.pull(key, None, history=False)

        bs_equity = None
        for key in ['CommonStockholdersEquity', 'StockholdersEquity',
                    'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
                    'PartnersCapitalIncludingPortionAttributableToNoncontrollingInterest',
                    'PartnersCapital', 'MemberEquity', 'AssetsNet']:
            if bs_equity is None:
                bs_equity = self.pull(key, 'bs.equity')

        # income statement
        is_sales = None
        for key in ['SalesRevenueNet', 'Revenues']:
            if is_sales is None:
                is_sales = self.pull(key, 'is.sales')

        is_cogs = None
        for key in ['CostOfGoodsAndServicesSold', 'CostOfGoodsSold', 
                    'CostOfServices', 'CostOfRevenue']:
            if is_cogs is None:
                is_cogs = self.pull(key, 'is.cogs')

        is_grossprofit = self.pull('GrossProfit', 'is.grossprofit')

        is_research = None
        for key in ['ResearchAndDevelopmentExpense',
                    'ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost']:
            if is_research is None:
                is_research = self.pull(key, 'is.research')

        is_sga = self.pull('SellingGeneralAndAdministrativeExpense', 'is.sga')
        if is_sga is None:
            is_sga = self.pull('GeneralAndAdministrativeExpense', None, history=False)
            tmp = self.pull('SellingAndMarketingExpense', None, history=False)
            if is_sga is None:
                is_sga = tmp
            elif tmp is not None:
                is_sga = int(is_sga) + int(tmp)

        is_opexpenses = None
        for key in ['OperatingCostsAndExpenses', 'OperatingExpenses', 
                    'CostsAndExpenses']:
            if is_opexpenses is None:
                is_opexpenses = self.pull(key, 'is.opexpenses')

        is_ebitda = None
        if is_grossprofit and is_opexpenses:
            is_ebitda = int(is_grossprofit) - int(is_opexpenses)
            tmp = self.pull('DepreciationAndAmortization', None, history=False)
            if tmp is not None:
                is_ebitda += int(tmp)

        # think IncomeTaxesPaid/IncomeTaxesPaidNet are cash flow
        is_incometax = self.pull('IncomeTaxExpenseBenefit', 'is.incometax')

        is_netincome = None
        for key in ['ProfitLoss', 'NetIncomeLoss',
                    'NetIncomeLossAvailableToCommonStockholdersBasic']:
            if is_netincome is None:
                is_netincome = self.pull(key, 'is.netincome')

        is_opincome = None
        for key in ['OperatingIncomeLoss', 
                    'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest']:
            if is_opincome is None:
                is_opincome = self.pull(key, 'is.opincome')

        # cash flow
        cf_operating = None
        for key in ['NetCashProvidedByUsedInOperatingActivities', 
                    'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations']:
            if cf_operating is None:
                cf_operating = self.pull(key, 'cf.operating')

        cf_depreciation = None
        for key in ['Depreciation', 'DepreciationNonproduction',
                    'DepreciationAndAmortization',
                    'DepreciationAmortizationAndAccretionNet']:
            if cf_depreciation is None:
                cf_depreciation = self.pull(key, 'cf.depreciation')

        cf_investing = None
        for key in ['NetCashProvidedByUsedInInvestingActivities', 
                    'NetCashProvidedByUsedInInvestingActivitiesContinuingOperations']:
            if cf_investing is None:
                cf_investing = self.pull(key, 'cf.investing')

        cf_ppe = None
        for key in ['PaymentsToAcquirePropertyPlantAndEquipment', 
                    'AdditionsToPropertyPlantEquipmentAndSoftwareCapitalization']:
            if cf_ppe is None:
                cf_ppe = self.pull(key, 'cf.ppe')

        cf_financing = None
        for key in ['NetCashProvidedByUsedInFinancingActivities',
                    'NetCashProvidedByUsedInFinancingActivitiesContinuingOperations']:
            if cf_financing is None:
                cf_financing = self.pull(key, 'cf.financing')

        cf_dividends = None
        for key in ['PaymentsOfDividends', 'PaymentsOfDividendsCommonStock',
                    'PaymentsOfDividendsMinorityInterest',
                    'PaymentsOfDividendsPreferredStockAndPreferenceStock']:
            if cf_dividends is None:
                cf_dividends = self.pull(key, 'cf.dividends')

        cf_cashchange = self.pull('CashAndCashEquivalentsPeriodIncreaseDecrease',
                                  'cf.cashchange')
        if cf_cashchange is None and (cf_operating or cf_investing or cf_financing):
            cf_cashchange = sum([int(x) for x in [
                                 cf_operating, cf_investing, cf_financing] if x])
            exchange = None
            for key in ['EffectOfExchangeRateOnCashAndCashEquivalents', 
                        'EffectOfExchangeRateOnCashAndCashEquivalentsContinuingOperations']:
                if exchange is None:
                    exchange = self.pull(key, None, history=False)
            if exchange is not None:
                cf_cashchange -= int(exchange)

        # write data to file
        with open(self.datapath, 'a') as f:
            f.write('{}\n'.format('|'.join(
                str(x) if x is not None else '' for x in [
                focus, ticker, cik, zipcode, form, formdate,
                date, acceptance, accession, name,
                bs_assets, bs_cash, bs_currentassets, bs_ppenet, 
                bs_ppegross, bs_currentliabilities, bs_longtermdebt,
                bs_equity, is_sales, is_cogs, is_grossprofit, 
                is_research, is_sga, is_opexpenses, is_ebitda, 
                is_incometax, is_netincome, is_opincome, 
                cf_operating, cf_depreciation, cf_investing,
                cf_ppe, cf_financing, cf_dividends, cf_cashchange])))

    def pull(self, element, field, history=True):
        """Returns most recent, period-appropriate value.
        Writes historical data to financials/data/history/{quarter}.

        :param element: XBRL element to look for
        :param field: standardized element name
        :param history: True to write historical periods to file
        """
        data = self.tree.xpath("//*[local-name()='{}']".format(element))
        if not data:
            return None

        y = []
        for x in data:
            if not x.text:
                continue
            val = x.text.split(':')[-1].strip()
            if val is not None:
                context = self.context[x.attrib.get('contextRef')]
                if 'explicitMember' in context:
                    continue
                y.append(dict(self.context[x.attrib.get('contextRef')].items() +
                              {'tag': element, 'val': val}.items()))
        if not y:
            return None
        if len(y) == 1:
            return y[0]['val']

        # return most recent instant value, write old to file
        if 'instant' in y[0]:
            y = sorted(y, key=lambda x: x['instant'], reverse=True)
            if history:
                with open(self.history, 'a') as f:
                    for d in y[1:]:
                        line = '|'.join([self.accession, 
                                         field,
                                         d['tag'],
                                         d['instant'].strftime('%Y%m%d'),
                                         d['val']])
                        f.write('{}\n'.format(line))
            return y[0]['val']

        # return 3-months data for quarterly, 12-months for annual
        for x in y:
            x['diff'] = (x['endDate'] - x['startDate']).days*-1
        if self.annual:
            z = [x for x in y if x['diff'] < -300]
        else:
            z = [x for x in y if x['diff'] < -60 and x['diff'] > -100]
        z = sorted(z, key=lambda x: (x['endDate'], x['diff']), reverse=True)

        # weird time periods
        if not z:
            z = sorted(y, key=lambda x: (x['endDate'], x['diff']), reverse=True)

        if history:
            with open(self.history, 'a') as f:
                for d in z[1:]:
                    line = '|'.join([self.accession,
                                     field,
                                     d['tag'],
                                     d['endDate'].strftime('%Y%m%d'),
                                     d['val']])
                    f.write('{}\n'.format(line))
        return z[0]['val']

    def test(self, data, element):
        """Returns list of relevant dicts.

        :param data: list of dicts
        :param element: XBRL element to look for
        """
        return [x for x in data if any(element.lower() in str(a).lower() for a 
                in (x.values() or x.keys()))]

