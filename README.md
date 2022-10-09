# Intro
 This is a DeGiro analytics platform. DeGiro is a low-fee Dutch investment broker that, sadly, offers limited account analytics functionality. This project leverages DeGiro's private API and provides some investment performance analytics tools.

# Installation

`pip install degiro_analytics`

# Requirments

 The project is built in `conda 4.12.0` environment.  
 # Description
 
 `degiro_analytics/DegiroWrapper.py` contains API to retrieve current portfolio information and product search. It does not include trading API. There are open-source projects implementing trading API. 

`degiro_analytics/utils.py` contains various methods for portfolio analytics.

`Examples.ipynb` Refer to this Jupyter Notebook for examples.