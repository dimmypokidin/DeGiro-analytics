# Intro
 This is a DeGiro analytics platform. DeGiro is a low fee Dutch investment broker, which is, unfortunately, offers a limited account analytics capabilities. This project leverages DeGiro's private API and provides some perfomance analytics tools.

# Requirments

 The project is built in `conda 4.12.0` environmnet.  
 # Description
 
 `src/DegiroWrapper.py` contains basic API to retrieve current portfolio information and product saearch. It does not contain trading API. For a more extensive API see [this project](https://github.com/lolokraus/DegiroAPI).

`src/utils.py` contains various methods for portfolio analytics

`Examples.ipynb` Jupyter notebook containing some use cases
 