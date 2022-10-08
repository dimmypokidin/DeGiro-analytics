import requests
from src.utils import process_price_history

class Product:

    PRICE_DATA_URL = 'https://charting.vwdservices.com/hchart/v1/deGiro/data.js'    

    def __init__(self, product_dict, client_token):
        for key, value in product_dict.items():
            setattr(self, key, value)
        self.token = client_token

    def get(self, columns, index_col=None):
        assert all(hasattr(self, col) for col in columns), "Some columns not in product"
        if index_col is not None: assert hasattr(self, index_col), "Index column not in product"
        out_cols = [getattr(self, col) for col in columns]
        if index_col is not None:
            return {getattr(self, index_col): out_cols}
        else:
            return out_cols

    def get_prices(self, history: str = '50Y', resolution: str = '1D'):
        """ Get products price history.
        Inputs:
            history: (str) lookback history format integer + ('Y' or 'D' or 'M'). Default 50Y
            resolution: (str) frequency of data. Default daily (1D). Possibly monthly 1M or intraday (T1M).
            Note that not all history/resolution combinations are feasible.
        Return:
            pd.DataFrame with price history
        """
        params = {
                'requestid': 1,
                'period': 'P' + history,
                'resolution': 'P' + resolution,
                'series': [f'{self.vwdIdentifierType}:' + self.vwdId, 
                            f'price:{self.vwdIdentifierType}:' + self.vwdId],
                'userToken': self.token
                 }
        response = requests.get(self.PRICE_DATA_URL, params=params)
        return process_price_history(response.json())