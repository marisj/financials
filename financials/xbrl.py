"""
    financials.xbrl
    ===============

    Parses fundamental accounting terms from SEC XBRL filings.

    Balance sheet: 
        assets, cash, current assets, net ppe, gross ppe,
        current liabilities, liabilities, long term debt noncurrent, 
        long term debt current, long term debt, equity

    Income statement: 
        sales, cogs, gross profit, research, sga, operating expenses,
        income tax, net income, operating income

    Cash flow statement:
        operating, depreciation, depreciation and amortization,
        investing, financing,
        dividends, change in cash/cash equivalents

    copyright: (c) 2017 by Maris Jensen and Ivo Welch.
    license: BSD, see LICENSE for more details.
"""
import os
import datetime
from collections import defaultdict
try:
    from http.client import IncompleteRead 
except ImportError:
    from httplib import IncompleteRead

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
        self.entity = None

    def get_index(self, url):
        """Returns list of [form type, description, document] for a filing
        and its exhibits.

        :param url: filing index URL
        """
        c = openurl(url)
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
                    'bs_assets', 'bs_cash', 'bs_currentassets', 'bs_ppenet', 
                    'bs_ppegross', 'bs_currentliabilities', 
                    'bs_liabilities', 'bs_longtermdebtnoncurrent',
                    'bs_longtermdebtcurrent', 'bs_longtermdebt', 'bs_equity',
                    'is_sales', 'is_cogs', 'is_grossprofit', 
                    'is_research', 'is_sga', 'is_opexpenses', 
                    'is_incometax', 'is_netincome', 'is_opincome', 
                    'cf_operating', 'cf_depreciation', 
                    'cf_depreciationamortization', 'cf_investing',
                    'cf_financing', 'cf_dividends', 'cf_cashchange'])))

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
        c = openurl('{}/full-index/{}/xbrl.idx'.format(self.edgar, qtr))
        lines = c.read().decode().split('\n')
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

    def add_history(self, start=2009, end=None):
        """Pulls historical data.

        :param start: YYYY
        :param end: YYYY
        """
        end = datetime.datetime.now().year if end is None else end
        for year in range(start, end+1):
            for qtr in range(1, 5):
                q = '{}/QTR{}'.format(year, qtr)
                self.add_quarter(q)
                print('{} added'.format(q))

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
            tree = etree.parse(openurl(instance))
        except etree.XMLSyntaxError:
            tree = etree.parse(openurl(instance),
                               parser=etree.XMLParser(recover=True))
        except IncompleteRead:
            tree = etree.parse(openurl(instance))

        # pull acceptance datetime and zip
        sgml = index.replace('-index.htm', '.hdr.sgml')
        c = openurl(sgml)
        lines = c.read()
        c.close()
        acceptance = lines.decode().split('<ACCEPTANCE-DATETIME>')[-1].split('<')[0].strip()
        zipcode = format_zip(lines.decode().split('<ZIP>')[-1].split('<')[0].strip())

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
            return crap

        # general
        self.tree = tree
        self.context = defs
        self.entity = None
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

        # check for multiple legal entities
        check = tree.xpath("//*[local-name()='EntityCentralIndexKey']")
        if len(check) > 1:
            entity = [defs[x.attrib.get('contextRef')] for x in check if 
                      int(x.text) == int(cik)]
            if entity and 'LegalEntityAxis' in entity[0]:
                self.entity = entity[0]['LegalEntityAxis']

        # balance sheet
        bs_assets = None
        for key in ['Assets', 'AssetsNet']:
            if bs_assets is None:
                bs_assets = self.pull(key, 'bs_assets')

        bs_cash = None 
        for key in ['CashAndDueFromBanks', 'CashAndCashEquivalents',
                    'CashAndCashEquivalentsAtCarryingValue']:
            if bs_cash is None:
                bs_cash = self.pull(key, 'bs_cash')

        bs_currentassets = self.pull('AssetsCurrent', 'bs_currentassets')

        bs_ppenet = None
        for key in ['PropertyPlantAndEquipmentNet',
                    'PublicUtilitiesPropertyPlantAndEquipmentNet']:
            if bs_ppenet is None:
                bs_ppenet = self.pull(key, 'bs_ppenet')
        
        bs_ppegross = self.pull('PropertyPlantAndEquipmentGross', 'bs_ppegross')
        
        bs_currentliabilities = self.pull('LiabilitiesCurrent', 
                                          'bs_currentliabilities')

        bs_liabilities = self.pull('Liabilities', 'bs_liabilities')

        bs_longtermdebtnoncurrent = self.pull('LongTermDebtNoncurrent', 
                                              'bs_longtermdebtnoncurrent')
        if bs_longtermdebtnoncurrent is None:

            # build long term notes and loans
            bs_longtermdebtnoncurrent = self.pull('LongTermNotesAndLoans', None, 
                                                  history=False)
            if bs_longtermdebtnoncurrent is None:
                notes_payable = self.pull('LongTermNotesPayable', None, 
                                          history=False)
                if notes_payable is None:
                    notes_payable = 0
                    for key in ['MediumtermNotesNoncurrent', 
                                'JuniorSubordinatedLongTermNotes',
                                'SeniorLongTermNotes',
                                'ConvertibleLongTermNotesPayable',
                                'NotesPayableToBankNoncurrent', 
                                'OtherLongTermNotesPayable']:
                        tmp = self.pull(key, None, history=False)
                        if tmp is not None:
                            notes_payable += int(tmp)

                loans_payable = self.pull('LongTermLoansPayable', None, 
                                          history=False)
                if loans_payable is None:
                    loans_payable = 0
                    for key in ['LongTermLoansFromBank',
                                'OtherLoansPayableLongTerm']:
                        tmp = self.pull(key, None, history=False)
                        if tmp is not None:
                            loans_payable += int(tmp)

                bs_longtermdebtnoncurrent = int(notes_payable) + int(loans_payable)
            else:
                bs_longtermdebtnoncurrent = int(bs_longtermdebtnoncurrent)

            # add other elements
            for key in ['LongTermLineOfCredit', 'CommercialPaperNoncurrent',
                        'ConstructionLoanNoncurrent', 'SecuredLongTermDebt',
                        'SubordinatedLongTermDebt', 'UnsecuredLongTermDebt', 
                        'ConvertibleDebtNoncurrent', 
                        'ConvertibleSubordinatedDebtNoncurrent', 
                        'LongTermTransitionBond', 'LongTermPollutionControlBond', 
                        'JuniorSubordinatedDebentureOwedToUnconsolidatedSubsidiaryTrustNoncurrent',
                        'SpecialAssessmentBondNoncurrent',
                        'LongtermFederalHomeLoanBankAdvancesNoncurrent',
                        'OtherLongTermDebtNoncurrent']:
                tmp = self.pull(key, None, history=False)
                if tmp is not None:
                    bs_longtermdebtnoncurrent += int(tmp)

        bs_longtermdebtcurrent = self.pull('LongTermDebtCurrent', 
                                           'bs_longtermdebtcurrent')

        bs_longtermdebt = None
        for key in ['LongTermDebtAndCapitalLeaseObligations', 'LongTermDebt',
                    'LongTermDebtNetAlternative']:
            if bs_longtermdebt is None:
                bs_longtermdebt = self.pull(key, 'bs_longtermdebt')

        bs_equity = None
        for key in ['StockholdersEquity', 
                    'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
                    'PartnersCapital', 'CommonStockholdersEquity', 
                    'PartnersCapitalIncludingPortionAttributableToNoncontrollingInterest',
                    'MemberEquity', 'AssetsNet']:
            if bs_equity is None:
                bs_equity = self.pull(key, 'bs_equity')

        # income statement
        is_sales = None
        for key in ['SalesRevenueNet', 'Revenues', 'SalesRevenueGoodsNet',
                    'SalesRevenueServicesNet']:
            if is_sales is None:
                is_sales = self.pull(key, 'is_sales')

        is_cogs = None
        for key in ['CostOfGoodsAndServicesSold', 'CostOfGoodsSold', 'CostOfServices', 
                    'CostOfGoodsSoldExcludingDepreciationDepletionAndAmortization',
                    'CostOfRevenue']:
            if is_cogs is None:
                is_cogs = self.pull(key, 'is_cogs')

        is_grossprofit = self.pull('GrossProfit', 'is_grossprofit')
  
        is_research = None
        for key in ['ResearchAndDevelopmentExpense',
                    'ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost']:
            if is_research is None:
                is_research = self.pull(key, 'is_research')

        is_sga = None
        for key in ['SellingGeneralAndAdministrativeExpense', 
                    'SellingGeneralAndAdministrativeExpenses']:
            if is_sga is None:
                is_sga = self.pull(key, 'is_sga')

        is_opexpenses = None
        for key in ['OperatingCostsAndExpenses', 'OperatingExpenses', 
                    'CostsAndExpenses']:
            if is_opexpenses is None:
                is_opexpenses = self.pull(key, 'is_opexpenses')

        is_incometax = self.pull('IncomeTaxExpenseBenefit', 'is_incometax')
        if is_incometax is None:
            is_incometax = self.pull('IncomeTaxExpenseBenefitContinuingOperations',
                                     'is_incometax')

        is_netincome = None
        for key in ['NetIncomeLoss',
                    'NetIncomeLossAvailableToCommonStockholdersBasic',
                    'ProfitLoss',
                    'NetIncomeLossAvailableToCommonStockholdersDiluted']:
            if is_netincome is None:
                is_netincome = self.pull(key, 'is_netincome')

        is_opincome = None
        for key in ['OperatingIncomeLoss', 
                    'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest']:
            if is_opincome is None:
                is_opincome = self.pull(key, 'is_opincome')

        # cash flow
        cf_operating = None
        for key in ['NetCashProvidedByUsedInOperatingActivities', 
                    'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations']:
            if cf_operating is None:
                cf_operating = self.pull(key, 'cf_operating')

        cf_depreciation = self.pull('Depreciation', 'cf_depreciation')

        cf_depreciationamortization = None
        for key in ['DepreciationAmortizationAndAccretionNet',
                    'DepreciationAndAmortization', 
                    'DepreciationDepletionAndAmortization']:
            if cf_depreciationamortization is None:
                cf_depreciationamortization = self.pull(key, 'cf_depreciationamortization')

        cf_investing = None
        for key in ['NetCashProvidedByUsedInInvestingActivities', 
                    'NetCashProvidedByUsedInInvestingActivitiesContinuingOperations']:
            if cf_investing is None:
                cf_investing = self.pull(key, 'cf_investing')

        cf_ppe = None
        for key in ['GainLossOnSaleOfPropertyPlantEquipment']:
            if cf_ppe is None:
                cf_ppe = self.pull(key, 'cf_ppe', history=False)

        cf_financing = None
        for key in ['NetCashProvidedByUsedInFinancingActivities',
                    'NetCashProvidedByUsedInFinancingActivitiesContinuingOperations']:
            if cf_financing is None:
                cf_financing = self.pull(key, 'cf_financing')

        cf_dividends = None
        for key in ['PaymentsOfDividends']:
            if cf_dividends is None:
                cf_dividends = self.pull(key, 'cf_dividends')

        cf_cashchange = self.pull('CashAndCashEquivalentsPeriodIncreaseDecrease',
                                  'cf_cashchange')
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
        if cf_cashchange is None:
            cf_cashchange = self.pull('CashPeriodIncreaseDecrease', 'cf_cashchange')

        # write data to file
        with open(self.datapath, 'a') as f:
            f.write('{}\n'.format('|'.join(
                str(x) if x is not None else '' for x in [
                focus, ticker, cik, zipcode, form, formdate,
                date, acceptance, accession, name,
                bs_assets, bs_cash, bs_currentassets, bs_ppenet, 
                bs_ppegross, bs_currentliabilities, bs_liabilities, 
                bs_longtermdebtnoncurrent, bs_longtermdebtcurrent, 
                bs_longtermdebt, bs_equity, 
                is_sales, is_cogs, is_grossprofit, 
                is_research, is_sga, is_opexpenses,
                is_incometax, is_netincome, is_opincome, 
                cf_operating, cf_depreciation, 
                cf_depreciationamortization, cf_investing,
                cf_financing, cf_dividends, cf_cashchange])))

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
                axes = [k for k in context.keys() if k.endswith('Axis') and 
                        k != 'LegalEntityAxis']
                if axes:
                    continue

                if self.entity is None:
                    y.append(dict(list(context.items()) + 
                             list({'tag': element, 'val': val}.items())))
                elif 'LegalEntityAxis' in context:
                    if context['LegalEntityAxis'] == self.entity:
                        y.append(dict(list(context.items()) + 
                                 list({'tag': element, 'val': val}.items())))

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
        y = [x for x in y if 'endDate' in x and 'startDate' in x]
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
        if not z:
            return None

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

    def temp_context(self, instance):
        tree = etree.parse(openurl(instance))
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
        return tree, defs

