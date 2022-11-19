

# -*- coding:UTF-8 -*-
from atexit import register
from email import message
import sys
import emoji
import pandas as pd
from backtest.exchange import Exchange
from share.TimeStamp import Timestamp
from strategyLibrary.simpleMACDStrategy import SimpleMacd
from events.engine import EventEngine, Event
from events.event import EVENT_TICK, EVENT_POSITION, EVENT_ACCOUNT, EVENT_LOG
from logging import INFO


class TradingEngine:
    def __init__(self,
                 exchange: Exchange,
                 config=None):
        if not config:
            print('请填写用户信息')
            return

        self.timestamp = Timestamp()  # 初始化时间操作对象
        self.exchange = exchange  # 交易所引擎

        self.checkSurplus = config['checkSurplus']  # 玩家止盈率
        self.stopLoss = config['stopLoss']  # 玩家止损率
        self.lever = 10  # 杠杆倍数
        self.update_times = 0
        self.tick_times = 0
        self.config = config

        self.simple_macd = SimpleMacd(computed=self.computed)

        # 内部变量
        self.buy_times = 0
        # 15m
        self.ema12 = 0
        self.ema26 = 0
        self.dea = 0
        self.old_kl = []

        self.register()

    def register(self):
        # 监听数据回调
        self.exchange.register(EVENT_TICK, self.breathing)
        self.exchange.register(EVENT_POSITION, self.update_position)
        self.exchange.register(EVENT_ACCOUNT, self.update_account)

    # 获取用户信息

    def update_account(self, event):
        data = event.data['data'][0]
        time = data['timestamp']
        money = data['details'][0]['availBal']  # 目前可用资产
        equity = self.exchange.user.availPos * \
            self.exchange.market.close - self.exchange.user.liability + \
            self.exchange.user.margin_lever  # 权益类资产
        total = equity + money  # 总资产

        fund = self.config['initFund']  # 初始资金
        uplRatio = "%.2f" % ((total-fund)/fund*100)  # 收益率
        # print('{name},目前总资产: {total}, 总收益率: {uplRatio}%, 可用资产{money}; {time}'.format(
        #     uplRatio=uplRatio, total=total, name=self.config['table_name'], money=money, time=self.timestamp.get_time_normal(time)))

    # 更新持仓数据
    def update_position(self, event):
        message = event.data
        data = message['data']
        if len(data) > 0 and 'uplRatio' in data[0] and data[0]['uplRatio'] != '':
            # 目前是全仓模式，最多只有一笔订单，此处不用处理的太复杂
            earnings = data[0]
            uplRatio = float(earnings['uplRatio'])

            def _is_checkSurplus():
                return uplRatio >= self.checkSurplus

            def _is_sotpLoss():
                if uplRatio <= 0:
                    return abs(uplRatio) >= self.stopLoss
                else:
                    return False

            # 检测止盈止损
            if _is_checkSurplus() or _is_sotpLoss():
                self.allSell()

    def breathing(self, kline_event):
        kline_data = kline_event.data
        # 判断新老数据
        # 第一次进入循环 或者 同一时间的老数据，都会进入
        if kline_data[0] in self.old_kl:
            # 其实可以完全不写下面的代码，但是意义就不一样了。
            self.old_kl = kline_data
            return
        else:
            _k = pd.DataFrame([kline_data]).astype(float)
            
            _k.columns = [
                'id_tamp', 'open_price', 'high_price', 'lowest_price',
                'close_price', 'vol', 'volCcy', 'volCcyQuote'
            ]
            KLINE_DATA = _k.to_dict('records')[0]
            # 准备数据-macd
            MACD_DATA = self._before_investment(KLINE_DATA)
            # 增加一条逻辑，前26条数据，用来初始化macd策略曲线
            if self.tick_times >= 26:
                self.tick_times = self.tick_times + 1
                return
            # 运行策略 *********** door **************

            self.simple_macd.runStrategy(
                KLINE_DATA,
                MACD_DATA
            )
            self.old_kl = kline_data

    # 钩子函数 计算完成

    def computed(self, data):
        medium_status = data['medium_status']  # 初级判断状态
        if medium_status and self.buy_times <= 2:
            # 买入 钩子
            self.allBuy()

    # 下单
    def allBuy(self):
        # 用户最大可买
        count = self.exchange.user.availBal * \
            0.15 / float(self.old_kl[4]) * self.lever
        # print('买点: ', self.timestamp.get_time_normal(self.old_kl[0]))
        self.exchange.buy(count)

    def allSell(self):
        # print('卖点', self.timestamp.get_time_normal(self.old_kl[0]))
        self.exchange.sell()

    def _before_investment(self, kline_data):
        # 私有函数
        # 计算macd值
        def _count_macd(price):
            """
            基准
            12
            26
            """
            # 获取往日 数据
            last_ema12 = self.ema12
            last_ema26 = self.ema26
            last_dea = self.dea
            # 计算当日 数据

            EMA12 = last_ema12 * 11 / 13 + price * 2 / 13
            EMA26 = last_ema26 * 25 / 27 + price * 2 / 27
            DIF = EMA12 - EMA26
            DEA = last_dea * 8 / 10 + DIF * 2 / 10
            MACD = DIF - DEA
            return {
                'ema12': EMA12,
                'ema26': EMA26,
                'dif': DIF,
                "dea": DEA,
                "macd": MACD * 2,
                "bar": MACD * 2
            }

        # 计算macd

        MACD_DATA = _count_macd(kline_data['close_price'])
        # 赋值当日macd变量
        self.ema12 = MACD_DATA['ema12']
        self.ema26 = MACD_DATA['ema26']
        self.dif = MACD_DATA['dif']
        self.dea = MACD_DATA['dea']
        self.macd = MACD_DATA['macd']
        return MACD_DATA

