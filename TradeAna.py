import json
from datetime import datetime
from liveApi import liveUtils
from liveApi.liveUtils import *
from pyalgotrade.utils import dt
import os

sdate = dt.localize(datetime(2018, 2, 3, 22, 16), localTz)
sdir =  'tradeOrders-%s'%sdate.strftime('%m%d_%H%M')

def getAllJsonFile(path):
    return map(lambda x:os.path.join(path, x), filter(lambda x:x.split('.')[-1]=='json', os.listdir(path)))

def Str2float(func):
    def waper(*args, **kwargs):
        return float(func(*args, **kwargs))
    return waper

class TradeInfo():
    def __init__(self, dic):
        self.__d = dic
    def creatTime(self):
        return datetime.fromtimestamp(self.__d['created-at']/1000) 
    def cancleTime(self):
        return datetime.fromtimestamp(self.__d['canceled-at']/1000) 
    def finishedTime(self):
        return datetime.fromtimestamp(self.__d['finished-at']/1000)
    @Str2float
    def getPrice(self):
        return self.__d['price']
    @Str2float
    def getFee(self):
        return self.__d['field-fees']
    def isBuy(self):
        return self.__d['type'] == 'buy-limit'
    def isSell(self):
        return self.__d['type'] == 'sell-limit'
    def getSymbol(self):
        return self.__d['symbol']
    @Str2float
    def getAmount(self):
        return self.__d['amount']
    @Str2float
    def getAmountFilled(self):
        return self.__d['field-amount']
    @Str2float
    def getUsdtField(self):
        return self.__d['field-cash-amount']
    def fromApi(self):
        return self.__d['source'] == 'api'
    def isFilled(self):
        return self.__d['state'] in ['filled', 'partial-canceled']

def getJson(name):
    return json.load(file(name, 'r'))

tc = 0
tb = 0
ts = 0
tf = 0
def cal(symbol):
    global tc,tb,ts,tf
    #obj = getJson('tradeOrders/cvcusdt.json')
    obj = map(TradeInfo, getJson(symbol))
    obj = filter(lambda x:x.fromApi() and x.isFilled(), obj)
    if len(obj) < 1:
        return
    #if obj[0].isBuy():
    #    obj.pop(0)
    buyCash = 0
    sellCash = 0
    feeCash = 0
    for info in obj:
        tc+=1
        if info.isBuy():
            print('-buy  [%s] - [%s] <%s>'%(info.creatTime(), info.finishedTime(), info.finishedTime() - info.creatTime()))
            buyCash += info.getUsdtField()
        else:
            print('+sell [%s] - [%s] <%s>'%(info.creatTime(), info.finishedTime(), info.finishedTime() - info.creatTime()))
            sellCash += info.getUsdtField()
            feeCash += info.getFee()
    tb += buyCash
    ts += sellCash
    tf += feeCash
    print('%s - %d buy:%f sell:%f fee:%f e:%f te:%f'%(symbol, len(obj), buyCash, sellCash, feeCash, sellCash-buyCash-feeCash, ts-tb-tf))

#cal('tradeOrders/sntusdt.json')
#cal('tradeOrders/gntusdt.json')
map(cal, getAllJsonFile(sdir))
print '%d buy:%f sell:%f fee:%f e:%f'%(tc, tb, ts, tf, ts-tb-tf)

