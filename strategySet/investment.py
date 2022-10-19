# -*- conding -*-

import pandas as pd
import numpy as np
import emoji
import sys
import threading
import time

from tqdm import tqdm

# import pyecharts.options as opts
# from pyecharts.charts import Line

sys.path.append('..')
from share.TimeStamp import TimeTamp
from strategyLibrary.simpleMACDStrategy import SimpleMacd
from sqlHandler import SqlHandler


class Investment(threading.Thread):
    def __init__(self,
                 checkSurplus,
                 stopLoss,
                 principal,
                 klineMediumLevel,
                 medDF,
                 table_name,
                 mode,
                 odds,
                 _name,
                 leverage=1,
                 threadID=None):
        """
        初始化
            止盈率 浮点型
            止损率 浮点型
            本金    浮点型
            资产(个) 浮点型
            交易价格 
            购币痕迹 
        """
        threading.Thread.__init__(self)
        # 数据导入 - 大型数据包
        self.klineMediumLevel = klineMediumLevel  # 初级k线数据包
        self.medDF = medDF  # 初级macd数据包
        # 入参赋值
        self.checkSurplus = float(checkSurplus)  # 止盈
        self.stopLoss = float(stopLoss)  # 止损
        self.principal = float(principal)  # 头寸
        self.table_name = table_name  # 表名
        self.mode = mode  # 宽容模式
        self.odds = odds  # 宽容度
        self.name = _name  # 数据别名
        #内部变量 - 买入时间
        self.buy_time = None
        # 内部变量 - 杠杆部分
        self.leverage = float(leverage)  # 杠杆倍数
        self.le_Amount = 0  # 杠杆金额
        # 内部变量 - 手续费部分
        self.entry_orders_rate = 0.0008  # 挂单费率
        self.eat_orders_rate = 0.001  # 吃单费率
        self.interest_rate = 0.0002  # 借币利率

        # 命名进程
        if not threadID:
            self.threadID = str(int(self.checkSurplus * 100)) + '_' + str(
                int(self.stopLoss * 100)) + '_' + str(
                    self.principal) + '_' + self.name
        else:
            self.threadID = threadID
        # 内部变量
        self.property = 0
        self.tradingPrice = 0
        self.buyTraces = 0
        self.timeTamp = TimeTamp()
        self.sqlHandler = SqlHandler(
            ip='127.0.0.1',
            userName='root',
            userPass='qass-utf-8',
            DBName='BTC-USDT_kline',
            charset='utf8',
        )

    def run(self):
        # 实例化核心算法对象----本级别
        self.pbar = tqdm(total=(len(self.klineMediumLevel) - 1))
        simpleMacd = SimpleMacd(self.mode, self.odds)
        for index in range(len(self.medDF['macd']) - 1):
            simpleMacd.runStrategy(
                self.klineMediumLevel.loc[index].to_dict(),
                self.medDF.loc[index].astype(float).to_dict(),
                self.onCalculate,
                self.completed,
            )

        self.pbar.set_description(
            emoji.emojize(
                '回测线程' + self.threadID + '已结束。   目前总资产：' + str(
                    round((self.property * self.klineMediumLevel.loc[
                        len(self.klineMediumLevel) - 1]['close_price'] -
                           self.le_Amount), 3) + self.principal) + '💰' +
                self.timeTamp.get_time_normal(self.klineMediumLevel.loc[
                    len(self.klineMediumLevel) - 1]['id_tamp']) + '   🖥'))
        self.pbar.update(len(self.klineMediumLevel))
        return {
            "checkSurplus":
            self.checkSurplus,
            "stopLoss":
            self.stopLoss,
            "principal":
            self.principal,
            "property":
            self.property,
            "value": (self.property *
                      self.klineMediumLevel.loc[len(self.klineMediumLevel) -
                                                1]['close_price']),
            "tradingPrice":
            self.tradingPrice
        }

    #钩子函数 计算中
    def onCalculate(self, res):
        # 变量定义
        id_tamp = res['id_tamp']  # 时间戳
        close_price = res['close_price']  # 收盘价

        self.pbar.set_description(
            emoji.emojize('回测线程：' + self.threadID + '   目前总资产：' + str(
                round((self.property * close_price) + self.principal -
                      self.le_Amount, 3)) + '💰' +
                          self.timeTamp.get_time_normal(id_tamp) + '   🖥'))
        self.pbar.update(1)

    #钩子函数 计算完成
    def completed(self, res):
        _step = res['step']  # 策略执行步骤
        medium_status = res['medium_status']  # 初级判断状态
        macd_data = res['macd_data']  # macd数据包
        kline_data = res['kline_data']  # k线数据包

        isBuySet = []  # 买卖点记录
        close_price = kline_data['close_price']  # 收盘价
        id_tamp = kline_data['id_tamp']  # 时间戳

        if medium_status and self.principal >= close_price:
            #买入 钩子
            self.allBuy(close_price, id_tamp)
            isBuySet.append('1')

        # 止盈止损
        checkSurplusFlag = self._is_checkSurplus(close_price)
        sotpLossFlag = self._is_sotpLoss(close_price)
        if checkSurplusFlag:
            self.allSell(close_price, id_tamp)
            isBuySet.append('0')

        elif sotpLossFlag:
            self.allSell(close_price, id_tamp)
            isBuySet.append('0')

        #把用户与行情数据存入
        _kline_list = kline_data

        # 回测数据--数据打包
        _kline_list.update({
            'check_surplus': self.checkSurplus,
            'stop_loss': self.stopLoss,
            'principal': self.principal,
            'property': self.property,
            'trading_price': self.tradingPrice,
            'buy_traces': self.buyTraces,
            'date': self.timeTamp.get_time_normal(id_tamp)
        })
        # 自定义数据 -- 买卖点 打包
        if len(isBuySet) > 0:
            _kline_list['is_buy_set'] = ','.join(isBuySet)
        else:
            _kline_list['is_buy_set'] = 'wait'
        # 行情数据———macd 打包
        _kline_list.update(macd_data)
        # 自定义数据 -- 研判步骤 打包
        _kline_list['step'] = str(_step)

        # 装车
        self.sqlHandler.insert_trade_marks_data(_kline_list, self.table_name)

    def _is_checkSurplus(self, close_price):
        # 盈亏比
        if self.property != 0:
            odds = ((close_price - self.tradingPrice) / self.tradingPrice)
            if self.leverage != 0:
                odds = odds * self.leverage
            if odds >= 0 and odds >= self.checkSurplus:
                return True
            else:
                return False
        else:
            return False

    def _is_sotpLoss(self, close_price):
        if self.property != 0:
            failure = ((close_price - self.tradingPrice) / self.tradingPrice)
            if self.leverage != 0:
                failure = failure * self.leverage
            if failure <= 0 and abs(failure) >= self.stopLoss:
                return True
            else:
                return False
        else:
            return False

    def allBuy(self, mediumPrice, id_tamp):
        """
        mediumPrice：当前市场货币交易价格
        _trad_coin：本次最大能交易的货币数量
        principal：本人剩余现金
        buyTraces：购买次数

        用本次最大交易量推导出可购买货币数量和花费的现金，再分别对各个变量进行增减。
        """

        # 买前
        principal = self.principal  # 头寸
        # 计算杠杆
        if self.leverage != 0 and self.principal > 0:
            self.le_Amount = self.le_Amount + self.principal * self.leverage - self.principal  # 获取杠杆金额
            principal = principal + self.le_Amount  # 加上杠杆资金
        principal = principal - principal * self.eat_orders_rate  # 买前减去吃单费用
        _trad_coin = principal // mediumPrice  # 算出可买币的数量
        self.property = _trad_coin + self.property  # 现有币个数
        # 买后
        self.principal = principal - (_trad_coin * mediumPrice)  # 买后获得剩余头寸
        self.tradingPrice = mediumPrice  # 交易价格记录
        self.buyTraces = self.buyTraces + 1  # 交易次数记录
        self.buy_time = id_tamp  # 交易时间记录
        # print('买入后剩余本金', self.principal, '交易价格', self.tradingPrice, '购买的比特币',
        #       self.property, '个')

    def allSell(self, mediumPrice, id_tamp):
        #卖前
        principal = self.principal

        # 内部函数 - 获取杠杆费率金额
        def _get_liabilities(le_Amount):
            if le_Amount != 0:
                hold_time = (id_tamp - self.buy_time) / 1000 / 60 / 60  # 持有小时
                return self.interest_rate * le_Amount * hold_time  # 利率 + 负债
            else:
                return 0

        self.tradingPrice = mediumPrice  # 记录交易价格
        # 卖后
        principal = self.property * mediumPrice  # 获得卖后资金
        principal = principal - principal * self.entry_orders_rate  # 减去挂单费用
        principal = principal - _get_liabilities(self.le_Amount)  # 减去杠杆费用
        self.principal = self.principal + principal - self.le_Amount  # 减去杠杆金额
        self.property = 0  # 币数量归零
        self.buyTraces = self.buyTraces + 1  # 交易次数记录
        self.buy_time = None  # 交易时间记录清0
        self.le_Amount = 0  #清除杠杆金额
        # print('卖出后剩余本金', self.principal, '交易价格', self.tradingPrice, '杠杆',
        #       le_Amount)
