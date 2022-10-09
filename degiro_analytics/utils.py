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
    return df

def products_to_df(products, columns):
    out = [product.get(columns) for product in products]
    return pd.DataFrame(out, columns=columns)

def products_to_prices_df(products, history='50Y', resolution='1D'):
    out = []
    for product in products:
        p = product.get_price_hist(history, resolution)
        out.append(p)
    return pd.concat(out)

def overview_to_df(ovs, columns=[], skipna=True):
    columns = ['date', 'type', 'currency', 'valueDate'] + columns
    out = []
    for ov in ovs:
        if any( not hasattr(ov, name) for name in columns) and skipna:
             continue
        out.append(ov.get(columns))
    df = pd.DataFrame(out, columns=columns)
    df['date'] = pd.to_datetime(df.date, utc=True)
    df['valueDate'] = pd.to_datetime(df.valueDate, utc=True)
    return df
    
def ordinal_to_date(ord_series, origin, frequency):
    if frequency=='P1M':
        k = 12
        years = origin.year+(ord_series+origin.month-1)//12
        months = (ord_series+origin.month-1)%12+1
        time_df = pd.DataFrame({'year': years, 'month': months})
        time_df['day'] = 1
        out = pd.to_datetime(time_df, utc=True)
    elif frequency=='P1D' or frequency=='PT1M':
        unit = frequency[-1:].lower()
        out = pd.to_datetime(ord_series, unit=unit, origin=origin, utc=True) 
    return out

def drawdown_analytics(p):
    """Drawdown is is a percentage of price decline since the last price peak.
       Drawdawn duration is the time elapsed (days) since the last time peak.
    """
    peaks = p.cummax()
    dd = (p-peaks).divide(peaks)
    dd_counts = (dd.eq(0) & dd.ne(dd.shift())).cumsum()
    n_dd = dd_counts.max()
    max_dd = -dd.min()
    dd_days = dd_counts.groupby(dd_counts).apply(lambda x: x.index[-1]-x.index[0]).dt.days
    max_dd_dur = dd_days.max()
    mean_dd_dur = dd_days.mean()
    out = {'Number of drawdowns': n_dd, 'Maximum Drawdown': max_dd, 
            'Max drawdown duration (days)': max_dd_dur,
            'Mean drawdown duration (days)': mean_dd_dur}
    return out

def return_analytics(p):
    r = p.divide(p.shift())-1
    mean_r = r.mean()
    mean_vol = r.std()
    mean_r_adj = mean_r/mean_vol
    out = {'Mean return': mean_r,
        'Std': mean_vol,
        'Risk Adjusted Return': mean_r_adj}
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

def irr(cfs: pd.Series, r=0, pos=True, step=.0001):
    "Calculates Internal Rate of Return (IRR) "
    assert isinstance(cfs.index, pd.DatetimeIndex), "input series' index must be datetime!"
    pows = (cfs.index-cfs.index[0]).days/365
    npv1 = npv(cfs.values, pows, r)
    if abs(npv1)<1:
        return r # converts to yearly
    if npv1>0 and pos:
        r+= step
    elif npv1<0 and not pos:
        r-= step
    elif npv1>0 and not pos:
        step/= 2
        r+= step
    elif npv1<0 and pos:
        step/= 2
        r-= step
    return irr(cfs, r, npv1>0, step)

def npv(cfs, pows, r):
    x = 1/(1+r)**pows
    return x@cfs