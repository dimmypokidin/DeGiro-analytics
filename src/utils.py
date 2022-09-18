import pandas as pd
import requests
from io import BytesIO
from datetime import datetime

def process_price_history(data: dict) -> pd.DataFrame:
    resolution = data['resolution']
    start_date = data['start'].split('+') # time zone not relevant for me
    start_date = datetime.strptime(start_date[0], '%Y-%m-%dT%H:%M:%S')
    series = data['series'][1]['data']
    df = pd.DataFrame(series, columns=['date', 'price'])
    df['date'] = ordinal_to_date(df['date'], start_date, resolution)
    return df.set_index('date')

def ordinal_to_date(ord_series, origin, frequency):
    if frequency=='P1M':
        k = 12
        years = origin.year+(ord_series+origin.month-1)//12
        months = (ord_series+origin.month-1)%12+1
        time_df = pd.DataFrame({'year': years, 'month': months})
        time_df['day'] = 1
        out = pd.to_datetime(time_df)
    elif frequency=='P1D' or frequency=='PT1M':
        unit = frequency[-1:].lower()
        out = pd.to_datetime(ord_series, unit=unit, origin=origin) 
    return out

def drawdown_analytics(p):
    peaks = p.cummax()
    dd = (p-peaks).divide(peaks)
    dd_counts = (dd.eq(0) & dd.ne(dd.shift())).cumsum()
    n_dd = dd_counts.max()
    max_dd = -dd.min()
    max_dd_dur = dd_counts.value_counts().max()
    mean_dd_dur = dd_counts.value_counts().mean()
    out = {'NumDD': n_dd, 'MaxDD': max_dd, 
            'Max DD duration': max_dd_dur,
            'Mean DD duration': mean_dd_dur}
    return out

def return_analytics(p):
    r = p.divide(p.shift())-1
    mean_r = r.mean()*12
    mean_vol = r.std()*12**.5
    mean_r_adj = mean_r/mean_vol
    out = {'Mean return': mean_r,
        'Std': mean_vol,
        'Adjusted Return': mean_r_adj}
    return out

def analytics(prices):
    out = return_analytics(prices)
    out.update(drawdown_analytics(prices))
    out['T'] = len(prices)
    return out

def get_core_selection_etf():
    response = requests.get('https://www.degiro.nl/assets/js/data/core-selection-list-nl.csv')
    df = pd.read_csv(BytesIO(df.content))
    return df

def get_mappings():
    response = requests.get('https://trader.degiro.nl/product_search/config/dictionary/')
    return response.json()