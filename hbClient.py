from liveApi.TradeClientBase import *
from liveApi.liveUtils import *
from pyalgotrade.utils import dt
from liveApi import liveLogger

from hbsdk import ApiClient, ApiError

from ApiKey import API_KEY
from ApiKey import API_SECRET

logger = liveLogger.getLiveLogger("hbClient")

def Str2float(func):
    def waper(*args, **kwargs):
        return float(func(*args, **kwargs))
    return waper

class hbOrderType():
    BuyLimit   = 'buy-limit'
    BuyMarket  = 'buy-market'
    SellLimit  = 'sell-limit'
    SellMarket = 'sell-market'

class hbOrderState():
    OrderFilled = 'filled'
    OrderCanceled = 'canceled'
    OrderSubmited = 'submitted'

class hbTradeOrder(TradeOrderBase):
    def __init__(self, obj):
        self.__obj = obj
        super(hbTradeOrder, self).__init__()

    def getId(self):
        return self.__obj.id
    def isBuy(self):
        return self.__obj.type in (hbOrderType.BuyLimit, hbOrderType.BuyMarket)
    def isSell(self):
        return not self.isBuy()
    @Str2float
    def getPrice(self):
        return self.__obj.price
    @Str2float
    def getAmount(self):
        return self.__obj.amount
    def getDateTime(self):
        return dt.timestamp_to_datetime(int(self.__obj['created-at'])/1000)

# GET /v1/order/orders/{order-id}/matchresults
class hbTradeUserTransaction(TradeUserTransactionBase):
    def __init__(self, obj):
        self.__obj = obj
    @Str2float
    def getBTC(self):
        return self.__obj['field-amount']
    @Str2float
    def getBTCUSD(self):
        #return self.__obj['field-cash-amount']
        return self.__obj['price']
    @Str2float
    def getFee(self):
        return self.__obj['field-fees']
    def getOrderId(self):
        return self.__obj['id']
    def isFilled(self):
        return self.__obj['state'] == hbOrderState.OrderFilled
    def getDateTime(self):
        return dt.timestamp_to_datetime(int(self.__obj['finished-at'])/1000)

class hbCoinType():
    def __init__(self, coin, cash):
        self.__coin = coin
        self.__cash = cash
        self.__symbol = coin+cash
    def getCoin(self):
        return self.__coin
    def getCash(self):
        return self.__cash
    def getSymbol(self):
        return self.__symbol
    def __str__(self):
        return self.getSymbol()

class hbAccountBalance():
    def __init__(self, obj):
        self.__balances = {}
        balancesList = obj.get('list')
        if balancesList is None:
            return
        for x in balancesList:
            self.__balances[x.currency] = x.balance
    @Str2float
    def getCoin(self, coin):
        return self.__balances.get(coin, 0)

class hbTradeClient(TradeClientBase):
    def __init__(self):
        self.__client = ApiClient(API_KEY, API_SECRET)
        self.__accountid = self.getAccountId()

    def getClient(self):
        return self.__client

    @tryForever
    def getAccountId(self):
        accs = self.__client.get('/v1/account/accounts')
        for x in accs:
            if x.type == 'spot' and x.state == 'working':
                return x.id
        raise Exception('no active account ID!')
        
    @tryForever
    def getAccountBalance(self, coinType):
        balances = self.__client.get('/v1/account/accounts/%s/balance' % self.__accountid)
        return hbAccountBalance(balances)

    @tryForever
    def cancelOrder(self, orderId):
        logger.info('cancelOrder:%s'%orderId)
        try:
            self.__client.post('/v1/order/orders/%s/submitcancel' % orderId)
        except:
            self.__checkOrderState(orderId, [hbOrderState.OrderCanceled, hbOrderState.OrderFilled])
                

    def buyLimit(self, symbol, limitPrice, quantity):
        logger.info('buyLimit: %s %s %s'%(symbol, limitPrice, quantity))
        orderInfo = self.__postOrder(symbol, limitPrice, quantity, hbOrderType.BuyLimit)
        return hbTradeOrder(orderInfo)

    def sellLimit(self, symbol, limitPrice, quantity):
        logger.info('sellLimit: %s %s %s'%(symbol, limitPrice, quantity))
        orderInfo = self.__postOrder(symbol, limitPrice, quantity, hbOrderType.SellLimit)
        return hbTradeOrder(orderInfo)

    @tryForever
    def getUserTransactions(self, ordersId):
        if len(ordersId):
            logger.info('getUserTransactions:%s'%ordersId)
        ret = []
        for oid in ordersId:
            orderInfo = self.__client.get('/v1/order/orders/%s' % oid)
            ret.append(hbTradeUserTransaction(orderInfo))
        return ret

    @tryForever
    def __postOrder(self, symbol, limitPrice, quantity, orderType):
        order_id = self.__client.post('/v1/order/orders', {
            'account-id': self.__accountid,
            'amount': quantity,
            'price': limitPrice,
            'symbol': symbol,
            'type': orderType,
            'source': 'api'
        })
        self.__activeOrder(order_id)
        while True:
            try:
                orderInfo = self.__checkOrderState(order_id, [hbOrderState.OrderSubmited, hbOrderState.OrderFilled])
                break
            except:
                continue
        return orderInfo

    def __checkOrderState(self, orderid, states):
        orderInfo = self.__client.get('/v1/order/orders/%s' % orderid)
        if orderInfo.state in states:
            return orderInfo
        raise Exception('wait state:%s => %s'%(orderInfo.state, states))

    @tryForever
    def __activeOrder(self, orderid):
        return self.__client.post('/v1/order/orders/%s/place' % orderid)

    def getMinAmount(self, symbol, minAmount):
        order_id = self.__client.post('/v1/order/orders', {
            'account-id': self.__accountid,
            'amount': minAmount,
            'price': 1,
            'symbol': symbol,
            'type': hbOrderType.BuyLimit,
            'source': 'api'
        })
        

