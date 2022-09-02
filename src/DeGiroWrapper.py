# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import requests
import json
import os
from datetime import date
import pandas as pd

class DeGiroWrapper:
    
    LOGIN_URL = 'https://trader.degiro.nl/login/secure/login'
    TFA_URL = 'https://trader.degiro.nl/login/secure/login/totp'
    CLIENT_INFO_URL = 'https://trader.degiro.nl/pa/secure/client'
    PORTFOLIO_URL = 'https://trader.degiro.nl/reporting/secure/v3/positionReport/xls'
    TRANSACTIONS_URL = 'https://trader.degiro.nl/reporting/secure/v4/transactions'
    ACC_OVERVIEW_URL = 'https://trader.degiro.nl/reporting/secure/v6/accountoverview'
    LOOKUP_URL = 'https://trader.degiro.nl/product_search/secure/v5/products/lookup'
    PRODUCT_INFO_URL = 'https://trader.degiro.nl/product_search/secure/v5/products/info'
    PRICE_DATA_URL = 'https://charting.vwdservices.com/hchart/v1/deGiro/data.js'
    CREDENTIALS_FILE = 'credentials.json'
    SESSION_CACHE = '__pycache__/session.json'

    def __init__(self, cache_credentials=False, cache_session=False):
        self.cache_credentials = cache_credentials
        self.cache_session = cache_session
        self._get_session_data()
        self.today = date.today().strftime('%d/%m/%Y')

    def session_status(method):
        "Decorator to check the session is active"
        def new_method(self, url, **kwargs):
            response = method(self, url, **kwargs)
            if response.status_code==401:
                print('Your session has expired. Logging in again...')
                self._get_session_data()
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

    def _load_credentials(self):
        "Load credentials from store file"
        with open(self.CREDENTIALS_FILE, "r") as infile:
            credentials = json.loads(infile.read())
        return credentials   

    def _credentials(self):
        print("Please type in your credentials.")
        uid = input('Enter username:')
        pwd = input('Enter password:')
        credentials = {'username': uid, 'password': pwd}
        return credentials

    def _write_credentials(self, credentials):
        "Request to fill in credential and cache them in the directory in a json format"
        with open(self.CREDENTIALS_FILE, "w") as outfile:
            json.dump(credentials, outfile) 

    def _login(self):
        credentials = self.get_credentials()
        response = self._post(self.LOGIN_URL, json=credentials).json()
        if response['status']==3:
            print('Your credentials are invalid') 
            os.remove('credentials.json')
            return self._login()
        elif response['status']==6: # 2FA enabled
            one_time_code = input('Enter 2FA code:')
            credentials['oneTimePassword'] = one_time_code
            response = self._post(self.TFA_URL, json=credentials).json()
            return response
        else:
            return response

    def get_credentials(self):
        if self.cache_credentials:
            if os.path.isfile(self.CREDENTIALS_FILE):
                return self._load_credentials()
            else:
                credentials = self._credentials()
                self._write_credentials(credentials)
                return credentials
        else:
            credentials = self._credentials()
            return credentials 

    def _cache_session(self, session):
        with open(self.SESSION_CACHE, "w") as outfile:
            json.dump(session, outfile) 

    def _load_session(self):
        "Load credentials from store file"
        with open(self.SESSION_CACHE, "r") as infile:
            session = json.loads(infile.read())
        self.session = session   

    def _get_session_data(self):
        if self.cache_session and os.path.isfile(self.SESSION_CACHE):
            self._load_session()
        else:
            response = self._login()
            self.session_id = response['sessionId']
            sess_id = {'sessionId': self.session_id}
            client_info = self._get(self.CLIENT_INFO_URL, params=sess_id).json()['data']        
            self.session = {'sessionId': self.session_id, 'intAccount': client_info['intAccount']}
            if self.cache_session: self._cache_session(self.session)

    def get_current_portfolio(self, also_closed=False):
        """ Get current portfolio holdings.
            Inputs:
                also_closed: (bool) wether to report also closed positions
            Returns:
                pf: pd.DataFrame with columns
                    name - security name
                    isin - ISIN (identifier)
                    symbol - symbol (identifier)
                    productType 
                    currency
                    exchangeId
                    closePrice - latest price quote
                    Q - number of shares
                    weight - portfolio weight
        """
        transactions = self.get_transactions('01/01/1990', self.today)
        Q = transactions.groupby('productId').quantity.sum().rename('Q', index='id')
        if not also_closed:
            Q = Q[Q>0]
        pf['Q'] = Q
        pf = pf.filter(['name', 'isin', 'symbol', 'productType', 'currency', 'exchangeId', 'closePrice', 'Q'], axis=1)
        pf['weight'] = pf.Q*pf.closePrice # pf weights
        pf['weight']/= pf['weight'].sum()
        return pf

    def get_overview(self, start_date: str, end_date: str=None) -> pd.DataFrame:
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
        out = []
        for row in data:
            if 'balance' in row:
                balance = row.pop('balance')
                if 'cashFund' in balance:
                    cash_fund = balance.pop('cashFund')
                    cash_fund = cash_fund[0]
                    cash_fund = {'csh_fnd_'+ key: value for key, value in cash_fund.items()}
                    balance.update(cash_fund)
                balance = {'bal_'+ key: value for key, value in balance.items()}
                row.update(balance)
            out.append(row)
        df = pd.DataFrame(out)
        df['date'] = pd.to_datetime(df.date, utc=True)
        return df

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
        df = pd.DataFrame(response.json()['data'])
        df['date'] = pd.to_datetime(df.date, utc=True)
        return df
    
    def _lookup(self, text: str, limit: int=10, ETF=False)-> dict:
        """ Srearch a product using text.
            Inputs:
                text: (str) could be identifier or name
                limit: (int) max number of products to return
            Returns:
                out: (dict)
        """
        params = {**self.session, 'searchText': text, 'limit': limit}
        if ETF: params['productTypeId'] = 131
        response = self._get(self.LOOKUP_URL, params=params)
        out = response.json()['products']
        return out

    def _product_info(self, ids: list or int or str)->dict:
        """ Get product info.
            Input:
                ids: DeGiro product(s) ID(s)
            Returns:
                out: (dict)
        """
        if not isinstance(ids, list):
            ids = [ids]
        ids = json.dumps(ids)
        headers = {'content-type': 'application/json'}
        response = self._post(self.PRODUCT_INFO_URL, params=self.session, data=ids, headers=headers)
        out = response.json()['data'] 
        return out

    def _get_prices(self, vwdId, vwdIdentifierType, history: str = '50Y', resolution: str = '1D'):
        """ Get instrument's price history.
        Inputs:
            vwdId: (int) identifier 
            vwdIdentifierType: (str) identifier type ('issueid' or 'vwId')
            history: (str) lookback history format integer + ('Y' or 'D' or 'M'). Default 50Y
            resolution: (str) frequency of data. Default daily (1D). Possibly monthly 1M or intraday (T1M).
            Note that not all history/resolution combinations are feasible.
        Return:
            dictionary with data
        """
        params = {
                'requestid': 1,
                'period': 'P' + history,
                'resolution': 'P' + resolution,
                'series': [f'{vwdIdentifierType}:' + vwdId, f'price:{vwdIdentifierType}:' + vwdId],
                'userToken': self.client_info['id']
                 }
        response = self._get(self.PRICE_DATA_URL, params=params)
        return response.json()
