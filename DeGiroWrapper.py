# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import requests
import json
import os
import pandas as pd
class DeGiroWrapper:
    
    LOGIN_URL = 'https://trader.degiro.nl/login/secure/login'
    CLIENT_INFO_URL = 'https://trader.degiro.nl/pa/secure/client'
    PORTFOLIO_URL = 'https://trader.degiro.nl/reporting/secure/v3/positionReport/xls'
    
    def __init__(self):
        self._login()
        
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
        sess_id = self._request(self.LOGIN_URL, json=credentials, type='post')
        self.session_id = sess_id['sessionId']
        sess_id = {'sessionId': self.session_id}
        self.client_info = self._request(self.CLIENT_INFO_URL, params=sess_id, 
                                 type='get')['data']        
        
    def _request(self, url, headers=None, json=None, data=None, 
                 params=None, type='get', **kwargs):
        if type=='post':
            response = requests.post(url, headers=headers, json=json, data=data, **kwargs)
        elif type=='get':
            response = requests.get(url, headers=headers, params=params, **kwargs)
        return response.json()        
    
        
DGW = DeGiroWrapper()