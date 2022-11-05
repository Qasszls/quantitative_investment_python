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


TRULY = 0


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
        self.crawler = OkxCrawlerEngine(config)
        self.sql_handler = Sql(event_engine, '127.0.0.1', 'root',
                               'QASS-utf-8', 'quant')
        self.timestamp = Timestamp()

        self.start_timestamp = self.timestamp.get_time_stamp(
            config['start_timestamp'])
        self.end_timestamp = self.timestamp.get_time_stamp(
            config['end_timestamp'])

        self.timestamp_cursor = ''

        self.bar = config['bar']
        self.bar_val = int(re.findall('\d+', self.bar)[0])
        self.unit = re.findall('[a-z]', self.bar)[0]

        self.table_name = config['table_name']
        self.active = True
        self.min_fetch = 100
        # 行情信息
        self.market = []

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
            print('数据起点', self.start_timestamp, '数据终点', self.end_timestamp)
            self.timestamp_cursor = self.end_timestamp
            while(True):
                # 查询剩余长度
                limit = self._time_slice()
                if limit <= 0:
                    break
                # 爬虫爬取数据
                market = self.crawler.get_market(
                    after=self.timestamp_cursor,  limit=limit)
                # print('爬虫查询', limit, self.timestamp.get_time_normal(self.timestamp_cursor), '行情尾部',
                #       self.timestamp.get_time_normal(int(market[limit-1][0])), '行情首部', self.timestamp.get_time_normal(int(market[0][0])))
                # 存库
                self.save_database(market)
                # 更新游标
                self.timestamp_cursor = min(
                    int(market[limit-1][0]), int(market[0][0]))

    #  存到数据库里
    def save_database(self, market):
        self.sql_handler.insert_kline_data(market, self.table_name)
        print('数据库插入')

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
    def _get_divide(self, unit: str, _ms: int, val: int):
        """根据粒度换算出一共需要请求多少次

        Args:
            unit (str): 时间粒度单位
            _ms (int): 毫秒级时间段
            val (int): 时间粒度值

        Returns:
            int: 次数
        """
        divide = ''
        if unit == 'm':
            divide = _ms / 1000 / 60 / val
        elif unit == 'H':
            divide = _ms / 1000 / 60 / 60 / val
        elif unit == 'D':
            divide = _ms / 1000 / 60 / 60 / 24 / val
        elif unit == 'W':
            divide = _ms / 1000 / 60 / 60 / 24 / 7 / val
        elif unit == 'M':
            divide = _ms / 1000 / 60 / 60 / 24 / 30 / val
        elif unit == 'Y':
            divide = _ms / 1000 / 60 / 60 / 24 / 30 / 12 / val
        return int(round(divide))

    # 将时间粒度换算成毫秒值
    def _timestamp_to_ms(self, unit: str, val: int):
        divide = ''
        if unit == 'm':
            divide = val * 60 * 1000
        elif unit == 'H':
            divide = val * 60 * 60 * 1000
        elif unit == 'D':
            divide = val * 60 * 24 * 60 * 1000
        elif unit == 'W':
            divide = val * 7 * 24 * 60 * 60 * 1000
        elif unit == 'M':
            divide = val * 24 * 30 * 60 * 60 * 1000
        elif unit == 'Y':
            divide = val * 12 * 24 * 30 * 60 * 60 * 1000
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
    def _time_slice(self, sort='desc'):
        limit = ''
        point = ''
        if sort == 'desc':
            point = self.start_timestamp
        elif sort == 'asc':
            point = self.end_timestamp

        try:
            # 计算两个时间戳之间需要请求的次数
            count = self._get_divide(
                self.unit, abs(self.timestamp_cursor - point), self.bar_val)
            if count < self.min_fetch:
                # 剩余的量不满足100，按照剩余量处理
                limit = count
            else:
                # 将时间戳向前推 一定的量
                # limit = 100
                limit = 10
        except Exception as e:
            self.log(str(e), level=ERROR)

        # 返回游标和结束时间
        return limit
