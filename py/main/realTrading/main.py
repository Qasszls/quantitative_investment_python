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
from okexApi._socket import SocketApi
from okexApi._http import HttpApi
from sqlHandler import SqlHandler


class Trading:
    def __init__(self,
                 checkSurplus,
                 stopLoss,
                 mode=None,
                 odds=0.05,
                 lever=2,
                 user_info=None):
        if not user_info:
            print('请填写用户信息')
            return

        self.table_name = user_info['table_name']

        self.simpleMacd = SimpleMacd(mode, odds)
        self.socket = SocketApi(on_message=self._router,
                                on_error=self.restart,
                                user_info=user_info)  # 初始化长连接
        self.http = HttpApi(user_info=user_info)  # 初始化短连接
        self.timeTamp = TimeTamp()  # 初始化时间操作对象
        self.sqlHandler = SqlHandler(  # 初始化数据库操作对象
            ip='127.0.0.1',
            userName='root',
            userPass='qass-utf-8',
            DBName='BTC-USDT_kline',
            charset='utf8',
        )

        self.checkSurplus = checkSurplus  # 玩家止盈率
        self.stopLoss = stopLoss  # 玩家止损率
        self.lever = lever  # 杠杆倍数
        # self.upl = ''  # 未实现收益
        # self.uplRatio = ''  # 未实现收益率
        #用户层面
        self._c = 0  # 现金余额 - 默认为USDT

        # 内部变量
        self.buy_times = 0
        # 1m
        # self.ema12 = 29656.0
        # self.ema26 = 29671.5
        # self.dea = -15.1924
        # 15m
        self.ema12 = 39707.8
        self.ema26 = 39736.5
        self.dea = -31.5827
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
        self._set_lever()
        #配置私有公有链接的频道
        _pri = self.btc_shangzuoliu_001['subscribe']['private']
        _pub = self.btc_shangzuoliu_001['subscribe']['public']
        for item in _pub:
            self.socket.run(public_subscribe=item)
        for item in _pri:
            self.socket.run(private_subscribe=item)

        while True:
            self.get_systm_status()
            time.sleep(1800)

    # 更新持仓数据
    def update_position(self, data):
        self.upl = float(data['upl'])
        uplRatio = abs(float(data['uplRatio']))

        def _is_checkSurplus():
            return uplRatio >= self.checkSurplus

        def _is_sotpLoss():
            return uplRatio >= self.stopLoss

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
        subscribe = _res['data']
        if self.is_public(subscribe):
            self.dingding_msg('重启公有星球')
            time.sleep(5)
            self.socket.run(public_subscribe=subscribe)
        else:
            self.dingding_msg('重启私有星球')
            time.sleeo(5)
            self.socket.run(private_subscribe=subscribe)

        # print('星球重启---开启新的征程', gc.collect())

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
        text = text + ' :525'
        print(text, flag)
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
            # 运行策略 *********** door **************
            self.simpleMacd.runStrategy(
                KLINE_DATA,
                MACD_DATA,
                self.onCalculate,
                self.completed,
            )
            self.old_kl = kline_data

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

        if medium_status and self.buy_times <= 2:
            #买入 钩子
            self.allBuy()

        # 数据装车
        # 把用户与行情数据存入
        _kline_list = kline_data
        # 回测数据--数据打包
        _kline_list.update({
            'date': self.timeTamp.get_time_normal(id_tamp),
            'is_buy_set': 'wait'
        })

        # 行情数据———macd 打包
        _kline_list.update({
            'dif': macd_data['dif'],
            "dea": macd_data['dea'],
            "macd": macd_data['macd'],
            "bar": macd_data['bar'] * 2
        })
        # 自定义数据 -- 研判步骤 打包
        _kline_list['step'] = str(_step)
        # 装车
        res = self.sqlHandler.insert_trade_marks_data(_kline_list,
                                                      self.table_name)
        # self.dingding_msg('完成节点:' + self.timeTamp.get_time_normal(id_tamp))

        # print('完成节点:'+ self.timeTamp.get_time_normal(id_tamp))

    # 下单
    def allBuy(self):
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
            'sz': availBuy * 2,
            'ccy': ccy,
        }
        # 下订单-市价买入
        print('下订单-市价买入')
        res, error = self.http.trade_order(params)
        print(res, error)
        if error:
            self.dingding_msg('买入失败' + str(error))
            return
        else:
            self.dingding_msg('买入成功' + str(res))
            self._trading_record(ordId=res[0]['ordId'], is_buy_set='1')

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
        print('下订单-市价平仓')
        res, err = self.http.close_position(params)
        if err:
            # print('sell error', res)
            self.dingding_msg('卖出失败，请手动平仓' + str(err))
            self._trading_record(ordId=None, is_buy_set='0')
            return
        else:

            self.dingding_msg('卖出成功' + str(res))
            self._trading_record(ordId=None, is_buy_set='0')

    # 记录交易点
    def _trading_record(self, ordId, is_buy_set):
        params = (self.table_name, {
            'is_buy_set': is_buy_set,
            'date_key': None
        })
        _now_tamp = None
        # 有订单ID，正常下单
        if ordId:
            instId = self.btc_shangzuoliu_001['instId']
            res, error = self.http.search_order({
                'instId': instId,
                'ordId': ordId
            })
            if res:
                _data = res[0]
                if self.buy_times > 1:
                    _now_tamp = _data['cTime']
                else:
                    _now_tamp = _data['uTime']
        # 没有订单ID，市价全平
        else:
            res, error = self.http.get_public_time()
            _now_tamp = res[0]['ts']

        # 存入数据库
        try:
            _sr = self.sqlHandler.select_trade_marks_data(
                self.table_name, _now_tamp)

            # 取出list中最后一个元素，作为交易的时间。
            _tamp = _sr['result'][len(_sr['result']) - 1][0]
            params['date_key'] = _tamp

            _ur = self.sqlHandler.update_buy_set(params)

            if _ur['status']:
                if is_buy_set == '1':
                    self.buy_times = self.buy_times + 1
                else:
                    self.buy_times = 0
                print('写入结束')
                print('写入交易点成功，code=', is_buy_set, '。交易时间为：',
                      self.timeTamp.get_time_normal(_tamp), '交易价格为:',
                      res['avgPx'])
            else:
                print('写入交易点失败code=', is_buy_set)
        except:
            print("Error: 请处理", self.timeTamp.get_time_normal(_now_tamp))

    # 获取服务器更新节点
    def get_systm_status(self):
        _ures, error = self.http.get_update_status()
        if not error and len(_ures) > 0:
            for item in _ures:
                if item['state'] == 'ongoing':
                    _udate_start = _ures['start']  # 服务器更新完成时间
                    _udate_end = _ures['end']  # 服务器更新完成时间
                    self.dingding_msg(
                        _ures, '服务器返回数据', '更新开始时间: ',
                        self.timeTamp.get_time_normal(_udate_start),
                        '更新结束时间: ', self.timeTamp.get_time_normal(_udate_end))
                    # 服务器正在更新
                    print(_ures, '更新中，谨慎恢复')
                    return
        elif error:
            # 网络问题 轮询请求接口，等待网络恢复
            print('get_systm_status 出现问题')
            self.get_systm_status()
        else:
            self.dingding_msg('服务器没有更新计划')

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
        #设置杠杆倍数 交易前配置
        instId = self.btc_shangzuoliu_001['instId']
        lever = self.btc_shangzuoliu_001['lever']
        mgnMode = self.btc_shangzuoliu_001['mgnMode']
        _s_p = {'instId': instId, 'lever': lever, 'mgnMode': mgnMode}
        res, err = self.http.set_account_set_leverage(_s_p)
        if err:
            time.sleep(2)
            self._set_lever()

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

    # 获取最新成交价 askPx/bidPx
    def _get_market_ticker(self):
        instId = self.btc_shangzuoliu_001['instId']
        params = {'instId': instId}
        result, error = self.http.market_ticker(params)
        askPx = result[0]['askPx']
        return {'askPx': askPx}

if __name__ == "__main__":
    # 获取要执行的用户配置

    # macd 底背离
    f = open('../config.json', 'r', encoding='utf-8')
    _data = json.load(f)
    _ulist = _data['realPay']
    # 止盈率:5%, 止损率:2%, 测试账户:主账户, 策略运行模式:宽松。
    trading = Trading(0.05, 0.02, user_info=_ulist, mode='loose')
    trading._init()
    # for item in _ulist['children']:
    #     if item['name'] == 'qassChildrenTwo':
    #         trading = Trading(1.2, 0.20, user_info=item)
    #         trading._init()
