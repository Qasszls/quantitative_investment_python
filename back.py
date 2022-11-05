

# -*- coding:UTF-8 -*-
import json
import time
import emoji
from backtest.engine import TestEngine
from backtest.exchange import Exchange
from backtest.analysis import AnalysisEngine
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


class Main:
    def __init__(self):
        self.event_engine = EventEngine()
        self.config_set = ConfigEngine()

        self.logger = LogEngine(self.event_engine)
        # self.analysis = AnalysisEngine()

        self.exchange = Exchange(self.event_engine,
                                 config=self.config_set.get_config())

        self.backtest = TestEngine(
            self.event_engine, self.config_set.get_config())

    def start(self):
        self.backtest.start()
        self.event_engine.start()
        self.exchange.start()




if __name__ == "__main__":

    engine = Main()
    engine.start()
