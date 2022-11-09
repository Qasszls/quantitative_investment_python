

# -*- coding:UTF-8 -*-
import json
import time
import emoji
from backtest.engine import TradingEngine
from backtest.exchange import Exchange
from backtest.analysis import AnalysisEngine
from backtest.index import BackTest
from datetime import datetime

from events.engine import EventEngine
from message.engine import LogEngine
from backtest.config import ConfigEngine

# test 随时删除
from events.event import EVENT_TICK

"""
    业务逻辑
    交易所查询数据是否存在，不存在就从线上拉取数据初始化到数据库里
    
    交易所数据准备好后，将其通过事件发出来
    
    主线
    拿到数据喂给策略，看看周期的收益结果
"""
TEST_GROUP = [
    {"initFund": 5000000.0,  # 初始资金
     "initCoin": 0.0,  # 初始币数量
     "avgPx": 0.0,  # 开仓均价
     "slippage": 0.0001,  # 滑点
     "rateInHour": 0.000003,  # 杠杆利率
     "entryOrders": 0.0008,  # 挂单手续费
     "eatOrder": 0.001,  # 吃单手续费
     "lever": 10,
     "checkSurplus": 0.322,  # 止盈
     "stopLoss": 0.169,  # 止损
     "liability": 0.0,  # 负债
     "instId": "BTC-USDT",
               "name": '柳尚佐',
               "bar": "1H",  # 粒度
     "table_name": "BTC_USDT_1H",
     "start_timestamp": "2019-11-1 00:00:00",
     "end_timestamp": "2022-11-6 00:00:00"},
    {"initFund": 5000000.0,  # 初始资金
     "initCoin": 0.0,  # 初始币数量
     "avgPx": 0.0,  # 开仓均价
     "slippage": 0.0001,  # 滑点
     "rateInHour": 0.000003,  # 杠杆利率
     "entryOrders": 0.0008,  # 挂单手续费
     "eatOrder": 0.001,  # 吃单手续费
     "lever": 10,
     "checkSurplus": 0.422,  # 止盈
     "stopLoss": 0.169,  # 止损
     "liability": 0.0,  # 负债
     "instId": "BTC-USDT",
               "name": '柳尚佐',
               "bar": "2H",  # 粒度
               "table_name": "BTC_USDT_2H",
     "start_timestamp": "2019-11-1 20:00:00",
     "end_timestamp": "2022-11-6 00:00:00"},
]


class Main:
    def __init__(self):
        self.event_engine = EventEngine()
        self.config_set = ConfigEngine()
        self.logger = LogEngine()

        self.back_test = BackTest(self.event_engine)

        self.analysis = AnalysisEngine(
            self.event_engine)

    def start(self):
        self.event_engine.start()
        # 同步的
        self.analysis.start()
        self.back_test.start(TEST_GROUP)
        self.on_end()

    def on_end(self):
        self.event_engine.stop()
        print('都关闭了')


if __name__ == "__main__":

    engine = Main()
    engine.start()
