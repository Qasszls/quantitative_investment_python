import time
from events.event import EVENT_TICK, EVENT_POSITION, EVENT_ACCOUNT, EVENT_LOG, K_LINE_DATA, SAVE_DATA
from events.engine import Event, EventEngine
from share.TimeStamp import Timestamp
from share.utils import to_json_parse, to_json_stringify, is_pass
from backtest.crawler import OkxCrawlerEngine
from backtest.constants import PositionsStructure, AccountStructure, TABLE_NOT_EXITS, Market, BUY, SELL
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


add_service_charge = 0.0  # 手续费累计
# 胜率
win_times = 0.0
game_times = 0
add_up = 0.0  # 累计金额
# 赔率
odds = 0.0


class UserInfo:
    def __init__(self, config):
        self.name = config['name']
        self.config = config
        self.margin_lever = 0.0  # 保证金
        self.liability = config['liability']  # 负债
        # 持仓字段
        self.uplRatio = 0.0  # 未实现收益率
        self.avgPx = config['avgPx']  # 开仓均价
        self.availPos = config['initCoin']  # 可平仓数量
        self.lever = config['lever']
        # 用户资产字段
        self.availBal = config['initFund']  # 用户可用资产

    # 保证金变动

    def margin_lever_change(self, money):
        self.margin_lever = money

    # 资产变动
    def account_change(self, availBal=None, liability=None):
        if liability != None:
            self.liability = liability
        if availBal != None:
            self.availBal = availBal

    # 仓位变动
    def positions_change(self, uplRatio=None, avgPx=None, availPos=None):
        if uplRatio != None:
            self.uplRatio = uplRatio  # 设置收益率
        if avgPx != None:
            self.avgPx = avgPx  # 设置开仓均价
        if availPos != None:
            self.availPos = availPos  # 设置可平仓数量

    # 用户购买
    def user_trading(self, count: float = 0.0, price: float = 0.0, type: float = BUY):
        availBal = 0.0
        availPos = 0.0
        avgPx = 0.0
        uplRatio = 0.0
        liability = 0.0
        margin_lever = 0.0
        global add_service_charge, add_up
        if type == BUY:  # 杠杆版本
            real_price = price * (1+self.config['slippage'])  # 购买价格
            liability = real_price * count + self.liability  # 总负债
            new_margin_lever = count * real_price / self.lever  # 保证金
            margin_lever = new_margin_lever + self.margin_lever  # 总保证金
            service_charge = real_price * count * \
                self.config['eatOrder']  # 手续费
            add_service_charge = add_service_charge + service_charge  # test
            spend = service_charge + new_margin_lever  # 花费
            availBal = self.availBal - spend  # 剩余可用

            availPos = count + self.availPos  # 持仓数量
            avgPx = real_price if int(self.avgPx) == 0 else (
                self.avgPx + real_price)/2  # 持仓均价
            upl = price * availPos - liability  # 收益

            uplRatio = upl / margin_lever   # 收益率
        else:  # 售卖 保证金版本
            real_price = price * (1-self.config['slippage'])  # 出售价格
            asset = real_price * self.availPos  # 仓位资产
            # 如果亏损过大，就将亏损固定为 4%
            if (asset-(self.avgPx * self.availPos))/(self.avgPx * self.availPos) <= -0.004:
                asset = (self.avgPx * self.availPos)*(1-0.004)
            service_charge = asset * self.config['eatOrder']  # 手续费
            add_service_charge = add_service_charge + service_charge  # test
            earnings = asset - self.liability - service_charge  # 收益
            add_up = add_up + earnings  # test

            availBal = earnings + self.availBal + self.margin_lever   # 剩余可用

        self.positions_change(
            uplRatio=uplRatio, availPos=availPos, avgPx=avgPx)
        self.account_change(availBal=availBal,
                            liability=liability)
        self.margin_lever_change(money=margin_lever)

    # 获得用户持仓

    def get_positions(self, type=None):
        # 获得用户持仓的数据结构
        _pos = PositionsStructure(
            uplRatio=self.uplRatio, avgPx=self.avgPx, availPos=self.availPos, lever=self.lever)
        # 如果传入字段名，返回内容data里的数据
        if type:
            return _pos.data[type]
        else:
            return vars(_pos)

    # 获得用户资产信息
    def get_account(self, type=None):
        _acc = AccountStructure(fund=self.availBal)
        # 如果传入字段名，返回内容data里的数据
        if type:
            return _acc.data[type]
        else:
            return vars(_acc)

    # 更新用户持仓
    def update_positions(self, close):
        if int(self.avgPx) != 0:
            upl = close * self.availPos - self.liability  # 收益率
            uplRatio = upl / self.margin_lever  # 收益率

            self.positions_change(uplRatio=uplRatio)


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
        self.unit = re.findall('[a-zA-Z]', self.bar)[0]

        self.table_name = config['table_name']
        self.min_fetch = 100
        # 行情信息
        self.market = {}

        # 性能信息
        self.runtime_start = 0
        self.runtime_end = 0

        # 账户信息
        self.user = UserInfo(
            config)
        # 事件表
        self.event_dict = {
            EVENT_TICK: "",
            EVENT_POSITION: "",
            EVENT_ACCOUNT: ""
        }

    def start(self):
        # 检查所属数据库数据
        self._checkout_table(self.table_name)
        # 初始化数据库数据
        self._data_init()
        # 开启回测函数
        self.start_back_test()

    # 数据初始化
    def _data_init(self):
        flag = input('是否更新行情数据？(yes/no)')
        if is_pass(flag):
            print('数据开始时间', self.start_timestamp,
                  '数据结束时间', self.end_timestamp)
            self.runtime_start = timer()
            # 初始化游标
            self.timestamp_cursor = self.end_timestamp
            # 获得粒度换算成毫秒的值
            interval = self._timestamp_to_ms()
            # 监听事件
            self.event_engine.register(SAVE_DATA, self.save_database)
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

    # 开始回测
    def start_back_test(self):
        # 回测数据要流过交易所的管道，所以数据库获得了后不直接给策略
        self.event_engine.register(K_LINE_DATA, self.on_tick)
        # 查询数据库
        self.sql_handler.search_table_content(self.table_name,
                                              self.start_timestamp, self.end_timestamp)

    def buy(self, count):
        # 用户购买
        self.user.user_trading(count=count, price=self.market.close, type=BUY)
        # self.on_account()
        # self.on_positions()

    # 出售
    def sell(self, count=0):
        global win_times, game_times, add_up, add_service_charge
        if count == 0:
            # print('{type}价 {price}'.format(price=self.market.close, type='买入' if BUY ==
            #                                          SELL else '卖出'), '几月几号:', self.timestamp.get_time_normal(self.market.timestamp))
            game_times = game_times + 1
            is_win = True if self.user.avgPx < self.market.close else False
            win_times = win_times + 1 if is_win else win_times
            # print('胜率', win_times/game_times *
            #       100, '%')
            # '交易额度', self.user.liability
            # print('收益累计', add_up, '手续费累计', add_service_charge)
            # 全部出售
            self.user.user_trading(price=self.market.close, type=SELL)
        else:
            # 部分出售
            pass

    def log(self, msg, level=INFO) -> None:
        """
        Event event push.
        """
        self._put(EVENT_LOG, {'level': level, 'msg': msg})

    def on_tick(self, tick_event) -> None:
        """
        Tick event push.
        """
        # 更新当前行情信息
        self.market = Market(tick_event.data)
        # 先更新持仓和用户资产信息
        self.on_positions()
        self.on_account()
        # 再触发行情事件 将实例对象转为数组
        self.process(EVENT_TICK, list(self.market.k_line_data))

    def on_positions(self) -> None:
        """
        Position event push.
        """
        # 获得格式化的用户持仓数据
        position = self.user.get_positions()
        # 更新持仓信息
        self.user.update_positions(self.market.close)
        # 对象增强
        position['data'][0]['timestamp'] = self.market.timestamp
        # 发送事件通知交易模块
        self.process(EVENT_POSITION, position)

    def on_account(self) -> None:
        """
        Account event push.
        """
        account = self.user.get_account()
        account['data'][0]['timestamp'] = self.market.timestamp
        self.process(EVENT_ACCOUNT, account)

    # 注册回调函数
    def register(self, event_name, handle):
        self.event_dict[event_name] = handle

    # 处理回调函数
    def process(self, event_name, data):
        if self.event_dict[event_name]:
            self.event_dict[event_name](Event(event_name, data))

    # 推送事件
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
