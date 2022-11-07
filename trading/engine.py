# -*- coding:UTF-8 -*-
from atexit import register
import json
import time
import emoji
import numpy as np
import pandas as pd

from share.TimeStamp import Timestamp
from strategyLibrary.simpleMACDStrategy import SimpleMacd
from events.engine import EventEngine, Event
from events.event import EVENT_TICK, EVENT_POSITION, EVENT_COMPUTED, EVENT_DING, EVENT_LOG
from logging import INFO


class Trading:
    def __init__(self,
                 event_engine: EventEngine,
                 http,
                 user_info=None):
        if not user_info:
            print('请填写用户信息')
            return

        self.timestamp = Timestamp()  # 初始化时间操作对象
        self.event_engine = event_engine
        self.http = http

        self.checkSurplus = 0.11  # 玩家止盈率
        self.stopLoss = 0.07  # 玩家止损率
        self.lever = 10  # 杠杆倍数
        self.update_times = 0

        self.simpleMacd = SimpleMacd(self.event_engine)

        # 内部变量
        self.buy_times = 0
        # 15m
        self.ema12 = float(user_info['ema12'])
        self.ema26 = float(user_info['ema26'])
        self.dea = float(user_info['dea'])
        self.old_kl = []

        self.okex_api_info = {
            'instType': 'SPOT',  # 产品类型SPOT：币币、SWAP：永续合约、FUTURES：交割合约、OPTION：期权
            'instId': user_info['symbol'],  # 交易产品 后期可为数组
            'tdMode': 'cross',  # 交易模式
            # 杠杆部分
            'ccy': 'USDT',  # 保证金币种
            'lever': self.lever,
            'mgnMode': 'cross',  # 保证金模式 isolated：逐仓、cross：全仓
            # 策略部分
            'ordType':
            'market',  # 倾向策略方式 conditional：单向止盈止损、oco：双向止盈止损、trigger：计划委托
            'subscribe': user_info['subscribe'],  # 监听的频道列表
        }

    def dingding_msg(self, msg):
        event: Event = Event(EVENT_DING, msg)
        self.event_engine.put(event)

    def start(self):
        self._set_lever()
        # 监听数据回调
        self.event_engine.register(EVENT_TICK, self.breathing)
        self.event_engine.register(EVENT_POSITION, self.update_position)
        # 监听策略回调
        self.event_engine.register(EVENT_COMPUTED, self.completed)

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
                return abs(uplRatio) >= self.stopLoss

            # 检测止盈止损
            if _is_checkSurplus() or _is_sotpLoss():
                self.allSell()

    def breathing(self, kline_event):
        kline_data = kline_event.data['data'][0]
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
                'close_price', 'vol', 'volCcy'
            ]
            KLINE_DATA = _k.to_dict('records')[0]
            # 准备数据-macd
            MACD_DATA = self._befor_investment(KLINE_DATA)
            # 运行策略 *********** door **************
            self.simpleMacd.runStrategy(
                KLINE_DATA,
                MACD_DATA
            )
            self.old_kl = kline_data

    # 钩子函数 计算中

    def onCalculate(self, res):
        # 变量定义
        None

    # 钩子函数 计算完成
    def completed(self, res):
        data = res.data
        medium_status = data['medium_status']  # 初级判断状态
        kline_data = data['kline_data']  # k线数据包
        # macd_data = data['macd_data']  # macd数据包
        _step = data['step']  # 策略执行步骤

        id_tamp = kline_data['id_tamp']  # 时间戳
        self.dingding_msg('已完成，步骤：' + str(_step) + ' ,买卖区间起点：' +
                          self.timestamp.get_time_normal(id_tamp))
        if medium_status and self.buy_times <= 2:
            # 买入 钩子
            self.allBuy()

    # 下单
    def allBuy(self):
        try:
            result = self._get_trad_sz()
        except BaseException as err:
            self.dingding_msg('获得计价货币函数出现问题, 重启函数' + str(err))
        action = 'buy'
        availBuy = result['availBuy']  # 当前计价货币最大可用的数量 一般是 USDT
        # 获取变量
        instId = self.okex_api_info['instId']
        tdMode = self.okex_api_info['tdMode']
        ordType = self.okex_api_info['ordType']
        ccy = self.okex_api_info['ccy']

        # 配置策略内容
        params = {
            'instId': instId,
            'tdMode': tdMode,
            'side': action,
            'ordType': ordType,
            'sz': availBuy * self.lever * 0.15,  # 计价货币乘上杠杆 再半仓，优化保证金率，控制风险
            'ccy': ccy,
        }
        # 下订单-市价买入
        res, error = self.http.trade_order(params)
        if error:
            self.dingding_msg('买入失败' + str(error))
        else:
            self.dingding_msg('买入成功' + str(res))

    def allSell(self):
        # 获取变量
        instId = self.okex_api_info['instId']
        mgnMode = self.okex_api_info['mgnMode']
        ccy = self.okex_api_info['ccy']

        # 配置策略内容
        params = {
            'instId': instId,
            'mgnMode': mgnMode,
            'ccy': ccy,
        }
        # 下订单-市价平仓
        res, err = self.http.close_position(params)
        if err:
            self.dingding_msg('卖出失败，请手动平仓' + str(err))
        else:
            self.dingding_msg('卖出成功' + str(res))

    def _befor_investment(self, kline_data):
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


# 工具查询---buy/sell阶段-数量


    def _set_lever(self):
        self.log('杠杆配置中')
        # 设置杠杆倍数 交易前配置
        instId = self.okex_api_info['instId']
        lever = self.okex_api_info['lever']
        mgnMode = self.okex_api_info['mgnMode']
        _s_p = {'instId': instId, 'lever': lever, 'mgnMode': mgnMode}
        self.http.set_account_set_leverage(_s_p)
        self.log('杠杆配置完毕')

    def _get_trad_sz(self):
        instId = self.okex_api_info['instId']
        tdMode = self.okex_api_info['tdMode']
        instType = self.okex_api_info['instType']
        ccy = self.okex_api_info['ccy']
        lever = self.okex_api_info['lever']
        _max_size_params = {
            'instId': instId,
            'tdMode': tdMode,
        }
        if tdMode == 'cross':
            _max_size_params['ccy'] = ccy
        # 获得野生可购买数量 - 烹饪食材
        _m_a_s_data, error = self.http.get_account_max_avail_size(
            _max_size_params)
        _m_a_s_data = _m_a_s_data[0]
        _m_s_availBuy = float(_m_a_s_data['availBuy'])  # 获得最大买入数量 ***
        _m_s_availSell = float(_m_a_s_data['availSell'])  # 获得最大卖出数量 ***
        # 获取交易产品基础信息 - 烹饪调料
        _p_i_result, error = self.http.get_public_instruments({
            'instType': instType,
            'instId': instId
        })
        _p_i_lotSz = _p_i_result[0]['lotSz']  # 最小下单数量精度 ***
        # 具体可购买数量 - 开启烹饪
        _sz = len(str(_p_i_lotSz).split('.')[1])
        _m_s_availBuy = round(_m_s_availBuy, _sz)
        _m_s_availSell = round(_m_s_availSell, _sz)

        # 出参 - 装盘上菜
        return {
            'availBuy': _m_s_availBuy,
            'availSell': _m_s_availSell,
        }

    def log(self, msg, level=INFO):
        data = {'msg': msg, 'level': level}
        event: Event = Event(EVENT_LOG, data)
        self.event_engine.put(event)
