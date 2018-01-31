
def usdt(p1, p2, amount):
    buyUSDT = p1 * amount
    sellUSDT1 = round(amount*0.998*p2*0.998, 2)
    sellUSDT2 = round(amount*p2*0.998-buyUSDT*0.002, 2)
    return (buyUSDT, sellUSDT1, sellUSDT2, round(sellUSDT2 - sellUSDT1, 4))

print usdt(1000, 1100, 1000)
print usdt(1000, 909, 1000)

def k(*args, **kw):
    print args
    print kw

k(1,2,3,c=10,**{'a':1,'b':2})
