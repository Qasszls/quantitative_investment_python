from concurrent.futures import ThreadPoolExecutor
import threading
import re

from matplotlib.pyplot import bar
from share.request import Request
from events.engine import Event
from share.utils import timestamp_to_ms, get_divide, get_time_normal, get_time_stamp
import logging
from logging import ERROR, INFO, Logger


class BaseEngine:
    def __init__(self):
        self.pools = ThreadPoolExecutor(
            5, thread_name_prefix='Account_Thread_Pool')
        self.request = Request().request
        self.lock = threading.RLock()
        self.logger: Logger = logging.getLogger()

    # 未来可以做一些进度条，每秒并发数量等数据展示的内容


class OkxCrawlerEngine(BaseEngine):
    def __init__(self,  sql_handler) -> None:
        BaseEngine.__init__(self)
        self.sql_handler = sql_handler

    def get_market(self,  after=None, limit=100, config=None):
        if not after or not config:
            self.logger.log(level=ERROR, msg='入参错误')

        bar_val = config['bar']
        instId = config['instId']
        table_name = config['table_name']
        params = {"instId": instId, "bar": bar_val, "limit": limit}
        if after:
            params["after"] = str(after)
        kline, error = self.request(
            "GET", "/api/v5/market/history-candles", params)
        self.sql_handler.insert_kline_data(kline['data'], table_name)

     # 数据初始化

    def init_market(self, config):
        self.logger.log(level=INFO, msg='开始下载{bar}'.format(bar=config['bar']))
        bar_val = int(re.findall('\d+', config['bar'])[0])
        unit = re.findall('[a-zA-Z]', config['bar'])[0]
        # 初始化游标
        timestamp_cursor = get_time_stamp(config['end_timestamp'])
        point_timestamp = get_time_stamp(config['start_timestamp'])
        # 获得粒度换算成毫秒的值
        interval = timestamp_to_ms(unit=unit, bar_val=bar_val)
        limit = ''
        while(True):
            try:
                # 剩余请求数量长度
                count = get_divide(unit=unit,
                                   ms=abs(timestamp_cursor - point_timestamp), bar_val=bar_val)
                # 剩余的量不满足100，按照剩余量处理
                if count < 100:
                    limit = count
                else:
                    # 将时间戳向前推 一定的量
                    limit = 100

            except Exception as e:
                print(str(e))
            finally:
                # 爬虫爬取数据
                self.pools.submit(
                    self.get_market, timestamp_cursor, limit, config)
                # 更新游标
                timestamp_cursor = timestamp_cursor - (interval * limit)

            if limit <= 0:
                break
        self.pools.shutdown(wait=True)
        self.logger.log(level=INFO, msg='下载完成：{bar}'.format(bar=config['bar']))
        
