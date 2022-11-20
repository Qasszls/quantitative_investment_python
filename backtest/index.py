
import logging
from logging import DEBUG, ERROR, INFO, Logger
import traceback
from backtest.crawler import OkxCrawlerEngine
from backtest.SQLhandler import Sql
from backtest.engine import TradingEngine
from backtest.exchange import Exchange

"""
    trading模块
    初始化一个交易员
    初始化一个交易所
    初始化一个交易类

    交易员通过交易类在交易所里买卖
"""


class BackTest:
    def __init__(self):
        self.sql_handler = Sql('127.0.0.1', 'root',
                               'QASS-utf-8', 'quant')
        self.logger: Logger = logging.getLogger()

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
            # 扔出数据
            return analysis_data
        except Exception as e:
            print('back_test.run error: {err}'.format(
                err=traceback.format_exc()))

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
                self.logger.log(level=ERROR, msg='创建失败')
            else:
                self.logger.log(level=DEBUG, msg='创建成功')

            return False
        else:
            return True

    def get_base_module(self, config):
        exchange = Exchange(sql_handler=self.sql_handler, config=config)
        TradingEngine(
            exchange=exchange, config=config)
        crawler = OkxCrawlerEngine(sql_handler=self.sql_handler)
        return exchange, crawler
