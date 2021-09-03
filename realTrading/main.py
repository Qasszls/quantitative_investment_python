# -*- coding:UTF-8 -*-

import emoji
import numpy as np
import pandas as pd
import sys
import threading
import time
import asyncio
import re
import json
import gc
import os

sys.path.append('..')
from dingtalkchatbot.chatbot import DingtalkChatbot
from util.TimeStamp import TimeTamp
from strategyLibrary.simpleMACDStrategy import StrategyRouter
from okexApi._websocket import PublicSocketApi
from okexApi._websocket import PrivateSocketApi
from okexApi._http import HttpApi


class Trading:
    def __init__(self, check_surplus, stop_loss, lever=10, user_info=None):
        if not user_info:
            print('请填写用户信息')
            return
        # 创建币对路由实例
        self.strategyRouter = StrategyRouter(user_info)
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

        self.check_surplus = check_surplus  # 玩家止盈率
        self.stop_loss = stop_loss  # 玩家止损率
        self.lever = lever  # 杠杆倍数
        # 用户层面
        self._c = 0  # 现金余额 - 默认为USDT
        # 内部变量
        self.buy_times = 0

        # 对照字典表
        self.channel_Dict = {
            'positions': self.update_position,  # 走 同上的函数
            "candle": self.breathing,  # 走 行情检测 函数
            'account': self.update_user,  # 走 更新用户信息 函数
        }

        self.okex_api_info = {
            'instType': 'SPOT',  # 产品类型SPOT：币币、SWAP：永续合约、FUTURES：交割合约、OPTION：期权
            'tdMode': 'cross',  # 交易模式
            'ccy': 'USDT',  # 保证金币种
            'mgnMode': 'cross',  # 保证金模式 isolated：逐仓、cross：全仓
            'ordType': 'market',  # 订单类型
        }

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
            _fun = query(channel)
            _fun(res)

    # 主函数

    def _init(self):
        # 配置杠杆
        self._set_lever()
        # 配置私有公有链接的频道
        self.publicSocketApi.subscription()
        self.privateSocketApi.subscription()
        print('主程序已打开，用户止盈率为：' + str(self.check_surplus * 100) + '%; 止损率为：' +
              str(self.stop_loss * 100) + '%; 默认杠杆倍数为：' + str(self.lever) +
              '倍')
        while True:
            self.get_systm_status()
            time.sleep(18000)

    # 更新持仓数据
    def update_position(self, data):
        position = data['data'][0]
        if position['uplRatio'] != '':
            # 检测止盈止损
            res = self.strategyRouter.isSell(position)
            if res['status']:
                self.allSell(res['share'], position['instId'])

    # 更新用户数据
    def update_user(self, data):
        user_info = data['data'][0]
        return

        # 获取用户的USDT的币种余额
        def _get_usdt(_detail):
            for _coin in _detail:
                if _coin['ccy'] == 'USDT':
                    return _coin['cashBal']
            print('未获取到USDT余额')

        _detail = user_info['details']
        self._c = _get_usdt(_detail)  # 更新用户的USDT的币种余额

    # 重启策略
    def restart(self, _res):
        name = _res['data']
        print(name + '新家园建立')
        if name == 'public':
            time.sleep(3)
            self.publicSocketApi.subscription()

        else:
            time.sleep(3)
            self.privateSocketApi.subscription()

    def dingding_msg(self, text, flag=False):
        webhook = 'https://oapi.dingtalk.com/robot/send?access_token=cb4b89ef41c8008bc4526bc33d2733a8c830f1c10dd6701a58c3ad149d35c8cc'
        ding = DingtalkChatbot(webhook)
        text = text + '\n作业时间：' + self.timeTamp.get_time_normal(
            time.time() * 1000) + ' :525'
        ding.send_text(msg=text, is_at_all=flag)

    # 策略核心内容
    def breathing(self, data):
        # 运行策略 *********** door **************
        self.strategyRouter.run(
            data,
            self.completed,
        )

    # 钩子函数 计算完成
    def completed(self, res):
        medium_status = res['medium_status']  # 初级判断状态
        indicators = res['indicators']  # 指标数据包
        _step = res['step']  # 策略执行步骤
        id_tamp = res['id_tamp']  # 时间戳
        instId = res['instId']
        # 其他数据
        self.dingding_msg('完成节点：' + str(_step) + '\n打卡时间：' +
                          self.timeTamp.get_time_normal(id_tamp) + '\n240均线：' +
                          str(indicators['ema240']))
        if medium_status and self.buy_times <= 4:
            # 买入 钩子
            self.allBuy(instId)

    # 下单
    def allBuy(self, instId):
        try:
            result = self._get_trad_sz(instId)
            # 编辑参数变量
            availBuy = result['availBuy']  # 当前计价货币最大可用的数量 一般是 USDT
            action = 'buy'
            tdMode = self.okex_api_info['tdMode']  # 仓位模式
            ordType = self.okex_api_info['ordType']  # 订单类型
            ccy = self.okex_api_info['ccy']  # 保证金比重

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
        except BaseException as err:
            self.dingding_msg('买入认时出现问题，请注意' + str(err))
            print('买入时出现问题，请注意' + str(err))
        finally:
            if error:
                self.dingding_msg('买入失败' + str(error))
            else:
                self.dingding_msg('买入成功' + str(res))
                self.buy_times = self.buy_times + 1

    def allSell(self, share, instId):
        try:
            # 获取变量
            mgnMode = self.okex_api_info['mgnMode']
            ccy = self.okex_api_info['ccy']

            # 配置策略内容
            params = {
                'instId': instId,
                'mgnMode': mgnMode,
                'ccy': ccy,
            }
            # 改造成按量下单，而不是强行平仓

            # 下订单-市价平仓
            # res, err = self.http.close_position(params)
            # if err:
            #     self.dingding_msg('卖出失败，请手动平仓' + str(err))
            #     self.buy_times = 0
            #     return False
            # else:
            #     self.dingding_msg('卖出成功' + str(res))
            #     self.buy_times = 0
            #     return True
        except BaseException as e:
            print('卖出错误: ', str(e))

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
                        ';\n更新结束时间: ' +
                        self.timeTamp.get_time_normal(item['end']))
                    # print('服务器正在更新中,更新开始时间: ' +
                    #       self.timeTamp.get_time_normal(item['begin']) +
                    #       ';\n更新结束时间: ' +
                    #       self.timeTamp.get_time_normal(item['end']))
                    # 找出最长更新时间段
                    if _utimes < int(item['end']):
                        _utimes = int(item['end'])
                    # 服务器正在更新
                elif item['state'] == 'scheduled':
                    self.dingding_msg(
                        '服务器有更新计划,更新开始时间: ' +
                        self.timeTamp.get_time_normal(item['begin']) +
                        ';\n更新结束时间: ' +
                        self.timeTamp.get_time_normal(item['end']))
                    # print('服务器有更新计划,更新开始时间: ' +
                    #       self.timeTamp.get_time_normal(item['begin']) +
                    #       '; 更新结束时间: ' +
                    #       self.timeTamp.get_time_normal(item['end']))
        elif error:
            # 网络问题 轮询请求接口，等待网络恢复
            print('get_systm_status 出现问题')
            time.sleep(3)
            self.get_systm_status()


# 工具查询---buy/sell阶段-数量

    def _set_lever(self):
        print('杠杆配置中')
        # 设置杠杆倍数 交易前配置
        instId = self.okex_api_info['instId']
        lever = self.lever
        mgnMode = self.okex_api_info['mgnMode']
        _s_p = {'instId': instId, 'lever': lever, 'mgnMode': mgnMode}
        self.http.set_account_set_leverage(_s_p)
        print('杠杆配置完毕')

    def _get_trad_sz(self, instId):
        tdMode = self.okex_api_info['tdMode']
        instType = self.okex_api_info['instType']
        ccy = self.okex_api_info['ccy']
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
    print('我的进程id 是 ', os.getpid())
    # 获取要执行的用户配置
    # macd 底背离
    f = open('../config.json', 'r', encoding='utf-8')
    _data = json.load(f)
    user_info = _data['realPay']['children'][0]
    # 止盈率:5%, 止损率:2%, 测试账户:主账户, 策略运行模式:宽松。
    trading = Trading(user_info=user_info['coin_list'])
    trading._init()
