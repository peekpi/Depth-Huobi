import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import matplotlib.ticker as mticker
from matplotlib.finance import candlestick_ohlc
import json
import numpy as np

def getJson(name):
    return json.load(file(name, 'r'))

def timestamp2num(t):
    return mdates.date2num(datetime.fromtimestamp(t))

def map2ohlc(x):
    return (timestamp2num(x['id']), x['open'], x['high'], x['low'], x['close'], x['vol'], x['count'])

symbol='btcusdt'
ohlc = map(map2ohlc, getJson('kline/%s-2000.txt'%symbol))

plt.style.use('dark_background')
ax1 = plt.subplot(211)
#ax2 = plt.subplot(312, sharex=ax1)
ax3 = plt.subplot(212, sharex=ax1)
candlestick_ohlc(ax1, ohlc[0:600], width=1.0/(60*24),  colorup="red", colordown="green")
plt.xticks(rotation=45)
'''
for label in ax1.xaxis.get_ticklabels():
    label.set_rotation(45)
'''
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
ax1.xaxis.set_major_locator(mticker.MaxNLocator(15))
ax1.grid(True)
date = np.array(map(lambda x:x[0], ohlc[0:600]))
vol = np.array(map(lambda x:x[-2], ohlc[0:600]))
count = map(lambda x:x[-1], ohlc[0:600])
#ax2.bar(date, vol, width=1.0/(60*24))
#ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
ax3.bar(date, vol/count, width=1.0/(60*24))
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
plt.legend()
plt.title('First Demo')
plt.show()
