"""字段存放地
"""
# 长连接接口地址
PUB_URL = "wss://ws.okx.com:8443/ws/v5/public"
PRI_URL = "wss://ws.okx.com:8443/ws/v5/private"

# 事件名
EVENT_LOGIN = 'login'
EVENT_SUBSCRIBE = 'subscribe'
EVENT_ERROR = 'error'
EVENT_UNSUBSCRIBE = 'unsubscribe'

# 推送数据刘
ARG_ACCOUNT = 'aAccount'
ARG_POSITION = 'aPosition'
