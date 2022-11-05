import time
from events.event import EVENT_TICK, EVENT_ERROR, EVENT_POSITION, EVENT_ACCOUNT, EVENT_LOG, K_LINE_DATA
from events.engine import Event, EventEngine
from share.TimeStamp import Timestamp
from share.utils import to_json_parse, to_json_stringify, is_pass
from backtest.crawler import OkxCrawlerEngine
from backtest.constants import PositionsStructure, AccountStructure, TABLE_NOT_EXITS
import re
from logging import ERROR, INFO
from backtest.SQLhandler import Sql
from tqdm import tqdm
import emoji

from timeit import default_timer as timer

TRULY = 0


class DownloadBar:
    def __init__(self):
        self.bar = ''

    def update(self, count, limit):
        self.bar.set_description(
            emoji.emojize('本次传输剩余   {count}条   每次{limit}条 📆'.format(count=count, limit=limit)))

        self.bar.update(limit)

    def create_bar(self, *args, **kwargs):
        self.bar = tqdm(*args, **kwargs)

    def destroy_all(self):
        self.bar = ''


class UserInfo:
    def __init__(self, name, availBal, coin):
        self.name = name
        self._positions = PositionsStructure(coin)  # 用户初始币数量 浮点型
        self._account = AccountStructure(availBal)

    # 资产变动
    def account_change(self, diff):
        availBal = self._account.get_data('availBal')
        self._account.set_data('availBal', availBal + diff)

    # 仓位变动
    def positions_change(self, uplRatio=None, avgPx=None, availPos=None):
        if uplRatio:
            self._positions.set_data('uplRatio', uplRatio)  # 设置收益率
        elif avgPx:
            self._positions.set_data('avgPx', avgPx)  # 设置开仓均价
        elif availPos:
            self._positions.set_data('availPos', availPos)  # 设置可平仓数量

    # 获得用户持仓
    def get_positions(self):
        return self._positions.get_data()

    # 获得用户资产信息
    def get_account(self):
        return self._account.get_data()

    # 获得用户持有的币种数量
    def get_positions_coin_count(self):
        return self._positions.get_data('availPos')


class Exchange:
    """衍生业务类
        主线1：_time_slice 函数负责拆分回测数据的时间段
        主线2：fetch_market_by_timestamp 函数负责查询数据并持续发出事件
        场景：
            1：本地有数据且完全，直接扔给事件循环
            2：本地有数据但不完全
                2.1 缺失的部分比本地更旧
                2.2 缺失的部分比本地更新
                2.3 缺失的部分比本地更旧也更新

    """

    def __init__(self, event_engine, config):
        self.event_engine = event_engine
        self.crawler = OkxCrawlerEngine(event_engine, config)
        self.sql_handler = Sql(event_engine, '127.0.0.1', 'root',
                               'QASS-utf-8', 'quant')
        self.timestamp = Timestamp()
        self.download_bar = DownloadBar()

        self.start_timestamp = self.timestamp.get_time_stamp(
            config['start_timestamp'])
        self.end_timestamp = self.timestamp.get_time_stamp(
            config['end_timestamp'])

        self.timestamp_cursor = ''

        self.bar = config['bar']
        self.bar_val = int(re.findall('\d+', self.bar)[0])
        self.unit = re.findall('[a-z]', self.bar)[0]

        self.table_name = config['table_name']
        self.min_fetch = 100
        # 行情信息
        self.market = []

        # 性能信息
        self.runtime_start = 0
        self.runtime_end = 0

        # 账户信息
        self.user = UserInfo(
            config['name'], config['initFund'], config['initCoin'])

    def start(self):
        # 检查所属数据库数据
        self._checkout_table(self.table_name)
        # 初始化数据库数据
        self._data_init()
        # 开启回测函数
        self.fetch_market_by_timestamp()

    # 数据初始化
    def _data_init(self):
        flag = input('是否更新行情数据？(yes/no)')
        if is_pass(flag):
            self.runtime_start = timer()
            # 初始化游标
            self.timestamp_cursor = self.end_timestamp
            # 获得粒度换算成毫秒的值
            interval = self._timestamp_to_ms()
            # 监听事件
            self.event_engine.register(K_LINE_DATA, self.save_database)
            # 创建进度条
            total_data = self._get_divide(
                abs(self.end_timestamp - self.start_timestamp))
            self.download_bar.create_bar(total=total_data)  # 进度条 和 总条数
            while(True):
                # 查询剩余长度
                limit, after = self._time_slice(interval)

                if limit <= 0:
                    self.download_bar.destroy_all()
                    break
                # 爬虫爬取数据
                self.crawler.get_market(
                    after=after,  limit=limit)

    #  存到数据库里

    def save_database(self, market_event):
        # 解包
        data = market_event.data[0]['data']
        # 数据量是否到尽头
        is_end = self.start_timestamp == int(data[len(data)-1][0])

        # # 正常及时插拔数据库
        self.sql_handler.insert_kline_data(
            data, self.table_name)

        if is_end or len(data) < 100:
            self.runtime_end = timer()
            self.log('数据初始化完毕，用时\n{second}秒\n'.format(
                second="%.3f" % (self.runtime_end-self.runtime_start)))

            # 获得指定时间戳内的行情数据
    def fetch_market_by_timestamp(self):
        # 查询数据库
        self.sql_handler.search_table_content(self.table_name,
                                              self.start_timestamp, self.end_timestamp)

    def buy(self, count):
        # 计算当前行情买这些币需要多少钱
        pay_money = count * -1
        # 结算花费的金钱
        self.user.account_change(pay_money)
        # 更新持仓和用户资产信息
        self.on_positions()
        self.on_account()

    # 出售
    def sell(self, price, count=0):
        if count == 0:
            # 全部出售
            # 根据行情 计算售卖手里所有的币的收益
            money = price * self.user.get_positions_coin_count()
            self.user.account_change(money)  # 加上这部分钱
            self.user.positions_change(0, 0, 0)  # 将用户持仓信息设置为空
        else:
            # 部分出售
            pass

    def log(self, msg, level=INFO) -> None:
        """
        Event event push.
        """
        self._put(EVENT_LOG, {'level': level, 'msg': msg})

    def on_tick(self, tick) -> None:
        """
        Tick event push.
        """
        self._put(EVENT_TICK, tick)

    def on_positions(self) -> None:
        """
        Position event push.
        """
        position = self.user.get_positions()
        self._put(EVENT_POSITION, position)

    def on_account(self) -> None:
        """
        Account event push.
        """
        account = self.user.get_account()
        self._put(EVENT_ACCOUNT, account)

    def _put(self, type, data):
        event: Event = Event(type, data)
        self.event_engine.put(event)

    # 根据粒度换算出一共需要请求多少次
    def _get_divide(self, ms):
        """根据粒度换算出一共需要请求多少次

        Args:
            unit (str): 时间粒度单位
            ms (int): 毫秒级时间段
            val (int): 时间粒度值

        Returns:
            int: 次数
        """
        divide = ''
        if self.unit == 'm':
            divide = ms / 1000 / 60 / self.bar_val
        elif self.unit == 'H':
            divide = ms / 1000 / 60 / 60 / self.bar_val
        elif self.unit == 'D':
            divide = ms / 1000 / 60 / 60 / 24 / self.bar_val
        elif self.unit == 'W':
            divide = ms / 1000 / 60 / 60 / 24 / 7 / self.bar_val
        elif self.unit == 'M':
            divide = ms / 1000 / 60 / 60 / 24 / 30 / self.bar_val
        elif self.unit == 'Y':
            divide = ms / 1000 / 60 / 60 / 24 / 30 / 12 / self.bar_val
        return int(round(divide))

    # 将时间粒度换算成毫秒值
    def _timestamp_to_ms(self):
        divide = ''
        if self.unit == 'm':
            divide = self.bar_val * 60 * 1000
        elif self.unit == 'H':
            divide = self.bar_val * 60 * 60 * 1000
        elif self.unit == 'D':
            divide = self.bar_val * 60 * 24 * 60 * 1000
        elif self.unit == 'W':
            divide = self.bar_val * 7 * 24 * 60 * 60 * 1000
        elif self.unit == 'M':
            divide = self.bar_val * 24 * 30 * 60 * 60 * 1000
        elif self.unit == 'Y':
            divide = self.bar_val * 12 * 24 * 30 * 60 * 60 * 1000
        return int(round(divide))

    # 检查表格
    def _checkout_table(self, table_name):
        # 查询表
        table_exist = self.sql_handler.is_table_exist(table_name)
        # 如果表不存在
        if not table_exist:
            flag = input('该表格不存在，是否新建？(yes/no)')
            if is_pass(flag):
                # 创建表
                res, code = self.sql_handler.create_table(self.table_name)
                # 创建成功/创建失败
                if code != TRULY:
                    self.log(level=ERROR, msg='创建失败')
            else:
                # 不创建表
                raise Exception('请手动程序')

        # 时间切片
    def _time_slice(self, interval):
        limit = ''
        after = self.timestamp_cursor
        try:
            # 计算新的游标 往前推到对应的时间段
            # 计算两个时间戳之间需要请求的次数 游标 - 终点目标值
            count = self._get_divide(
                abs(after - self.start_timestamp))
            # 计算本次请求长度
            if count < self.min_fetch:
                # 剩余的量不满足100，按照剩余量处理
                limit = count
            else:
                # 将时间戳向前推 一定的量
                limit = 100
        except Exception as e:
            self.log(str(e), level=ERROR)
        finally:
            # 更新游标
            self.timestamp_cursor = after - (interval * limit)
            # 更新进度条
            self.download_bar.update(count=count, limit=limit)
        # 返回游标和结束时间
        return limit, after
