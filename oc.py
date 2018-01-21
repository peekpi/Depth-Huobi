from liveApi.liveUtils import *
from hbsdk import ApiClient, ApiError
from ApiKey import API_KEY
from ApiKey import API_SECRET

client = ApiClient(API_KEY, API_SECRET)

oid = 840419149
orderInfo = client.get('/v1/order/orders/%s' % oid)
print orderInfo
