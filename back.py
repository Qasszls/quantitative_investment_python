

# -*- coding:UTF-8 -*-
import json
import time
import emoji
from backtest.engine import TradingEngine
from backtest.exchange import Exchange
from backtest.analysis import AnalysisEngine
from backtest.index import BackTest
from datetime import datetime
from backtest.config import BASE_CONFIG, VAR_CONFIG, BAR_CONFIG, CHECK_SURPLUS_SCOPE, STOP_LOSS_SCOPE

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
        self.logger = LogEngine()

        self.back_test = BackTest(self.event_engine)

        self.analysis = AnalysisEngine(
            self.event_engine)

    def start(self):
        self.event_engine.start()
        # 同步的
        test_group = self.analysis.get_test_config(*self.get_analysis_params())
        self.back_test.start(test_group)
        
        self.on_end()

    def on_end(self):
        self.event_engine.stop()

    # 获得回测数据参数
    def get_analysis_params(self):
        bar_config = [*BAR_CONFIG]
        cs_scope = {**CHECK_SURPLUS_SCOPE}
        sl_scope = {**STOP_LOSS_SCOPE}
        base_config = {**VAR_CONFIG, **BASE_CONFIG}

        return (bar_config, cs_scope, sl_scope, base_config)


if __name__ == "__main__":

    engine = Main()
    engine.start()
