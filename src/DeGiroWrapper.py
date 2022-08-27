# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import requests
import json
import os
import math
from datetime import date
import pandas as pd

class DeGiroWrapper:
    
    LOGIN_URL = 'https://trader.degiro.nl/login/secure/login'
    CLIENT_INFO_URL = 'https://trader.degiro.nl/pa/secure/client'
    PORTFOLIO_URL = 'https://trader.degiro.nl/reporting/secure/v3/positionReport/xls'
    TRANSACTIONS_URL = 'https://trader.degiro.nl/reporting/secure/v4/transactions'
    ACC_OVERVIEW_URL = 'https://trader.degiro.nl/reporting/secure/v6/accountoverview'
    LOOKUP_URL = 'https://trader.degiro.nl/product_search/secure/v5/products/lookup'
    PRODUCT_INFO_URL = 'https://trader.degiro.nl/product_search/secure/v5/products/info'
    PRICE_DATA_URL = 'https://charting.vwdservices.com/hchart/v1/deGiro/data.js'

    def __init__(self):
        self._login()
        self.today = date.today().strftime('%d/%m/%Y')
        
    def _load_credentials(self):
        with open("credentials.json", "r") as infile:
            credentials = json.loads(infile.read())
        return credentials   
    
    def _write_credentials(self):
        uid = input('Enter username:')
        pwd = input('Enter password:')
        credentials = {'username': uid, 'password': pwd}
        with open("credentials.json", "w") as outfile:
            json.dump(credentials, outfile) 

    def _login(self):
        if not os.path.isfile('credentials.json'):
            self._write_credentials()
        credentials = self._load_credentials()
        response = requests.post(self.LOGIN_URL, json=credentials)
        if response.status_code:
            pass
        self.session_id = sess_id['sessionId']
        sess_id = {'sessionId': self.session_id}
        self.client_info = requests.get(self.CLIENT_INFO_URL, params=sess_id).json()['data']        
        self.session = {'sessionId': self.session_id, 'intAccount': self.client_info['intAccount']}

    def get_portfolio(self, date=None) -> pd.DataFrame:
        """ Get portfolio holdings as of {date}
            date: str of format dd/mm/yyyy
        """
        date = date if date is not None else self.today
        params = {**self.session, 'country': 'NL', 'lang': 'en', 'toDate': date}
        response = requests.get(self.PORTFOLIO_URL, params=params)
        df = pd.read_excel(response.content)
        df['weight'] = df['Waarde in EUR']/df['Waarde in EUR'].sum()
        ids, vwids = [], []
        for isin in df['Symbool/ISIN']:
            if isinstance(isin, str):
                res = self._lookup(isin, limit=1)[0]
                ids.append(res['id'])
                vwids.append(res['vwdId'])
            else:
                ids.append(None)
                vwids.append(None)
        df['vwids'] = vwids
        idx = pd.Index(ids, name='id')
        return df.set_index(idx)
    
    def get_overview(self, start_date: str, end_date=None):
        """ Get account overview from {start_date} to {end_date}
            start_date, end_date: str of format dd/mm/yyyy
        """
        end_date = end_date if end_date is not None else self.today
        params = {**self.session, 'fromDate': start_date, 'toDate': end_date}
        response = requests.get(self.ACC_OVERVIEW_URL, params=params)
        return pd.DataFrame(response.json()['data']['cashMovements'])

    def get_transactions(self, start_date: str, end_date: str, group_by_order=False):
        """ Get portfolio holdings as of {date}
            date: str of format dd/mm/yyyy
        """
        params = {**self.session,
                  'groupTransactionsByOrder': group_by_order, 
                  'fromDate': start_date, 
                  'toDate': end_date}
        response = requests.get(self.TRANSACTIONS_URL, params=params)
        df = pd.DataFrame(response.json()['data'])
        return df
    
    def _lookup(self, text: str, limit: int=10, ETF=False):
        """ Get portfolio holdings as of {date}
            date: str of format dd/mm/yyyy
        """
        params = {**self.session, 'searchText': text, 'limit': limit}
        if ETF: params['productTypeId'] = 131
        response = requests.get(self.LOOKUP_URL, params=params)
        return response.json()['products']

    def _product_info(self, ids: list):
        """ Get portfolio holdings as of {date}
            date: str of format dd/mm/yyyy
        """
        ids = json.dumps(ids)
        headers = {'content-type': 'application/json'}
        response = requests.post(self.PRODUCT_INFO_URL, params=self.session, data=ids, headers=headers)
        df = pd.DataFrame(response.json()['data']).T
        return df.set_index('id')

    def get_price_history(self, isin=None, vwid=None, history: str = '50Y', resolution: str = '1D'):
        """ Get portfolio holdings as of {date}
            date: str of format dd/mm/yyyy
        """
        assert isin is not None or vwid is not None, "You must specify either 'isin' or 'vwid'"
        if vwid is None:
            res = self._lookup(isin, limit=1)[0]
            vwid = res['vwdId']
        params = {
                'requestid': 1,
                'period': 'P' + history,
                'resolution': 'P' + resolution,
                'series': ['issueid:' + vwid, 'price:issueid:' + vwid],
                'userToken': self.client_info['id']
                 }
        response = requests.get(self.PRICE_DATA_URL, params=params)
        return response.json()

