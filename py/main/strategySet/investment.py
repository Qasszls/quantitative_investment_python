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
from util.TimeStamp import TimeTamp
from simpleMACDStrategy import SimpleMacd
from sqlHandler import SqlHandler


class Investment(threading.Thread):
    def __init__(self,
                 checkSurplus,
                 stopLoss,
                 principal,
                 klineMediumLevel,
                 klineAdvancedLevel,
                 medDF,
                 advDF,
                 table_name,
                 mode,
                 odds,
                 _name,
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
        # 数据导入
        self.klineMediumLevel = klineMediumLevel
        self.klineAdvancedLevel = klineAdvancedLevel
        self.medDF = medDF
        self.advDF = advDF
        self.checkSurplus = float(checkSurplus)
        self.stopLoss = float(stopLoss)
        self.principal = int(float(principal))
        self.table_name = table_name
        self.mode = mode
        self.odds = odds
        self.name = _name
        # 命名进程
        if not threadID:
            self.threadID = str(int(self.checkSurplus * 100)) + '_' + str(
                int(self.stopLoss * 100)) + '_' + str(self.principal) + '_'+self.name
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
        simpleMacd = SimpleMacd(self.klineMediumLevel.loc[0]['close_price'],
                                self.medDF.loc[0]['dif'], self.medDF,
                                self.advDF, self.mode, self.odds)
        for index in range(len(self.medDF['macd']) - 1):
            simpleMacd.runStrategy(
                self.klineMediumLevel.loc[index]['close_price'],
                self.klineMediumLevel.loc[index]['id_tamp'],
                index,
                self.onCalculate,
                self.completed,
            )

        self.pbar.set_description(
            emoji.emojize('回测线程' + self.threadID + '已结束。   目前总资产：' + str(
                round((self.property * self.klineMediumLevel.loc[
                    len(self.klineMediumLevel) - 1]['close_price']), 3) +
                self.principal) + '💰' + self.timeTamp.get_time_normal(
                    self.klineMediumLevel.loc[len(self.klineMediumLevel) -
                                              1]['id_tamp']) + '   🖥'))
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
        index = res['index']

        mkline = self.klineMediumLevel
        med_tamp = mkline.loc[index]['id_tamp']
        close_price = mkline.loc[index]['close_price']
        self.pbar.set_description(
            emoji.emojize(
                '回测线程：' + self.threadID + '   目前总资产：' +
                str(round((self.property * close_price) + self.principal, 3)) +
                '💰' + self.timeTamp.get_time_normal(med_tamp) + '   🖥'))
        self.pbar.update(1)

    #钩子函数 计算完成
    def completed(self, res):
        # 买卖点记录
        isBuySet = []
        index = res['index']
        _step = res['step']
        close_price = res['close_price']
        med_tamp = res['tamp']
        mediumStatus = res['mediumStatus']
        advancedStatus = res['advancedStatus']
        medDFLine = self.medDF.loc[:, ('macd', 'dif', 'dea',
                                       'bar')].loc[index].to_dict()

        if mediumStatus and advancedStatus and self.principal >= close_price:
            #买入 钩子
            self.allBuy(close_price)
            isBuySet.append('1')

        # 止盈止损
        checkSurplusFlag = self._is_checkSurplus(close_price, med_tamp)
        sotpLossFlag = self._is_sotpLoss(close_price)
        if checkSurplusFlag:
            self.allSell(self.klineMediumLevel.loc[index][4])
            isBuySet.append('0')

        elif sotpLossFlag:
            self.allSell(self.klineMediumLevel.loc[index][4])
            isBuySet.append('0')

        #把用户与行情数据存入
        _kline_list = self.klineMediumLevel.loc[index].to_dict()

        # 回测数据--数据打包
        _kline_list.update({
            'check_surplus': self.checkSurplus,
            'stop_loss': self.stopLoss,
            'principal': self.principal,
            'property': self.property,
            'trading_price': self.tradingPrice,
            'buy_traces': self.buyTraces,
            'date': self.timeTamp.get_time_normal(med_tamp)
        })
        # 自定义数据 -- 买卖点 打包
        if len(isBuySet) > 0:
            _kline_list['is_buy_set'] = ','.join(isBuySet)
        else:
            _kline_list['is_buy_set'] = 'wait'
        # 行情数据———macd 打包
        _kline_list.update(medDFLine)
        # 自定义数据 -- 研判步骤 打包
        _kline_list['step'] = str(_step)

        # 装车
        self.sqlHandler.insert_trade_marks_data(_kline_list, self.table_name)

    def _is_checkSurplus(self, close_price, tamp):
        # 盈亏比
        if self.property != 0:
            odds = ((close_price - self.tradingPrice) / self.tradingPrice)
            if odds >= 0 and odds >= self.checkSurplus:
                return True
            else:
                return False
        else:
            return False

    def _is_sotpLoss(self, close_price):
        if self.property != 0:
            failure = ((close_price - self.tradingPrice) / self.tradingPrice)
            if failure <= 0 and abs(failure) >= self.stopLoss:
                return True
            else:
                return False
        else:
            return False

    def allBuy(self, mediumPrice):
        """
        mediumPrice：当前市场货币交易价格
        _trad_coin：本次最大能交易的货币数量
        principal：本人剩余现金
        buyTraces：购买次数

        用本次最大交易量推导出可购买货币数量和花费的现金，再分别对各个变量进行增减。
        """
        _trad_coin = self.principal // mediumPrice
        self.tradingPrice = mediumPrice
        self.property = _trad_coin + self.property
        self.principal = self.principal - (_trad_coin * mediumPrice)
        self.buyTraces = self.buyTraces + 1
        # print('买入后剩余本金', self.principal, '交易价格', self.tradingPrice, '购买的比特币',
        #       self.property, '个')

    def allSell(self, mediumPrice):
        self.tradingPrice = mediumPrice
        self.principal = self.property * mediumPrice + self.principal
        self.property = 0
        self.buyTraces = self.buyTraces + 1
        # print('卖出后剩余本金', self.principal, '交易价格', self.tradingPrice)
