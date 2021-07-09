# -*- coding:UTF-8 -*-

import pandas as pd
import numpy as np
import emoji
import sys
import threading
import time
import asyncio
import re
from requests.api import request

from tqdm import tqdm

# import pyecharts.options as opts
# from pyecharts.charts import Line

sys.path.append('..')
from util.TimeStamp import TimeTamp
from strategyLibrary.simpleMACDStrategy import SimpleMacd
from okexApi._socket import SocketApi
from okexApi._http import HttpApi
# from sqlHandler import SqlHandler


class Trading:
    def __init__(self, checkSurplus, stopLoss, mode=None, odds=0.03, lever=3):
        self.simpleMacd = SimpleMacd(mode, odds)
        self.socket = SocketApi(callback=self._router,
                                trading_type="virtualPay")  # 初始化长连接
        self.http = HttpApi(trading_type="virtualPay")  # 初始化长连接
        self.timeTamp = TimeTamp()

        self.checkSurplus = checkSurplus  # 玩家止盈率
        self.stopLoss = stopLoss  # 玩家止损率
        self.lever = lever  # 杠杆倍数
        self.upl = ''  # 未实现收益
        self.uplRatio = ''  # 未实现收益率
        #用户层面
        self._c = 0  # 现金余额 - 默认为USDT

        # 内部变量
        self.ema12 = 0
        self.ema26 = 0
        self.dea = 0
        self.old_kl = []
        # 对照字典表
        self.channel_Dict = {
            'balance_and_position':
            self.update_position,  # 走update_position函数、
            'positions': self.update_position,
            "candle": self.breathing,  # 走 breathing 函数
            'account': self.update_user  #走 update_user 函数
        }

        self.btc_shangzuoliu_001 = {
            'instType': 'SPOT',  # 产品类型SPOT：币币、SWAP：永续合约、FUTURES：交割合约、OPTION：期权
            'instId': 'BTC-USDT',  # 交易产品 后期可为数组
            'tdMode': 'cross',  # 交易模式
            # 杠杆部分
            'ccy': 'USDT',  # 保证金币种
            'lever': self.lever,
            'mgnMode': 'cross',  # 保证金模式 isolated：逐仓、cross：全仓
            # 策略部分
            'tpTriggerRate': self.checkSurplus,  # 止盈
            'slTriggerRate': self.stopLoss,  # 止损
            'ordType':
            'market',  # 倾向策略方式 conditional：单向止盈止损、oco：双向止盈止损、trigger：计划委托
        }

    def query(self, channel):

        if channel in self.channel_Dict:
            return self.channel_Dict[channel]
        elif re.search('candle', channel).group():
            return self.channel_Dict['candle']
        else:
            print('调用错误')
            return False

    # 主函数
    def _init(self):
        self._set_lever()
        new_loop = asyncio.new_event_loop()  #在当前线程下创建时间循环，（未启用）
        t = threading.Thread(target=self.start_loop,
                             args=(new_loop, ))  #通过当前线程开启新的线程去启动事件循环
        t.start()
        # 启动私有socket接口轮询的事件循环
        for subscribe in [
                'positions',
                'market',
                # 'account'
        ]:
            asyncio.run_coroutine_threadsafe(self.socket.run(subscribe),
                                             new_loop)

    # 运行事件循环
    def start_loop(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    # 推送路由
    def _router(self, res):
        channel = res['arg']['channel']
        data = res['data'][0]
        _fun = self.query(channel)
        _fun(data)

    # 更新持仓数据
    def update_position(self, data):
        def _is_checkSurplus():
            return self.uplRatio >= self.checkSurplus

        def _is_sotpLoss():
            return self.uplRatio <= self.stopLoss

        self.upl = float(data['upl'])
        self.uplRatio = float(data['uplRatio'])

        # 检测止盈止损
        if _is_checkSurplus() or _is_sotpLoss():
            self.allSell(1)

    # 更新用户数据
    def update_user(self, data):

        # 获取用户的USDT的币种余额
        def _get_usdt(_detail):
            for _coin in _detail:
                if _coin['ccy'] == 'USDT':
                    return _coin['cashBal']
            print('未获取到USDT余额')

        _detail = data['detail']

        self._c = _get_usdt(_detail)  # 更新用户的USDT的币种余额

    # 工具查询---buy/sell阶段-数量
    def _set_lever(self):
        #设置杠杆倍数 交易前配置
        instId = self.btc_shangzuoliu_001['instId']
        lever = self.btc_shangzuoliu_001['lever']
        mgnMode = self.btc_shangzuoliu_001['mgnMode']
        _s_p = {'instId': instId, 'lever': lever, 'mgnMode': mgnMode}
        self.http.set_account_set_leverage(_s_p)

    def _get_trad_sz(self):
        instId = self.btc_shangzuoliu_001['instId']
        tdMode = self.btc_shangzuoliu_001['tdMode']
        instType = self.btc_shangzuoliu_001['instType']
        ccy = self.btc_shangzuoliu_001['ccy']
        lever = self.btc_shangzuoliu_001['lever']
        _max_size_params = {
            'instId': instId,
            'tdMode': tdMode,
        }
        if tdMode == 'cross':
            _max_size_params['ccy'] = ccy
        # 获得野生可购买数量 - 烹饪食材
        _m_a_s_data = self.http.get_account_max_avail_size(_max_size_params)
        _m_s_availBuy = float(_m_a_s_data['availBuy'])  # 获得最大买入数量 ***
        _m_s_availSell = float(_m_a_s_data['availSell'])  # 获得最大卖出数量 ***

        # 获取交易产品基础信息 - 烹饪调料
        _p_i_result = self.http.get_public_instruments({
            'instType': instType,
            'instId': instId
        })
        _p_i_lotSz = _p_i_result['lotSz']  # 最小下单数量精度 ***

        # 具体可购买数量 - 开启烹饪
        _sz = len(str(_p_i_lotSz).split('.')[1])
        _m_s_availBuy = round(_m_s_availBuy, _sz)
        _m_s_availSell = round(_m_s_availSell, _sz)

        # 出参 - 装盘上菜
        return {
            'availBuy': _m_s_availBuy,
            'availSell': _m_s_availSell,
        }

    # 获取最新成交价 askPx/bidPx
    def _get_market_ticker(self):
        instId = self.btc_shangzuoliu_001['instId']
        params = {'instId': instId}
        result = self.http.market_ticker(params)
        askPx = result['askPx']
        return {'askPx': askPx}

    # 策略核心内容
    def breathing(self, kline_data):
        #判断新老数据
        if kline_data[0] in self.old_kl:
            return
        # 准备数据-kline
        self.old_kl = kline_data
        kline_data = pd.DataFrame([kline_data]).astype(float)
        kline_data.columns = [
            'id_tamp', 'open_price', 'high_price', 'lowest_price',
            'close_price', 'vol', 'volCcy'
        ]
        KLINE_DATA = kline_data.to_dict('records')[0]
        # 准备数据-macd
        MACD_DATA = self._befor_investment(KLINE_DATA)

        # 运行策略 *********** door **************
        self.simpleMacd.runStrategy(
            KLINE_DATA,
            MACD_DATA,
            self.onCalculate,
            self.completed,
        )

    #钩子函数 计算中
    def onCalculate(self, res):
        # 变量定义
        None

    #钩子函数 计算完成
    def completed(self, res):
        medium_status = res['medium_status']  # 初级判断状态
        kline_data = res['kline_data']  # k线数据包

        close_price = kline_data['close_price']  # 收盘价
        id_tamp = kline_data['id_tamp']  # 时间戳
        if medium_status and self.principal >= close_price:
            #买入 钩子
            self.allBuy(id_tamp)

        # 数据装车

    # 下单
    def allBuy(self, id_tamp):
        result = self._get_trad_sz()
        action = 'buy'
        availBuy = result['availBuy']  # 当前币对最大可用的数量
        # 获取变量
        instId = self.btc_shangzuoliu_001['instId']
        tdMode = self.btc_shangzuoliu_001['tdMode']
        ordType = self.btc_shangzuoliu_001['ordType']
        ccy = self.btc_shangzuoliu_001['ccy']

        # 配置策略内容
        params = {
            'instId': instId,
            'tdMode': tdMode,
            'side': action,
            'ordType': ordType,
            'sz': availBuy * 0.7,
            'ccy': ccy,
        }
        # 下订单-市价买入
        self.http.trade_order(params)

    def allSell(self, id_tamp):
        ccy = self.btc_shangzuoliu_001['ccy']
        instId = self.btc_shangzuoliu_001['instId']
        mgnMode = self.btc_shangzuoliu_001['mgnMode']

        _p = {'instId': instId, 'mgnMode': mgnMode, 'ccy': ccy}

        result, error = self.http.close_position(_p)
        print('卖出！')

    def _befor_investment(self, kline_data):
        # 计算macd
        MACD_DATA = self._count_macd(kline_data['close_price'])
        # 赋值当日macd变量
        self.ema12 = MACD_DATA['ema12']
        self.ema26 = MACD_DATA['ema26']
        self.dif = MACD_DATA['dif']
        self.dea = MACD_DATA['dea']
        self.macd = MACD_DATA['macd']
        return MACD_DATA

    def _count_macd(self, price):
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
        EMA26 = last_ema26 * 11 / 27 + price * 2 / 27
        DIF = EMA12 - EMA26
        DEA = last_dea * 8 / 10 + DIF * 2 / 10
        MACD = DIF - DEA

        return {
            'ema12': EMA12,
            'ema26': EMA26,
            'dif': DIF,
            "dea": DEA,
            "macd": MACD,
            "bar": MACD * 2
        }


if __name__ == "__main__":
    trading = Trading(0.16, 0.075)
    trading._init()
