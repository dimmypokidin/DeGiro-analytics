# Intro
 This is a DeGiro analytics platform. DeGiro is a low-fee Dutch investment broker that, sadly, offers limited account analytics functionality. This project leverages DeGiro's private API and provides some investment performance analytics tools.

# Installation

`pip install degiro_analytics`

# Requirments

 `pandas>=1.4.2`
`requests>=2.27.1`
 # Description
 
 `degiro_analytics/DegiroWrapper.py` contains API to retrieve current portfolio information and product search. It does not include trading API. There are open-source projects implementing trading API. 

`degiro_analytics/utils.py` contains various methods for portfolio analytics.

`Examples.ipynb` Refer to this Jupyter Notebook for examples.

# Examples


```python
import pandas as pd
from degiro_analytics import DeGiroWrapper
from degiro_analytics.utils import irr, analytics
DGW = DeGiroWrapper(True, True, base_curr='EUR') # you will have to provide your credentials (and possibly multi-factor auth code)
```

## Insights into your portfolio


```python
pf = DGW.get_current_portfolio() # retrieves your current portfolio
```

Get price history of your portfolio constituents


```python
P = DGW.get_prices(pf.index)
P = P.pivot(index='date', columns='name', values='price')
P = P.apply(lambda x: x/x.dropna().iloc[0]) # normalize by starting price
P.plot(title='Portfolio constituents perfomance', figsize=(15, 7))
```

    
![png](img/Examples_5_1.png)
    


## Perfomance of your account


```python
start_date = '01/01/2020' # use any date
T = DGW.get_transactions(start_date) # trasactions history
P = DGW.get_prices(T.productId.unique()) # get price history of all products from T
P = P[P.date>=T.date.min()]
P = pd.pivot_table(P, index='date', columns='productId', values='price', aggfunc='mean') # product per columns
P.fillna(method='ffill', inplace=True)
```


```python
Q = pd.pivot_table(T, index='date', columns='productId', values='quantity', aggfunc='sum') # number of shares purchased, product per column
Q = Q.reindex(P.index.append(Q.index)).sort_index().fillna(0).cumsum() # portfolio quantities per day
```


```python
idx = P.index.get_indexer(Q.index, method='nearest')
matched_P = P.iloc[idx].values
```

The following cell computes portfolio returns as $R_t = \frac{Q_{t-1}'P_t}{Q_{t-1}'P_{t-1}}$.


```python
numerator = Q.shift().multiply(matched_P).sum(axis=1)
denominator = Q.multiply(matched_P).sum(axis=1).shift()
R = numerator/denominator
```


```python
IDX = R.fillna(1).cumprod() # index (or normalized price) of the portfolio
IDX.plot(title='Account Portfolio Perfomance', figsize=(15, 7))
```

    
![png](img/Examples_12_1.png)
    


Some analytics


```python
analytics(IDX) 
```




    {'Mean return': 0.00027660251717962994,
     'Std': 0.010483131903391498,
     'Risk Adjusted Return': 0.02638548477007559,
     'Number of drawdowns': 28,
     'Maximum Drawdown': 0.25730401117784857,
     'Max drawdown duration (days)': 320,
     'Mean drawdown duration (days)': 26.035714285714285,
     'T': 570}



Cash Flows analysis and money weighted return (IRR)


```python
cf_df = DGW.get_account_cash_flows('01/01/2000', fees=True, dividends=True)
cf = cf_df.set_index('date').CF
cf.loc[pd.to_datetime(DGW.today, dayfirst=True, utc=True)] = pf.Q.multiply(pf.price_base_curr).sum() # current portfolio value
```


```python
mwr = irr(cf)
print('Money weighted return is', mwr)
```

    Money weighted return is 0.008600000000000003


## Search products


```python
search_text = 'Microsoft'
product = DGW.lookup(search_text, limit=1)[0]
print('The current price of', product.name, 'is', product.closePrice, product.currency)
p = product.get_price_hist(convert=False).set_index('date').price
p.plot(title=product.name, figsize=(15,7))
```

    The current price of Microsoft Corp is 229.25 USD

    
![png](img/Examples_19_2.png)
    



```python
search_text = 'Apple'
product = DGW.lookup(search_text, limit=1)[0]
print('The current price of', product.name, 'is', product.closePrice, product.currency)
p = product.get_price_hist(history='1D', resolution='T1M', convert=False).set_index('date').price
p.plot(title=product.name + ' (intraday pricing)', figsize=(15,7))
```

    The current price of Apple Inc is 140.42 USD

    
![png](img/Examples_20_2.png)
    


## Search and analyze ETFs from core selection


```python
etfs = DGW.search_etfs(only_free=True, limit=200) # returns all ETFs from DeGiro core selection
```

Loop through the ETFs and analyze the prices


```python
out = []
for etf in etfs:
    p = etf.get_price_hist(resolution='1M')
    a = analytics(p.set_index('date').price)
    a['name'] = etf.name
    out.append(a)
```


```python
pd.DataFrame(out).sort_values('Risk Adjusted Return')
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Mean return</th>
      <th>Std</th>
      <th>Risk Adjusted Return</th>
      <th>Number of drawdowns</th>
      <th>Maximum Drawdown</th>
      <th>Max drawdown duration (days)</th>
      <th>Mean drawdown duration (days)</th>
      <th>T</th>
      <th>name</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>185</th>
      <td>-0.003599</td>
      <td>0.024421</td>
      <td>-0.147393</td>
      <td>6</td>
      <td>0.315074</td>
      <td>1278</td>
      <td>375.333333</td>
      <td>80</td>
      <td>Xtrackers USD Corporate Bond UCITS ETF 2D HEUR</td>
    </tr>
    <tr>
      <th>100</th>
      <td>-0.001715</td>
      <td>0.012107</td>
      <td>-0.141665</td>
      <td>5</td>
      <td>0.163109</td>
      <td>852</td>
      <td>329.000000</td>
      <td>59</td>
      <td>iShares Core Gl Aggregate Bd UCITS ETF EUR Hgd...</td>
    </tr>
    <tr>
      <th>190</th>
      <td>-0.012569</td>
      <td>0.095570</td>
      <td>-0.131513</td>
      <td>2</td>
      <td>0.624981</td>
      <td>699</td>
      <td>380.000000</td>
      <td>27</td>
      <td>The Medical Cannabis and Wellness UCITS ETF Acc</td>
    </tr>
    <tr>
      <th>178</th>
      <td>-0.012005</td>
      <td>0.106949</td>
      <td>-0.112248</td>
      <td>2</td>
      <td>0.649046</td>
      <td>699</td>
      <td>380.000000</td>
      <td>27</td>
      <td>Rize Medical Cannabis and Life Sciences UCITS ETF</td>
    </tr>
    <tr>
      <th>106</th>
      <td>-0.001573</td>
      <td>0.015111</td>
      <td>-0.104113</td>
      <td>4</td>
      <td>0.207632</td>
      <td>1064</td>
      <td>578.250000</td>
      <td>80</td>
      <td>Vanguard EUR Eurozone Government Bd UCITS ETF EUR</td>
    </tr>
    <tr>
      <th>...</th>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th>72</th>
      <td>0.015837</td>
      <td>0.052422</td>
      <td>0.302098</td>
      <td>14</td>
      <td>0.243017</td>
      <td>396</td>
      <td>139.357143</td>
      <td>78</td>
      <td>SPDR MSCI World Technology UCITS ETF</td>
    </tr>
    <tr>
      <th>63</th>
      <td>0.012074</td>
      <td>0.038280</td>
      <td>0.315414</td>
      <td>23</td>
      <td>0.176644</td>
      <td>518</td>
      <td>166.782609</td>
      <td>149</td>
      <td>Amundi S&amp;P 500 UCITS ETF- EUR (C)</td>
    </tr>
    <tr>
      <th>14</th>
      <td>0.015172</td>
      <td>0.046238</td>
      <td>0.328118</td>
      <td>21</td>
      <td>0.239507</td>
      <td>365</td>
      <td>175.523810</td>
      <td>142</td>
      <td>iShares NASDAQ 100 UCITS ETF USD (Acc)</td>
    </tr>
    <tr>
      <th>172</th>
      <td>0.023167</td>
      <td>0.070230</td>
      <td>0.329876</td>
      <td>3</td>
      <td>0.271599</td>
      <td>365</td>
      <td>284.333333</td>
      <td>31</td>
      <td>Lyx Msci Future Etf</td>
    </tr>
    <tr>
      <th>149</th>
      <td>0.025988</td>
      <td>0.065900</td>
      <td>0.394360</td>
      <td>3</td>
      <td>0.238976</td>
      <td>365</td>
      <td>294.333333</td>
      <td>32</td>
      <td>WisdomTree Battery Solutions UCITS ETF USD Acc</td>
    </tr>
  </tbody>
</table>
<p>198 rows × 9 columns</p>
</div>
