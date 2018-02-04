#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from multiprocessing.dummy import Pool
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
OrderFilledSelled = 2
OrderExitSelled = 3
OrderCancel = 4
OrderSell = 5

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
        'sellTime'       : timestamp(),
        'sellID'        : order.getId(),
        'sellPrice'     : order.getPrice(),
        'sellAmount'    : order.getAmount(),
        'selledAmount'  : 0,
        'selledFee'     : 0,
        'sellStatus'    : OrderSell,
    }

def getPnl(order):
    sellUsdt = 0
    for sellOrder in order['sellOrders']:
        sellUsdt += sellOrder['sellPrice']*sellOrder['selledAmount']-sellOrder['selledFee']
    buyUsdt = order['selledAmount']*order['buyPrice']/0.998
    return (sellUsdt-buyUsdt)/buyUsdt


def updateBuyOrder(order):
    orderInfo = broker.getUserTransactions([order['buyID']])[0]
    order['buyedAmount'] = orderInfo.getBTC() - orderInfo.getFee()
    if orderInfo.isFilled():
        order['buyStatue'] = OrderBuyed   

def exitSellOrders(orderIDs):
    for oid in orderIDs:
        broker.cancelOrder(oid)

def updateSellOrder(symbol, order, price, pricePrecision, amountPrecision, minAmount):
    sellPrice = order['sellPrice']
    if len(order['sellOrders']):
        minPrice = 10**-pricePrecision
        sellPrice = round(price - minPrice, pricePrecision)
    cancelIds = []
    for sellOrder in order['sellOrders']:
        if sellOrder['sellStatus'] == OrderSell and ((sellOrder['sellPrice'] > price and price >= order['sellPriceMin']) or timestamp() - sellOrder['sellTime'] > 300):
            sellOrder['sellStatus'] = OrderCancel
            cancelIds.append(sellOrder['sellID'])
    exitSellOrders(cancelIds)

    openOrderAmount = 0
    filledOrderAmount = 0
    selledAmount = 0
    for sellOrder in order['sellOrders']:
        if sellOrder['sellStatus'] in (OrderSell, OrderCancel):
            orderInfo = broker.getUserTransactions([sellOrder['sellID']])[0]
            sellOrder['selledAmount'] = orderInfo.getBTC()
            sellOrder['selledFee'] = orderInfo.getFee()
            if sellOrder['sellStatus'] == OrderCancel:
                sellOrder['sellStatus'] = OrderExitSelled
        if sellOrder['sellStatus'] == OrderSell:
            openOrderAmount += sellOrder['sellAmount']
        else:
            filledOrderAmount += sellOrder['selledAmount']
        selledAmount += sellOrder['selledAmount']

    order['selledAmount'] = selledAmount
    newAmount = order['buyedAmount'] - openOrderAmount - filledOrderAmount
    newAmount = RoundDown(newAmount, amountPrecision)
    if newAmount >= minAmount:
        sellOrder = buildSellOrder(symbol, newAmount, sellPrice)
        order['sellOrders'].append(sellOrder)
        order['sellAmount'] = openOrderAmount + filledOrderAmount + newAmount

    if (order['buyStatue'] in (OrderBuyed, OrderCancel)) and order['buyedAmount'] - order['selledAmount'] < minAmount:
        if order['buyStatue'] == OrderBuyed:
            order['buyStatue'] = OrderFilledSelled
        else:
            order['buyStatue'] = OrderExitSelled

def exitBuyOrder(order):
    broker.cancelOrder(order['buyID'])
    order['buyStatue'] = OrderCancel

# polling trade order
#def executeOrder(coin, bidPrice, askPrice):
def executeOrder(coin, bids, asks):
    pricePrecision = coin['price-precision']
    minPrice = 10**-pricePrecision
    bidPrice,bidAmount = bids[0]
    askPrice,askAmount = asks[0]
    bidPrice = RoundUp(bidPrice, pricePrecision)
    askPrice = RoundDown(askPrice, pricePrecision)
    order = coin['execOrder']
    if order['buyStatue'] == OrderBuy:
        curTime = timestamp()
        bidPrice1,bidAmount1 = bids[1]
        if askPrice <= order['sellPriceMin'] or bidPrice - bidPrice1 > minPrice or bidPrice > order['buyPrice'] or curTime - order['buyTime'] > 120:
            exitBuyOrder(order)
            print('---askPrice:%f minPrice:%f curTiem:%d orderTime:%d'%(askPrice, order['sellPriceMin'], curTime, order['buyTime']))
            logger.info('exitBuyOrder: %s'%coin['symbol'])
        logger.info('updateBuyOrder: %s'%coin['symbol'])
        updateBuyOrder(order)
    amountPrecision = coin['amount-precision']
    updateSellOrder(coin['symbol'], order, askPrice, pricePrecision, coin['amount-precision'], coin['minAmount'])
    logger.info('updateSellOrder: %s'%coin['symbol'])
    logger.info('orderInfo: %s buy:%f filled:%f sell:%f filled:%f'%(coin['symbol'], order['buyAmount'], order['buyedAmount'], order['sellAmount'], order['selledAmount'] ))
    if order['buyStatue'] in (OrderFilledSelled, OrderExitSelled):
        if order['buyStatue'] == OrderFilledSelled:
            if getPnl(order) > 0:
                coin['dealNum'] += 1
            else:
                coin['dealNum'] -= 2
        showOrders(coin)
        coin['execOrder'] = None

# coin
# bids: buy  price
# asks: sell price
def onDepth(coin, bids, asks):
    if coin['dealNum'] < 0:
        return
    bidPrice,bidAmount = bids[0]
    askPrice,askAmount = asks[0]
    pricePrecision = coin['price-precision']
    minPrice = 10**-pricePrecision
    bidPrice += minPrice
    askPrice -= minPrice
    bidPrice = RoundUp(bidPrice, pricePrecision)
    askPrice = RoundDown(askPrice, pricePrecision)
    logger.info("------onDepth bid:%f ask:%f"%(bidPrice, askPrice))
    coin['percent'] = percent = RoundDown(0.996*askPrice/bidPrice - 1, 4)
    if coin['execOrder'] is None:
        if percent >= 0.0006:
            minAmount = coin['minAmount']
            buyAmount = coin['minLoseAmount'] * coin['dealNum']
            if coin['dealNum'] == 0 or buyAmount < minAmount:
                buyAmount = minAmount * 2
            amountPrecision = coin['amount-precision']
            buyAmount = RoundDown(buyAmount, amountPrecision)
            sellExitPrice = RoundUp(bidPrice/0.996, pricePrecision)
            logger.info('---------------%s---------------'%coin['symbol'])
            logger.info('%f %f %f %f %f'%(percent, bidPrice, askPrice, buyAmount, sellExitPrice))
            coin['execOrder'] = buildBuyOrders(coin['symbol'], buyAmount, bidPrice, askPrice, sellExitPrice)
    else:
        #executeOrder(coin, _bidPrice, _askPrice)
        executeOrder(coin, bids, asks)

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

    f = lambda x:round((10**(3-x))/2.0, x)
    minLoseAmount = f(x['amount-precision'])
    logger.info('%s : %s %s'%(symbol, minAmount, minLoseAmount))

    return {
        'part'              : x['symbol-partition'],
        'coin'              : baseCurrency,
        'money'             : quoteCurrency,
        'symbol'            : symbol,
        'price-precision'   : x['price-precision'],
        'amount-precision'  : amountPrecision,
        'minAmount'         : minAmount,
        'minLoseAmount'     : minLoseAmount,
        'percent'           : 0,
        'execOrder'         : None,
        'dealNum'           : 0,
    }

def getDepth(coin):
    while True:
        try:
            depth = client.mget('/market/depth', rkey='tick', symbol=coin['symbol'], type='step1')
            onDepth(coin, depth.bids, depth.asks)
            return coin
        except:
            logger.info('------------EXCEPT------------')
            logger.info(coin['symbol'])
            logger.info(traceback.format_exc())
            logger.info('------------======------------')
            time.sleep(1)

def ThreadRun(coin):
    while coin['dealNum'] >= 0:
        coin = getDepth(coin)
        time.sleep(1)
    logger.info('-------%s exit Thread'%coin['symbol'])

def main():
    logger.info('******************GetSymbols******************')
    allSymbol = client.mget('/v1/common/symbols')
    coins = map(coinType, filter(lambda x:x['quote-currency'] == 'usdt', allSymbol))
    #coins = map(coinType, filter(lambda x:x['quote-currency'] == 'usdt' and x['base-currency'] == 'dash', allSymbol))

    #coins = map(coinType, allSymbol)


    pool = Pool(len(coins))
    pool.map(ThreadRun, coins)
    pool.close()
    pool.join()
    '''
    while True:
        logger.info('**********************************************')
        coins = map(getDepth, coins)
        coins.sort(key=lambda x:x['percent'], reverse=True)
        time.sleep(1)
    '''

main()

