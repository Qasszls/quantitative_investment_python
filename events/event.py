"""
Event type string used in the trading platform.
"""

# from vnpy.event import EVENT_TIMER  # noqa

EVENT_TICK = "eTick."
EVENT_TRADE = "eTrade."
EVENT_ORDER = "eOrder."
EVENT_POSITION = "ePosition."
EVENT_ACCOUNT = "eAccount."

EVENT_QUOTE = "eQuote."
EVENT_CONTRACT = "eContract." # 合约
EVENT_LOG = "eLog"
EVENT_DING = "elog"

# 策略运行事件
EVENT_COMPUTED = 'eComputed'

# 异常事件
EVENT_ERROR = 'eError'

K_LINE_DATA = "eklineData"
# 爬虫数据响应
SAVE_DATA = "esaveData"