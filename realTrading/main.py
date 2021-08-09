# -*- coding:UTF-8 -*-

from dingtalkchatbot.chatbot import DingtalkChatbot
import pandas as pd
import numpy as np
import emoji
import sys
import threading
import time
import asyncio
import re
import json
import gc

sys.path.append('..')
from util.TimeStamp import TimeTamp
from strategyLibrary.simpleMACDStrategy import SimpleMacd
from okexApi._websocket import PublicSocketApi
from okexApi._websocket import PrivateSocketApi
from okexApi._http import HttpApi


class Trading:
    def __init__(self,
                 checkSurplus,
                 stopLoss,
                 mode=None,
                 odds=0.05,
                 lever=10,
                 user_info=None):
        if not user_info:
            print('请填写用户信息')
            return

        self.simpleMacd = SimpleMacd(mode, odds)
        self.publicSocketApi = PublicSocketApi(on_created=None,
                                               on_message=self._router,
                                               on_closed=self.restart,
                                               user_info=user_info)  # 初始化长连接
        self.privateSocketApi = PrivateSocketApi(on_created=None,
                                                 on_message=self._router,
                                                 on_closed=self.restart,
                                                 user_info=user_info)  # 初始化长连接
        self.http = HttpApi(user_info=user_info)  # 初始化短连接
        self.timeTamp = TimeTamp()  # 初始化时间操作对象

        self.checkSurplus = checkSurplus  # 玩家止盈率
        self.stopLoss = stopLoss  # 玩家止损率
        self.lever = lever  # 杠杆倍数
        self.update_times = 0
        # self.upl = ''  # 未实现收益
        # self.uplRatio = ''  # 未实现收益率
        #用户层面
        self._c = 0  # 现金余额 - 默认为USDT

        # 内部变量
        self.buy_times = 0
        # 15m
        self.ema12 = float(user_info['ema12'])
        self.ema26 = float(user_info['ema26'])
        self.dea = float(user_info['dea'])
        self.old_kl = []
        # 对照字典表
        self.channel_Dict = {
            'balance_and_position': self.update_position,  # 走 更新持仓信息 函数、
            'positions': self.update_position,  # 走 同上的函数
            "candle": self.breathing,  # 走 行情检测 函数
            'account': self.update_user,  #走 更新用户信息 函数
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
            'subscribe': user_info['subscribe'],  # 监听的频道列表
        }

    # 是否是公共频道
    def is_public(self, _s):
        public_subscribe = self.btc_shangzuoliu_001['subscribe']['public']
        return _s in public_subscribe

    # 推送路由
    def _router(self, res):
        def query(channel):
            if channel in self.channel_Dict:
                return self.channel_Dict[channel]
            elif re.search('candle', channel).group():
                return self.channel_Dict['candle']
            else:
                print('调用错误')
                return False

    # okex 回调数据

        channel = res['arg']['channel']
        # 如果回调数据 data长度为0，说明暂无数据，调用无效
        if len(res['data']) == 0:
            return
        else:
            data = res['data'][0]
            _fun = query(channel)
            _fun(data)

    # 主函数

    def _init(self):
        # 配置杠杆
        self._set_lever()
        #配置私有公有链接的频道
        self.publicSocketApi.subscription()
        self.privateSocketApi.subscription()
        print('服务器状态轮询准备开启')
        while True:
            print('服务器状态轮询中……')
            self.get_systm_status()
            time.sleep(3600)

    # 更新持仓数据
    def update_position(self, data):
        if data['upl'] != '':
            upl = float(data['upl'])
            uplRatio = float(data['uplRatio'])

            def _is_checkSurplus():
                return uplRatio >= self.checkSurplus

            def _is_sotpLoss():
                return abs(uplRatio) >= self.stopLoss

            # 检测止盈止损
            if _is_checkSurplus() or _is_sotpLoss():
                self.allSell()

    # 更新用户数据
    def update_user(self, data):
        # 获取用户的USDT的币种余额
        def _get_usdt(_detail):
            for _coin in _detail:
                if _coin['ccy'] == 'USDT':
                    return _coin['cashBal']
            print('未获取到USDT余额')

        _detail = data['details']
        self._c = _get_usdt(_detail)  # 更新用户的USDT的币种余额

    # 重启策略
    def restart(self, _res):
        if self.update_times > 0:
            _ntamp = time.time() * 1000
            print('当前时间')
            print(time.time() * 1000, '未来时间', _ntamp, '睡眠',
                  (self.update_times - _ntamp) / 1000, '秒')
            self.dingding_msg('当前时间' + str(time.time() * 1000) + '未来时间' +
                              str(_ntamp) + '睡眠' +
                              str((self.update_times - _ntamp) / 1000) + '秒')
            time.sleep(self.update_times - _ntamp)
        name = _res['data']
        print(name + '新家园建立')
        if name == 'public':
            time.sleep(3)
            self.publicSocketApi.subscription()

        else:
            time.sleep(3)
            self.privateSocketApi.subscription()

    # 是服务器的原因 还是 网络的原因
    # 是服务器的原因 请求服务器获取服务器时间，根据服务器时间计算出恢复时间点，在其后五秒执行恢复方法
    # 否则如果是私有频道，直接恢复
    # 不然就执行谨慎的恢复方法
    # 谨慎的恢复方法为
    # 材料： 链接中断时的时间戳
    # 准备1： 根据【链接中断时的时间戳】推断出 链接中断的时间节点
    # 准备2： 传送【链接中断的时间节点】给服务器，获取目前时间到 该时间节点的所有k线数据
    # 准备3： 根据k线数据计算每一节点的【量化数据（list）】
    # 阶段： 在谨慎的恢复方法执行之前
    # 1.判断主线程与当前服务器时间间隔N（秒），N小于等于30秒的，仍认为当前数据连接中断状态
    # 2.使用time.sleep方法模拟中断时间，入参为N。
    # 阶段： 在谨慎的恢复方法执行之中
    # 1.N秒后遍历【量化数据（list）】并调用breathing方法进行计算与数据落库的工作（争议：在此期间买点、卖点被激活怎么办？）
    # 2.调用 socket.run 方法重启被中断的链接

    # 策略核心内容
    def dingding_msg(self, text, flag=False):
        webhook = 'https://oapi.dingtalk.com/robot/send?access_token=cb4b89ef41c8008bc4526bc33d2733a8c830f1c10dd6701a58c3ad149d35c8cc'
        ding = DingtalkChatbot(webhook)
        text = text + self.timeTamp.get_time_normal(
            time.time() * 1000) + ' :525'
        ding.send_text(msg=text, is_at_all=flag)

    def breathing(self, kline_data):
        # 判断新老数据
        # 第一次进入循环 或者 同一时间的老数据，都会进入
        if kline_data[0] in self.old_kl:
            # 其实可以完全不写下面的代码，但是意义就不一样了。
            self.old_kl = kline_data
            return
        else:
            # 防止数据为初始化就走下面的逻辑
            if len(self.old_kl) == 0:
                self.old_kl = kline_data
                return

            _k = pd.DataFrame([self.old_kl]).astype(float)
            _k.columns = [
                'id_tamp', 'open_price', 'high_price', 'lowest_price',
                'close_price', 'vol', 'volCcy'
            ]
            KLINE_DATA = _k.to_dict('records')[0]
            # 准备数据-macd
            MACD_DATA = self._befor_investment(KLINE_DATA)
            self.old_kl = kline_data
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
        macd_data = res['macd_data']  # macd数据包
        _step = res['step']  # 策略执行步骤
        id_tamp = kline_data['id_tamp']  # 时间戳
        self.dingding_msg('时间：' + self.timeTamp.get_time_normal(id_tamp) +
                          '已完成，步骤：' + str(_step))
        if medium_status and self.buy_times <= 2:
            #买入 钩子
            self.allBuy()

    # 下单
    def allBuy(self):
        try:
            result = self._get_trad_sz()
        except BaseException as err:
            self.dingding_msg('获得计价货币函数出现问题, 重启函数' + str(err))
            print('获得计价货币函数出现问题, 重启函数' + str(err))
        action = 'buy'
        availBuy = result['availBuy']  # 当前计价货币最大可用的数量 一般是 USDT
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
            'sz': availBuy * self.lever * 0.50,  # 计价货币乘上杠杆 再半仓，优化保证金率，控制风险
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
        instId = self.btc_shangzuoliu_001['instId']
        mgnMode = self.btc_shangzuoliu_001['mgnMode']
        ccy = self.btc_shangzuoliu_001['ccy']

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

    # 获取服务器更新节点
    def get_systm_status(self):
        _ures, error = self.http.get_update_status()
        if not error and len(_ures) > 0:
            _utimes = 0
            for item in _ures:
                if item['state'] == 'ongoing':
                    self.dingding_msg(
                        '服务器正在更新中,更新开始时间: ' +
                        self.timeTamp.get_time_normal(item['begin']) +
                        '; 更新结束时间: ' +
                        self.timeTamp.get_time_normal(item['end']))
                    print('服务器正在更新中,更新开始时间: ' +
                          self.timeTamp.get_time_normal(item['begin']) +
                          '; 更新结束时间: ' +
                          self.timeTamp.get_time_normal(item['end']))
                    # 找出最长更新时间段
                    if _utimes < int(item['end']):
                        _utimes = int(item['end'])
                    # 服务器正在更新
                elif item['state'] == 'scheduled':
                    self.dingding_msg(
                        '服务器有更新计划,更新开始时间: ' +
                        self.timeTamp.get_time_normal(item['begin']) +
                        '; 更新结束时间: ' +
                        self.timeTamp.get_time_normal(item['end']))
                    print('服务器有更新计划,更新开始时间: ' +
                          self.timeTamp.get_time_normal(item['begin']) +
                          '; 更新结束时间: ' +
                          self.timeTamp.get_time_normal(item['end']))
            self.update_times = _utimes
        elif error:
            # 网络问题 轮询请求接口，等待网络恢复
            print('get_systm_status 出现问题')
            time.sleep(3)
            self.get_systm_status()
        else:
            self.dingding_msg('策略运行中，服务器没有更新计划')

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
        print('杠杆配置中')
        #设置杠杆倍数 交易前配置
        instId = self.btc_shangzuoliu_001['instId']
        lever = self.btc_shangzuoliu_001['lever']
        mgnMode = self.btc_shangzuoliu_001['mgnMode']
        _s_p = {'instId': instId, 'lever': lever, 'mgnMode': mgnMode}
        self.http.set_account_set_leverage(_s_p)
        print('杠杆配置完毕')

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
        print('获得野生可购买数量 - 烹饪食材')
        _m_a_s_data, error = self.http.get_account_max_avail_size(
            _max_size_params)
        _m_a_s_data = _m_a_s_data[0]
        _m_s_availBuy = float(_m_a_s_data['availBuy'])  # 获得最大买入数量 ***
        _m_s_availSell = float(_m_a_s_data['availSell'])  # 获得最大卖出数量 ***
        # 获取交易产品基础信息 - 烹饪调料
        print('获取交易产品基础信息 - 烹饪调料')
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

if __name__ == "__main__":
    # 获取要执行的用户配置

    # macd 底背离
    f = open('../config.json', 'r', encoding='utf-8')
    _data = json.load(f)
    _ulist = _data['realPay']['children'][0]
    # 止盈率:5%, 止损率:2%, 测试账户:主账户, 策略运行模式:宽松。
    trading = Trading(0.12, 0.05, user_info=_ulist, mode='loose')
    trading._init()
