from iexfinance.stocks import Stock
from datetime import datetime

def get_book(ID):
    appl = Stock(ID,token = "pk_67bb48c25c294c459b9ca4f19636510a")
    x=appl.get_book()
    return x
def get_historical_prices(ID):
    appl = Stock(ID,token = "pk_67bb48c25c294c459b9ca4f19636510a")
    x=appl.get_historical_prices()
    return x

def get_previous_day_prices(ID):
    appl = Stock(ID,token = "pk_67bb48c25c294c459b9ca4f19636510a")
    x=appl.get_previous_day_prices()
    return x