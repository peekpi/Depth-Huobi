import time

def timestamp():
    return int(time.time())

class OrderManager():
    OrderOpen = 0
    OrderFilledBuy = 1
    OrderFilledSell = 2
    OrderCancel = 3
    def __init__(self, buyOrder):
        self.__createTime = timestamp()
        self.__orderStatus = OrderManager.OrderOpen
        self.__buyOrder = buyOrder
        self.__buyAmountFilled = 0
        self.__sellOrders = []
        self.__sellAmount = 0
        self.__sellAmountFilled = 0

    def getBuyPrice(self):
        return self.__buyOrder.getPrice()

    def getExitPrice(self):
        return self.getBuyPrice()/0.996004

    def getBuyAmount(self):
        return self.__buyOrder.getAmount()
    
    def getSellAmount




