import time
from events.event import EVENT_TICK, EVENT_POSITION, EVENT_ACCOUNT, EVENT_LOG
from events.engine import Event, EventEngine
from share.utils import to_json_parse, to_json_stringify, is_pass, get_time_stamp
from backtest.constants import AnalysisStructure, PositionsStructure, AccountStructure, TABLE_NOT_EXITS, Market, BUY, SELL
import logging
from logging import ERROR, INFO, Logger


class UserInfo:
    def __init__(self, config):
        self.name = config['name']
        self.config = config
        self.margin_lever = 0.0  # 保证金
        self.liability = config['liability']  # 负债
        self.stopLoss = config['stopLoss']  # 止损
        # 持仓字段
        self.uplRatio = 0.0  # 未实现收益率
        self.avgPx = config['avgPx']  # 开仓均价
        self.availPos = config['initCoin']  # 可平仓数量
        self.lever = config['lever']
        # 用户资产字段
        self.availBal = config['initFund']  # 用户可用资产
        # 统计用户战斗力
        self.win_times = 0
        self.game_times = 0

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
        if type == BUY:  # 杠杆版本
            real_price = price * (1+self.config['slippage'])  # 购买价格
            liability = real_price * count + self.liability  # 总负债
            new_margin_lever = count * real_price / self.lever  # 保证金
            margin_lever = new_margin_lever + self.margin_lever  # 总保证金
            service_charge = real_price * count * \
                self.config['eatOrder']  # 手续费
            spend = service_charge + new_margin_lever  # 花费
            availBal = self.availBal - spend  # 剩余可用

            availPos = count + self.availPos  # 持仓数量
            avgPx = real_price if int(self.avgPx) == 0 else (
                self.avgPx + real_price)/2  # 持仓均价
            upl = price * availPos - liability  # 收益

            uplRatio = upl / margin_lever   # 收益率
        else:  # 售卖 保证金版本
            real_price = price * (1-self.config['slippage'])  # 出售价格
            market_asset = real_price * self.availPos  # 仓位资产现价
            current_asset = self.avgPx * self.availPos  # 仓位资产买入价
            # 控制亏损
            if (market_asset-(current_asset))/(current_asset) <= -self.stopLoss:
                market_asset = (current_asset)*(1-self.stopLoss)
            service_charge = market_asset * self.config['eatOrder']  # 手续费
            earnings = market_asset - self.liability - service_charge  # 收益

            availBal = earnings + self.availBal + self.margin_lever   # 剩余可用

            # 数据统计，计算 买一次算玩一次
            self.game_times = self.game_times + 1
            # 买入价小于卖出价，就算赢
            self.win_times = self.win_times + \
                1 if market_asset > current_asset else self.win_times

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

    def __init__(self, sql_handler, config):
        self.sql_handler = sql_handler
        self.logger: Logger = logging.getLogger()
        self.config = config
        self.table_name = config['table_name']
        # 行情信息
        self.market = {}
        self.start_timestamp = get_time_stamp(config['start_timestamp'])
        self.end_timestamp = get_time_stamp(config['end_timestamp'])
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
        self.logger.log(
            level=INFO, msg="开始执行{name}回测程序".format(name=self.table_name))

        # 开启回测函数
        self.start_back_test()
        # 整理回测数据
        current_uplRatio = self.get_user_uplRatio()
        data = AnalysisStructure(
            {'win_times': self.user.win_times, 'game_times': self.user.game_times, 'uplRatio': current_uplRatio, 'config': self.config})
        return data

    # 开始回测
    def start_back_test(self):
        # 查询数据库
        sql = 'SELECT * FROM ' + self.table_name + \
            ' WHERE id_tamp BETWEEN {start_timestamp} AND {end_timestamp}'.format(
                start_timestamp=self.start_timestamp, end_timestamp=self.end_timestamp)

        ss_cursor, conn = self.sql_handler.connect(ss_cursor=True)
        # 执行sql语句
        ss_cursor.execute(sql)
        while True:
            tick = ss_cursor.fetchone()
            if not tick:
                # 关闭测试进程
                break
            self.on_tick(tick)

    # 购买
    def buy(self, count):
        # 用户购买
        self.user.user_trading(count=count, price=self.market.close, type=BUY)

    # 出售
    def sell(self, count=0):
        if count == 0:
            # 全部出售
            self.user.user_trading(price=self.market.close, type=SELL)
        else:
            # 部分出售
            pass

    # 触发行情
    def on_tick(self, tick) -> None:
        """
        Tick event push.
        """
        try:
            # 更新当前行情信息
            self.market = Market(tick)
            # 先更新持仓和用户资产信息
            self.on_positions()
            self.on_account()
            # 再触发行情事件 将实例对象转为数组
            self.process(EVENT_TICK, list(self.market.k_line_data))
        except Exception as e:
            self.logger.log(level=ERROR, msg=str(e))

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

    # 获得用户收益率
    def get_user_uplRatio(self):
        equity = self.user.availPos * \
            self.market.close - self.user.liability + \
            self.user.margin_lever  # 权益类资产
        total = equity + self.user.availBal  # 总资产

        fund = self.config['initFund']  # 初始资金
        current_uplRatio = (total-fund)/fund  # 收益率

        return current_uplRatio
