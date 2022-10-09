# Intro
 This is a DeGiro analytics platform. DeGiro is a low fee Dutch investment broker, which, unfortunately, offers a limited account analytics capabilities. This project leverages DeGiro's private API and provides some investment perfomance analytics tools.

# Instalation

`pip install degiro_analytics`

# Requirments

 The project is built in `conda 4.12.0` environmnet.  
 # Description
 
 `degiro_analytics/DegiroWrapper.py` contains API to retrieve current portfolio information and product saearch. It does not contain trading API. There are open source projects implementing trading API. 

`degiro_analytics/utils.py` contains various methods for portfolio analytics

`Examples.ipynb` Refer to this Jupyter Notebook for examples.
 