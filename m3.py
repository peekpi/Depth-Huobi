#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import traceback
import time

from hbsdk import ApiClient, ApiError

API_KEY = "API_KEY"
API_SECRET = "API_SECRET"

client = ApiClient(API_KEY, API_SECRET)

# coin
# bids: buy  price
# asks: sell price
def onDepth(coin, bids, asks):
    print('---------------%s---------------'%coin['coin'])
    bidPrice,bidAmount = bids
    askPrice,askAmount = asks
    bidPrice += coin['minPrice']
    askPrice -= coin['minPrice']
    percent = round(0.996004*askPrice/bidPrice - 1, 4)
    print('%f %f %f'%(percent,bidPrice,askPrice))
    return percent

def coinType(x):
    return {
        'part' : x['symbol-partition'],
        'coin' : x['base-currency'],
        'money' : x['quote-currency'],
        'symbol' : x['base-currency'] + x['quote-currency'],
        'minPrice': 10**-x['price-precision'],
        'minAmount': 10**-x['amount-precision'],
        'percent': 0,
    }

def getDepth(coin):
    while True:
        try:
            depth = client.mget('/market/depth', rkey='tick', symbol=coin['symbol'], type='step1')
            bids,asks = depth.bids[0],depth.asks[0]
            coin['percent'] = onDepth(coin, bids, asks)
            return coin
        except:
            print('------------EXCEPT------------')
            print(traceback.print_exc())
            print('------------======------------')
            time.sleep(1)

def main():
    allSymbol = client.mget('/v1/common/symbols')
    coins = filter(lambda x:x['part'] == 'main' and x['money'] == 'usdt', map(coinType, allSymbol))
    while True:
        print('**********************************************')
        coins = map(getDepth, coins)
        coins.sort(key=lambda x:x['percent'], reverse=True)
        time.sleep(1)

main()
