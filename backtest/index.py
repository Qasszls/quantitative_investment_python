from concurrent.futures import ThreadPoolExecutor
import logging
from logging import DEBUG, ERROR, INFO, Logger
import traceback
from backtest.crawler import OkxCrawlerEngine
from backtest.SQLhandler import Sql
from backtest.engine import TradingEngine
from backtest.exchange import Exchange
from events.engine import Event, EventEngine
from events.event import BACK_TEST

"""
    trading模块
    初始化一个交易员
    初始化一个交易所
    初始化一个交易类

    交易员通过交易类在交易所里买卖
"""


class BackTest:
    def __init__(self, event_engine):
        self.pools = ThreadPoolExecutor(
            3, thread_name_prefix='Account_Thread_Pool')
        self.sql_handler = Sql('127.0.0.1', 'root',
                               'QASS-utf-8', 'quant')
        self.logger: Logger = logging.getLogger()
        self.workers = {}
        self.event_engine: EventEngine = event_engine

    def start(self, groups):
        for config in groups:
            self.pools.submit(self.run, config)
        self.pools.shutdown(wait=True)

    def run(self, config):
        try:
            exchange, crawler = self.get_base_module(config=config)
            # 检查数据
            flag = self.checkout_table(config)
            # 初始化数据
            if not flag:
                crawler.init_market(config)
            # 执行策略
            analysis_data = exchange.start()
            # 扔出事件
            event: Event = Event(type=BACK_TEST, data=analysis_data)
            self.event_engine.put(event)
        except Exception as e:
            print('back_test.run error: {err}'.format(err=traceback.format_exc()))

    def checkout_table(self, config):
        table_name = config['table_name']
        # 查询表
        table_exist = self.sql_handler.is_table_exist(table_name)
        # 如果表不存在
        if not table_exist:
            # 创建表
            res, code = self.sql_handler.create_table(table_name)
            # 创建成功/创建失败
            if code != 0:
                self.log(level=ERROR, msg='创建失败')
            else:
                self.log(level=DEBUG, msg='创建成功')

            return False
        else:
            return True

    def get_base_module(self, config):
        exchange = Exchange(sql_handler=self.sql_handler, config=config)
        TradingEngine(
            exchange=exchange, config=config)
        crawler = OkxCrawlerEngine(sql_handler=self.sql_handler)
        return exchange, crawler
