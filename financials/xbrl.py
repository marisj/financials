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

    def update_quarter(self, qtr):
        """Pulls XBRL financial statement links from quarterly EDGAR index.

        :param qtr: 'YYYY/QTR2'
        """
        if qtr is None:
            today = datetime.datetime.now()
            qtr = '{}/QTR{}'.format(today.year, 
                                    quarter_from_month(today.month))
        self.recreate_files(qtr)

        c = urllib2.urlopen('{}/full-index/{}/xbrl.idx'.format(self.edgar, qtr))
        lines = c.read().split('\n')
        c.close()
        for line in lines[10:]:
            try:
                (cik, name, form, date, filing) = \
                    [x.strip() for x in line.strip().split('|')]
                #name = name.replace(',', '')
                if form in self.forms:
                    self.parse(cik, name, form, date, filing)
            except ValueError:
                with open(os.path.join(os.path.realpath('.'), 'check.txt'), 'a') as f:
                    f.write('{}\n'.format(line))

    def parse(self, cik, name, form, date, filing, return_all=False):
        """Parses XBRL instance doc into list of dicts. 

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
                            val = datetime.datetime.strptime(xx.text.strip(), 
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
        self.context = defs
        ticker = self.pull(tree, 'TradingSymbol', None, history=False)
        if ticker is not None:
            ticker = clean_ticker(ticker)
        if ticker is None:
            ticker = clean_ticker(xbrl[0].split('-')[0])
        fiscal_year = self.pull(tree, 'DocumentFiscalYearFocus', None,
                                history=False)
        fiscal_period = self.pull(tree, 'DocumentFiscalPeriodFocus', None,
                                  history=False)
        if fiscal_year is not None and fiscal_period is not None:
            focus = '{}{}'.format(fiscal_year, fiscal_period)
        else:
            focus = self.datapath.split('/')[-1]
        formdate = self.pull(tree, 'DocumentPeriodEndDate', None, history=False)

        # balance sheet
        bs_assets = self.pull(tree, 'Assets', 'bs.assets')
        bs_cash = self.pull(tree, 'Cash', 'bs.cash')
        if bs_cash is None:
            bs_cash = self.pull(tree, 'CashAndCashEquivalentsAtCarryingValue',
                                'bs.cash')
        bs_currentassets = self.pull(tree, 'AssetsCurrent', 'bs.currentassets')
        bs_ppenet = self.pull(tree, 'PropertyPlantAndEquipmentNet', 'bs.ppenet')
        bs_ppegross = self.pull(tree, 'PropertyPlantAndEquipmentGross', 'bs.ppegross')
        bs_currentliabilities = self.pull(tree, 'LiabilitiesCurrent', 
                                          'bs.currentliabilities')
        bs_longtermdebt = self.pull(tree, 'LongTermDebt', 'bs.longtermdebt')
        if bs_longtermdebt is None:
            tmp = self.pull(tree, 'LongTermDebtCurrent', None, history=False)
            tmp2 = self.pull(tree, 'LongTermDebtNoncurrent', None, history=False)
            if tmp is not None and tmp2 is not None:
                bs_longtermdebt = int(tmp) + int(tmp2)
            elif tmp is not None:
                bs_longtermdebt = tmp
            elif tmp2 is not None:
                bs_longtermdebt = tmp2
        bs_equity = None
        for key in ['CommonStockholdersEquity', 'StockholdersEquity',
                    'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
                    'PartnersCapitalIncludingPortionAttributableToNoncontrollingInterest',
                    'PartnersCapital', 'MemberEquity', 'AssetsNet']:
            if bs_equity is None:
                bs_equity = self.pull(tree, key, 'bs.equity')

        # income statement
        is_sales = self.pull(tree, 'SalesRevenueNet', 'is.sales')
        if is_sales is None:
            is_sales = self.pull(tree, 'Revenues', 'is.sales')
        is_cogs = self.pull(tree, 'CostOfGoodsAndServicesSold', 'is.cogs')
        if is_cogs is None:
            is_cogs = self.pull(tree, 'CostOfGoodsSold', 'is.cogs')
        is_grossprofit = self.pull(tree, 'GrossProfit', 'is.grossprofit')
        is_research = self.pull(tree, 'ResearchAndDevelopmentExpense', 'is.research')
        is_sga = self.pull(tree, 'SellingGeneralAndAdministrativeExpense', 'is.sga')
        is_opexpenses = self.pull(tree, 'OperatingCostsAndExpenses', 'is.opexpenses')
        if is_opexpenses is None:
            is_opexpenses = self.pull(tree, 'OperatingExpenses', 'is.opexpenses')
        is_ebitda = None
        if is_grossprofit and is_opexpenses:
            tmp = self.pull(tree, 'DepreciationAndAmortization', None, history=False)
            if tmp is not None:
                is_ebitda = int(is_grossprofit) - int(is_opexpenses) + int(tmp)
        is_incometax = self.pull(tree, 'IncomeTaxesPaid', 'is.incometax')
        if is_incometax is None:
            is_incometax = self.pull(tree, 'IncomeTaxesPaidNet', 'is.incometax')
        is_netincome = None
        for key in ['NetIncomeLoss', 'ProfitLoss', 'NetIncomeLossAvailableToCommonStockholdersBasic']:
            if is_netincome is None:
                is_netincome = self.pull(tree, key, 'is.netincome')
        is_opincome = self.pull(tree, 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
                                'is.opincome')

        # cash flow
        cf_operating = self.pull(tree, 'NetCashProvidedByUsedInOperatingActivities',
                                 'cf.operating')
        if cf_operating is None:
            cf_operating = self.pull(tree, 'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations',
                                     'cf.operating')
        cf_depreciation = self.pull(tree, 'Depreciation', 'cf.depreciation')
        cf_investing = self.pull(tree, 'NetCashProvidedByUsedInInvestingActivities',
                                 'cf.investing')
        if cf_investing is None:
            cf_investing = self.pull(tree, 'NetCashProvidedByUsedInInvestingActivitiesContinuingOperations',
                                     'cf.investing')
        cf_ppe = self.pull(tree, 'PaymentsToAcquirePropertyPlantAndEquipment',
                           'cf.ppe')
        cf_financing = self.pull(tree, 'NetCashProvidedByUsedInFinancingActivities',
                                 'cf.financing')
        if cf_financing is None:
            cf_financing = self.pull(tree, 'NetCashProvidedByUsedInFinancingActivitiesContinuingOperations',
                                     'cf.financing')
        cf_dividends = self.pull(tree, 'PaymentsOfDividends', 'cf.dividends')
        cf_cashchange = None
        if cf_operating and cf_investing and cf_financing:
            cf_cashchange = int(cf_operating) + int(cf_investing) + int(cf_financing)
            exchange = self.pull(tree, 'EffectOfExchangeRateOnCashAndCashEquivalents',
                                 None, history=False)
            if exchange is None:
                exchange = self.pull(tree, 'EffectOfExchangeRateOnCashAndCashEquivalentsContinuingOperations',
                                     None, history=False)
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

    def pull(self, tree, element, field, history=True):
        """Returns most recent value or list of relevant dicts.
        Writes historical data to financials/data/history/{quarter}.

        :param tree: ElementTree
        :param element: XBRL element to look for
        :param field: standardized element name
        :param history: True to write historical periods to file
        """
        data = tree.xpath("//*[local-name()='{}']".format(element))
        if not data:
            return None

        y = []
        for x in data:
            if not x.text:
                continue
            val = x.text.split(':')[-1].strip()
            if val is not None:
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

