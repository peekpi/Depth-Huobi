#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import traceback
import time
import hbClient as hbc
from liveApi import liveLogger
from hbsdk import ApiError
import json

from liveApi.commonApi import getKLineBar

logger = liveLogger.getLiveLogger("strategy")

broker = hbc.hbTradeClient()
client = broker.getClient()

OrderBuy = 0
OrderBuyed = 1
OrderSelled = 2
OrderCancel = 3

def timestamp():
    return int(time.time())

def showOrders(coin):
    order = coin['execOrder']
    symbol = coin['symbol']
    logger.info("------symbol:%s-%d------"%(symbol, timestamp()))
    logger.info('Order: %s'%order)


def buildBuyOrders(symbol, buyAmount, buyPrice, sellPrice):
    order = broker.buyLimit(symbol, buyPrice, buyAmount)
    return{
    'buyTime' : timestamp(),
    'buyID' : order.getId(),
    'buyStatue': OrderBuy,
    'buyPrice' : order.getPrice(),
    'buyAmount' : order.getAmount(),
    'buyedAmount' : 0,
    'sellPrice' : sellPrice,
    'sellPriceMin' : buyPrice/0.996004,
    'sellAmount' : 0,
    'selledAmount' : 0,
    'sellOrders' : [],
    }
# buyedAmount = sellAmount

# sell Order
def buildSellOrder(symbol, amount, price):
    order = broker.sellLimit(symbol, price, amount)
    return {
        'sellID': order.getId(),
        'sellPrice': order.getPrice(),
        'sellAmount': order.getAmount(),
        'selledAmount': 0,
    }

def updateBuyOrder(order):
    orderInfo = broker.getUserTransactions([order['buyID']])[0]
    order['buyedAmount'] = orderInfo.getBTC() - orderInfo.getFee()
    if orderInfo.isFilled():
        order['buyStatue'] = OrderBuyed   

def updateSellOrder(symbol, order, price):
    newAmount = order['buyedAmount'] - order['sellAmount']
    if newAmount:
        sellOrder = buildSellOrder(symbol, newAmount, price)
        order['sellOrders'].append(sellOrder)
        order['sellAmount'] += sellOrder['sellAmount']
    selledAmount = 0
    for sellOrder in order['sellOrders']:
        # if filed then
        if sellOrder['selledAmount'] < sellOrder['sellAmount']:
            orderInfo = broker.getUserTransactions([sellOrder['sellID']])[0]
            sellOrder['selledAmount'] = orderInfo.getBTC()
        selledAmount += sellOrder['selledAmount']
    order['selledAmount'] = selledAmount
    if order['buyStatue'] == OrderBuyed and order['selledAmount'] == order['buyedAmount']:
        order['buyStatue'] = OrderSelled

def exitBuyOrder(order):
    broker.cancelOrder(order['buyID'])
    order['buyStatue'] = OrderCancel
    
    

# polling trade order
def executeOrder(coin, bidPrice, askPrice):
    curTime = timestamp()
    order = coin['execOrder']
    if order['buyStatue'] == OrderBuy:
        if askPrice <= order['sellPriceMin'] or curTime - order['buyTime'] > 300:
            exitBuyOrder(order)
        updateBuyOrder(order)

    updateSellOrder(coin['symbol'], order, askPrice)
        
    if order['buyStatue'] == OrderSelled:
        showOrders(coin)
        coin['execOrder'] = None
    
# coin
# bids: buy  price
# asks: sell price
def onDepth(coin, bids, asks):
    bidPrice,bidAmount = bids
    askPrice,askAmount = asks
    bidPrice += coin['minPrice']*2
    askPrice -= coin['minPrice']*2
    coin['percent'] = percent = round(0.996004*askPrice/bidPrice - 1, 4)
    if coin['execOrder'] is None:
        if percent > 0.001:
            buyAmount = 2/bidPrice
            coin['execOrder'] = buildBuyOrders(coin['symbol'], buyAmount, bidPrice, askPrice)
            logger.info('---------------%s---------------'%coin['symbol'])
            logger.info('%f %f %f %f'%(percent,bidPrice,askPrice, buyAmount))
    else:
        executeOrder(coin, bidPrice, askPrice)

@hbc.tryForever
def coinType(x):
    symbol = x['base-currency'] + x['quote-currency']
    klines = client.mget('/market/history/kline', symbol=symbol, period='%dmin'%1, size=2000)
    print '----%s %d'%(symbol, len(klines))
    json.dump(klines, file('kline/%s-%d.txt'%(symbol, len(klines)), 'w'))
    minAmount = 10**-x['amount-precision']
    try:
        broker.getMinAmount(symbol, minAmount)
    except ApiError, e:
        msgs = e.message.split(':')
        if msgs[0] == "order-limitorder-amount-min-error" and len(msgs) == 3:
            strAmount = msgs[-1].split('`')[1]
            minAmount = float(strAmount)
    f = lambda x:round((10**(3-x))/4.0, x) if x else int((10**(3-x))/4.0)
    minLoseAmount = f(x['amount-precision'])
    return {
        'part' : x['symbol-partition'],
        'coin' : x['base-currency'],
        'money' : x['quote-currency'],
        'symbol' : symbol,
        'price-precision': x['price-precision'],
        'amount-precision': x['amount-precision'],
        'minAmount': minAmount,
        'minLoseAmount': minLoseAmount,
        'percent': 0,
        'execOrder' : None,
    }

def getDepth(coin):
    while True:
        try:
            depth = client.mget('/market/depth', rkey='tick', symbol=coin['symbol'], type='step1')
            bids,asks = depth.bids[0],depth.asks[0]
            onDepth(coin, bids, asks)
            return coin
        except:
            logger.info('------------EXCEPT------------')
            logger.info(coin['symbol'])
            logger.info(traceback.format_exc())
            logger.info('------------======------------')
            time.sleep(1)

def main():
    print('----')
    allSymbol = client.mget('/v1/common/symbols')
    #coins = filter(lambda x:x['part'] == 'main' and x['money'] == 'usdt', map(coinType, allSymbol))
    #coins = map(coinType, filter(lambda x:x['quote-currency'] == 'usdt', allSymbol))
    coins = map(coinType, filter(lambda x:x['quote-currency'] == 'usdt', allSymbol))
    #coins = map(coinType, allSymbol)
    for x in coins:
        print '--------%s--------'%x['symbol']
        for o in x:
            print "%s:%s"%(o, x[o])

main()

