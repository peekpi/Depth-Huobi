#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import traceback
import time
import hbClient as hbc
from hbsdk import ApiError
from liveApi.liveUtils import *
from liveApi import liveLogger

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


def buildBuyOrders(symbol, buyAmount, buyPrice, sellPrice, sellPriceExit):
    order = broker.buyLimit(symbol, buyPrice, buyAmount)
    return{
        'buyTime'       : timestamp(),
        'buyID'         : order.getId(),
        'buyStatue'     : OrderBuy,
        'buyPrice'      : order.getPrice(),
        'buyAmount'     : order.getAmount(),
        'buyedAmount'   : 0,
        'sellPrice'     : sellPrice,
        'sellPriceMin'  : sellPriceExit,
        'sellAmount'    : 0,
        'selledAmount'  : 0,
        'sellOrders'    : [],
    }
# buyedAmount = sellAmount

# sell Order
def buildSellOrder(symbol, amount, price):
    order = broker.sellLimit(symbol, price, amount)
    return {
        'sellID'        : order.getId(),
        'sellPrice'     : order.getPrice(),
        'sellAmount'    : order.getAmount(),
        'selledAmount'  : 0,
    }

def updateBuyOrder(order):
    orderInfo = broker.getUserTransactions([order['buyID']])[0]
    order['buyedAmount'] = orderInfo.getBTC() - orderInfo.getFee()
    if orderInfo.isFilled():
        order['buyStatue'] = OrderBuyed   

def updateSellOrder(symbol, order, price, amountPrecision, minAmount):
    newAmount = order['buyedAmount'] - order['sellAmount']
    newAmount = RoundDown(newAmount, amountPrecision)
    if newAmount >= minAmount:
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
    if (order['buyStatue'] in (OrderBuyed, OrderCancel)) and order['buyedAmount'] - order['selledAmount'] < minAmount:
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
            print('---askPrice:%f minPrice:%f curTiem:%d orderTime:%d'%(askPrice, order['sellPriceMin'], curTime, order['buyTime']))
            logger.info('exitBuyOrder: %s'%coin['symbol'])
            exitBuyOrder(order)
        logger.info('updateBuyOrder: %s'%coin['symbol'])
        updateBuyOrder(order)

    amountPrecision = coin['amount-precision']
    updateSellOrder(coin['symbol'], order, max(askPrice, order['sellPriceMin']), coin['amount-precision'], coin['minAmount'])
    logger.info('updateSellOrder: %s'%coin['symbol'])
    logger.info('orderInfo: %s buy:%f filled:%f sell:%f filled:%f'%(coin['symbol'], order['buyAmount'], order['buyedAmount'], order['sellAmount'], order['selledAmount'] ))
        
    if order['buyStatue'] == OrderSelled:
        showOrders(coin)
        coin['execOrder'] = None
    
# coin
# bids: buy  price
# asks: sell price
def onDepth(coin, bids, asks):
    bidPrice,bidAmount = bids
    askPrice,askAmount = asks
    pricePrecision = coin['price-precision']
    minPrice = 10**-pricePrecision
    bidPrice += minPrice
    askPrice -= minPrice
    bidPrice = RoundUp(bidPrice, pricePrecision)
    askPrice = RoundDown(askPrice, pricePrecision)
    coin['percent'] = percent = round(0.995*askPrice/bidPrice - 1, 4)
    if coin['execOrder'] is None:
        if percent >= 0.001:
            minAmount = coin['minAmount']
            buyAmount = minAmount*2
            if buyAmount*bidPrice > 10:
                return
            amountPrecision = coin['amount-precision']
            buyAmount = RoundDown(buyAmount, amountPrecision)
            sellExitPrice = RoundUp(bidPrice/0.995, pricePrecision)
            logger.info('---------------%s---------------'%coin['symbol'])
            logger.info('%f %f %f %f %f'%(percent, bidPrice, askPrice, buyAmount, sellExitPrice))
            coin['execOrder'] = buildBuyOrders(coin['symbol'], buyAmount, bidPrice, askPrice, sellExitPrice)
    else:
        executeOrder(coin, bidPrice, askPrice)

@hbc.tryForever
def coinType(x):
    baseCurrency = x['base-currency']
    quoteCurrency = x['quote-currency']
    symbol = baseCurrency + quoteCurrency
    amountPrecision = x['amount-precision']
    minAmount = 10**-amountPrecision
    try:
        broker.getMinAmount(symbol, minAmount)
    except ApiError, e:
        msgs = e.message.split(':')
        if msgs[0] == "order-limitorder-amount-min-error" and len(msgs) == 3:
            strAmount = msgs[-1].split('`')[1]
            minAmount = float(strAmount)

    logger.info('%s : %s'%(symbol, minAmount))

    return {
        'part'              : x['symbol-partition'],
        'coin'              : baseCurrency,
        'money'             : quoteCurrency,
        'symbol'            : symbol,
        'price-precision'   : x['price-precision'],
        'amount-precision'  : amountPrecision,
        'minAmount'         : minAmount,
        'percent'           : 0,
        'execOrder'         : None,
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
    logger.info('******************GetSymbols******************')
    allSymbol = client.mget('/v1/common/symbols')
    #coins = filter(lambda x:x['part'] == 'main' and x['money'] == 'usdt', map(coinType, allSymbol))
    coins = map(coinType, filter(lambda x:x['quote-currency'] == 'usdt', allSymbol))
    #coins = map(coinType, allSymbol)
    while True:
        logger.info('**********************************************')
        coins = map(getDepth, coins)
        coins.sort(key=lambda x:x['percent'], reverse=True)
        time.sleep(1)

main()

