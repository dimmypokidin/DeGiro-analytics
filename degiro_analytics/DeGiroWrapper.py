import requests
import json
import os
from datetime import date
from degiro_analytics.utils import process_price_history, products_to_df, products_to_prices_df, overview_to_df
import pandas as pd
class DeGiroWrapper:
    
    LOGIN_URL = 'https://trader.degiro.nl/login/secure/login'
    TFA_URL = 'https://trader.degiro.nl/login/secure/login/totp'
    CLIENT_INFO_URL = 'https://trader.degiro.nl/pa/secure/client'
    PORTFOLIO_URL = 'https://trader.degiro.nl/reporting/secure/v3/positionReport/xls'
    TRANSACTIONS_URL = 'https://trader.degiro.nl/reporting/secure/v4/transactions'
    ACC_OVERVIEW_URL = 'https://trader.degiro.nl/reporting/secure/v6/accountoverview'
    ETF_SEARCH_URL = 'https://trader.degiro.nl/product_search/secure/v5/etfs'
    LOOKUP_URL = 'https://trader.degiro.nl/product_search/secure/v5/products/lookup'
    PRODUCT_INFO_URL = 'https://trader.degiro.nl/product_search/secure/v5/products/info'
    ETF_URL = 'https://trader.degiro.nl/product_search/secure/v5/etfs'
    CREDENTIALS_FILE = 'credentials.json'
    SESSION_CACHE = '__pycache__/session'
    CURRENCY_MAP = {'EUR': {'GBP': 714324, 'USD': 705366, 'CFH': 714322, 'JPY': 1316472, 'CAD': 841089} }

    def __init__(self, cache_credentials=False, cache_session=False, base_curr='EUR'):
        """ You may chose to cache_credentials in the working directory to avoid enetring them every time.
        You may also opt to cache the session to avoid logging in again if the kernels is restarted.
        base_curr can be one of the currencies in the CURRENCY_MAP. The currency conversion happens under the hood.
        """
        self.cache_credentials = cache_credentials
        self.cache_session = cache_session
        self._get_session_data()
        self.today = date.today().strftime('%d/%m/%Y')
        self.base_curr = base_curr

    def session_status(method):
        "Decorator to check if the session is active"
        def new_method(self, url, **kwargs):
            response = method(self, url, **kwargs)
            if response.status_code==401:
                print('Your session has expired. Logging in again...')
                if self.cache_session: os.remove(self.SESSION_CACHE)
                self._get_session_data()
                kwargs['params'].update(**self.session)
                return method(self, url, **kwargs)
            else:
                return response
        return new_method

    @session_status
    def _post(self, url, **kwargs):
        response = requests.post(url, **kwargs)
        return response

    @session_status
    def _get(self, url, **kwargs):
        response = requests.get(url, **kwargs)
        return response

    @property
    def rates(self):
        if not hasattr(self, 'fx_rates'):
            self._compute_rates()
        return self.fx_rates

    def __load_credentials(self):
        "Load credentials from store file"
        with open(self.CREDENTIALS_FILE, "r") as infile:
            credentials = json.loads(infile.read())
        return credentials   

    def __credentials(self):
        print("Please type in your credentials.")
        uid = input('Enter username:')
        pwd = input('Enter password:')
        credentials = {'username': uid, 'password': pwd}
        return credentials

    def __write_credentials(self, credentials):
        "Request to fill in credential and cache them in the directory in a json format"
        with open(self.CREDENTIALS_FILE, "w") as outfile:
            json.dump(credentials, outfile) 

    def __mfa(self, credentials):
        one_time_code = input('Enter 2FA code:')
        credentials['oneTimePassword'] = one_time_code
        response = self._post(self.TFA_URL, json=credentials).json()
        if response['status']==3:
            print('2FA code is invalid. Try again...')
            return self.__mfa(credentials)
        return response

    def __login(self):
        credentials = self.get_credentials()
        response = self._post(self.LOGIN_URL, json=credentials).json()
        if response['status']==3:
            print('Your credentials are invalid') 
            os.remove('credentials.json')
            return self.__login()
        elif response['status']==6: # 2FA enabled
            response = self.__mfa(credentials)
            return response
        else:
            return response

    def get_credentials(self):
        if self.cache_credentials:
            if os.path.isfile(self.CREDENTIALS_FILE):
                return self.__load_credentials()
            else:
                credentials = self.__credentials()
                self.__write_credentials(credentials)
                return credentials
        else:
            credentials = self.__credentials()
            return credentials 

    def __cache_session(self, session):
        with open(self.SESSION_CACHE, "w") as outfile:
            outfile.write(session) 

    def _load_session(self):
        "Load credentials from store file"
        with open(self.SESSION_CACHE, "r") as infile:
            session = infile.read()
        return session   

    def __get_session_id(self):
        if self.cache_session and os.path.isfile(self.SESSION_CACHE):
            session_id = self._load_session()
        else:
            response = self.__login()
            session_id = response['sessionId']
            if self.cache_session: self.__cache_session(session_id)
        return session_id

    def _get_session_data(self):
        session_id = self.__get_session_id()
        self.session = {'sessionId': session_id}
        self.client_info = self._get(self.CLIENT_INFO_URL, params=self.session).json()['data']        
        self.session['intAccount'] = self.client_info['intAccount']

    def _compute_rates(self):
        currencies = self.get_products(self.CURRENCY_MAP['EUR'].values())
        rates = {'EUR': {}}
        for rate in currencies:
            rates['EUR'][rate.name[-3:]] = rate.get_rate_hist()
        if self.base_curr!='EUR':
            rates_n = {self.base_curr: {}}
            for key, value in rates['EUR'].items():
                if key!=self.base_curr:
                    rates_n[self.base_curr][key] = 1/rates['EUR'][self.base_curr]*value
                else:
                    rates_n[self.base_curr]['EUR'] = 1/rates['EUR'][key]
            rates = rates_n
        self.fx_rates = rates

    def get_prices(self, ids, history: str = '50Y', resolution: str = '1D'):
        "Get price history"
        products = self.get_products(ids)
        return products_to_prices_df(products, history, resolution)

    def get_current_portfolio(self):
        """ Get current portfolio holdings.
            Returns:
                pf: pd.DataFrame with columns
                    name - security name
                    isin - ISIN (identifier)
                    productType 
                    currency
                    exchangeId
                    closePrice - latest price quote
                    price_base_curr - latest price in base currency
                    Q - number of shares
                    W - portfolio weight
        """
        transactions = self.get_transactions('01/01/1990', self.today)
        Q = transactions.groupby('productId').quantity.sum().rename('Q')
        Q = Q[Q>0] # drop closed positions
        Q.index.name = 'id'
        products = self.get_products(Q.index)     
        pf = products_to_df(products ,columns=['id', 'name' ,'isin', 'currency', 'productType', 'exchangeId',
                                               'closePrice', 'price_base_curr'] ).set_index('id')  
        pf = pf.join(Q)   
        pf['W'] = pf.Q*pf.price_base_curr
        pf['W']/= pf['W'].sum()
        return pf

    def get_overview(self, start_date: str, end_date: str=None):
        """ Get account overview.
            Inputs:
                start_date: str of format dd/mm/yyyy 
                end_date: str of format dd/mm/yyyy 
            Returns:
                df: pd.DataFrame
        """
        end_date = end_date if end_date is not None else self.today
        params = {**self.session, 'fromDate': start_date, 'toDate': end_date}
        response = self._get(self.ACC_OVERVIEW_URL, params=params)
        data = response.json()['data']['cashMovements']
        return [OverviewItem(item, self) for item in data]

    def get_transactions(self, start_date: str, end_date: str = None, group_by_order=False) -> pd.DataFrame:
        """ Get account transactions history.
            Inputs:
                start_date: (str) of format dd/mm/yyyy 
                end_date: (str) of format dd/mm/yyyy
            Returns:
                df: pd.DataFrame 
        """
        end_date = self.today if end_date is None else end_date
        params = {**self.session,
                  'groupTransactionsByOrder': group_by_order, 
                  'fromDate': start_date, 
                  'toDate': end_date}
        response = self._get(self.TRANSACTIONS_URL, params=params)
        out = response.json()['data']
        df = pd.DataFrame(out)
        df['date'] = pd.to_datetime(df.date, utc=True)
        if self.base_curr!='EUR':
            rates = self.rates[self.base_curr]['EUR']
            idx = rates.index.get_indexer(df.date, method='nearest')
            df['totalPlusAllFeesInBaseCurrency']/= rates.iloc[idx].values
            df['totalInBaseCurrency']/= rates.iloc[idx].values
        return df

    def get_account_cash_flows(self, start_date, end_date=None, fees=True, dividends=True):
        T = self.get_transactions(start_date, end_date)
        if fees:
            cf_col = 'totalPlusAllFeesInBaseCurrency'
        else:
            cf_col = 'totalInBaseCurrency'
        CF = T[['date', 'productId', cf_col]].copy()
        CF['type'] = 'Transaction + Fee' if fees else 'Transaction'
        CF.rename(columns={cf_col: 'CF'}, inplace=True)
        if dividends:
            OV = self.get_overview(start_date, end_date)
            OV = overview_to_df(OV, columns=['productId', 'description', 'change'])
            D = OV.loc[OV.description.str.contains('Dividend'), ['date', 'productId', 'change']].copy()
            D.rename(columns={'change': 'CF'}, inplace=True)
            D['type'] = 'Dividend'
            CF = pd.concat([CF, D])
        prods = self.get_products(CF.productId.unique())
        prods = products_to_df(prods, ['id', 'name', 'isin'])
        return CF.merge(prods, left_on='productId', right_on='id').drop('id', axis=1).sort_values('date')

    def lookup(self, text: str, limit: int=10)-> dict:
        """ Srearch investment products using text.
            Inputs:
                text: (str) could be identifier or name
                limit: (int) max number of products to return
            Returns:
                out: (dict)
        """
        params = {**self.session, 'searchText': text, 'limit': limit}
        response = self._get(self.LOOKUP_URL, params=params)
        out = response.json()['products']
        return [Product(prod, self) for prod in out]

    def get_products(self, ids: list or int or str)->list:
        """ Retrieve investment products using their IDs.
            Input:
                ids: DeGiro product(s) ID(s)
            Returns:
                out: (list) products
        """
        if hasattr(ids, '__len__'):
            ids = [int(l) for l in ids]
        else:
            ids = [ids]
        ids = json.dumps(ids)
        headers = {'content-type': 'application/json'}
        response = self._post(self.PRODUCT_INFO_URL, params=self.session, data=ids, headers=headers)
        out = response.json()['data'] 
        out = [Currency(dict, self) if dict['productType']=='CURRENCY' else Product(dict, self) for dict in out.values()]
        return out

    def search_etfs(self, text:str=None, only_free:bool=False, limit: int=25):
        """ Srearch ETFs using text.
            Inputs:
                text: (str) could be identifier or name
                only_free: (bool) look only ETFs from DeGiro core selection (comission free)
                limit: (int) max number of products to return
            Returns:
                out: (dict)
        """
        params = {**self.session, 'limit': limit}
        if only_free: 
            params['etfFeeTypeId'] = 2
        if text:
            params['searchText'] = text
        response = self._get(self.ETF_URL, params=params)
        out = response.json()['products']
        return [Product(prod, self) for prod in out]


class ProductBase:

    PRICE_DATA_URL = 'https://charting.vwdservices.com/hchart/v1/deGiro/data.js'

    def __init__(self, product_dict, DGW: DeGiroWrapper):
        for key, value in product_dict.items():
            if key in ['id', 'productId']:
                value = int(value)
            setattr(self, key, value)
        self.token = DGW.client_info['id']
        self.base_curr = DGW.base_curr
        self.DGW = DGW
        self.convert_currency()
  
    def convert_currency(self):
        return

    def get(self, attrs):
        "Get a set of product attributes attrs"
        out_cols = []
        for col in attrs:
            try:
                val = getattr(self, col)
            except AttributeError:
                print('Warning:', col, 'not in product', self.name)
                val = None
            out_cols.append(val)
        return out_cols

    def __get_history__(self, history, resolution):
        params = {
            'requestid': 1,
            'period': 'P' + history,
            'resolution': 'P' + resolution,
            'series': [f'{self.vwdIdentifierType}:' + self.vwdId, f'price:{self.vwdIdentifierType}:' + self.vwdId],
            'userToken': self.token
            }
        response = requests.get(self.PRICE_DATA_URL, params=params)
        return response.json()

 
class Product(ProductBase):

    def convert_currency(self):
        if hasattr(self, 'closePrice'):
            if self.base_curr!=self.currency:
                self.price_base_curr = self.closePrice/self.DGW.rates[self.base_curr][self.currency][self.closePriceDate]
            else:
                self.price_base_curr = self.closePrice

    def get_price_hist(self, history: str = '50Y', resolution: str = '1D', convert=True):
        """
        Get product's price history.
        Inputs:
            history: (str) lookback history format integer + ('Y' or 'D' or 'M'). Default 50Y
            resolution: (str) frequency of data. Default daily (1D). Possibly monthly 1M or intraday (T1M).
            Note that not all history/resolution combinations are feasible.
            convert: (bool) whether to convert to the base currency or keep the original
        Output:
            out: (pd.DataFrame)
        """
        hist_dct = self.__get_history__(history, resolution)
        out = process_price_history(hist_dct)
        out['name'] = self.name
        out['productId'] = self.id
        out['isin'] = self.isin
        if convert and self.base_curr!=self.currency and resolution != 'T1M': # currently no support for intraday currency conversion
            out = out.join(self.DGW.rates[self.DGW.base_curr][self.currency], on='date', how='left')
            out.rate.fillna(method='bfill', inplace=True) 
            out['price']/= out.rate
        return out

class Currency(ProductBase):
        
    def get_rate_hist(self):
        hist_dct = self.__get_history__('50Y', '1D')
        return process_price_history(hist_dct).set_index('date').price.rename('rate')

class OverviewItem(ProductBase):
        
    def convert_currency(self):
        if hasattr(self, 'change'):
            if self.base_curr!=self.currency:
                self.change_base_curr = self.change/self.DGW.rates[self.base_curr][self.currency].asof(self.valueDate)
            else:
                self.change_base_curr = self.change