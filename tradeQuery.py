import hbClient as hbc
import json
from liveApi.liveUtils import *
from pyalgotrade.utils import dt
import datetime
import os

broker = hbc.hbTradeClient()
client = broker.getClient()

sdate = dt.localize(datetime.datetime(2018, 2, 3, 22, 16), localTz)
edate = dt.localize(datetime.datetime(2018, 2, 4, 15, 00), localTz)
stime = int(dt.datetime_to_timestamp(sdate))
sdir =  'tradeOrders-%s'%sdate.strftime('%m%d_%H%M')
print stime,sdate,sdir
try:
    os.mkdir(sdir)
except:
    pass

@hbc.tryForever
def getTradeOrder(x):
    symbol = x['base-currency'] + x['quote-currency']
    tradeInfo = client.get('/v1/order/orders', **{'symbol':symbol, 'states':'partial-canceled,filled', 'types':'buy-limit,sell-limit', 'start-date':sdate.strftime('%Y-%m-%d'), 'end-date':edate.strftime('%Y-%m-%d')})
    apiOrder = filter(lambda x:x['source'] == 'api' and int(x['finished-at']/1000) > stime, tradeInfo)
    json.dump(apiOrder, file('%s/%s.json'%(sdir, symbol), 'w'))


allSymbol = client.mget('/v1/common/symbols')
map(getTradeOrder, filter(lambda x:x['quote-currency'] == 'usdt', allSymbol))
