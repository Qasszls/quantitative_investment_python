# -*- coding:UTF-8 -*-

import talib
import pandas as pd
import numpy as np
import time
import sys
# import pyecharts.options as opts
# from pyecharts.charts import Line

sys.path.append("..")
from util.TimeStamp import TimeTamp
from simpleMACDStrategy import SimpleMacd
from draw import DrawMacd


class Main:
    def __init__(self, checkSurplus, stopLoss, principal):
        """
        初始化
            止盈率
            止损率
            本金
            资产(个)
            交易价格
            购币痕迹
        """
        self.checkSurplus = checkSurplus
        self.stopLoss = stopLoss
        self.principal = principal
        #内部变量
        self.property = 0
        self.tradingPrice = 0
        self.buyTraces = 0
        self.timeTamp = TimeTamp()

    def runBackTest(self, klineMediumLevel, klineAdvancedLevel, medDF, advDF):
        # 实例化核心算法对象----本级别
        simpleMacd = SimpleMacd(klineMediumLevel.loc[0]['close_price'],
                                medDF.loc[0]['dif'])
        simpleMacd.run(klineMediumLevel, klineAdvancedLevel, medDF, advDF,
                       self.onCalculate, self.completed)
        # 钩子
        print(
            '剩余本金：', self.principal, '元。剩余币：', self.property, '元。剩余价值：',
            self.principal +
            (self.property *
             klineMediumLevel.loc[len(klineMediumLevel) - 1]['close_price']))

    #钩子函数 计算中
    def onCalculate(self, res):
        None

    #钩子函数 计算完成
    def completed(self, res):
        index = res['index']
        klineMediumLevel = res['klineMediumLevel']
        close_price = klineMediumLevel.loc[index]['close_price']
        med_tamp = klineMediumLevel.loc[index]['id_tamp']
        advancedStatus = res['advancedStatus']
        if advancedStatus:
            #买入 钩子
            if self.principal >= close_price:
                self.allBuy(close_price)
        # 止盈止损
        if self._is_checkSurplus(close_price, med_tamp):
            self.allSell(klineMediumLevel.loc[index][4])
        elif self._is_sotpLoss(close_price):
            self.allSell(klineMediumLevel.loc[index][4])
        #把用户与行情数据存入

    def _is_checkSurplus(self, close_price, tamp):
        # 盈亏比
        if self.property != 0:
            odds = ((close_price - self.tradingPrice) / self.tradingPrice)
            print(self.timeTamp.get_time_normal(tamp), '止盈率',
                  format(self.checkSurplus * 100, '.2f') + '%', '止损率',
                  format(self.stopLoss * 100, '.2f') + '%',
                  '赔率' + format(odds * 100, '.5f') + '%', '总资产：',
                  self.principal + self.property * close_price)
            # time.sleep(0.31)
            if odds >= 0 and odds >= self.checkSurplus:
                return odds >= self.checkSurplus
            else:
                return False
        else:
            # 观察钩子
            if self.buyTraces > 0:
                odds = ((close_price - self.tradingPrice) / self.tradingPrice)
                print(self.timeTamp.get_time_normal(tamp), '比特币价格',
                      close_price, '上次交易价格', self.tradingPrice, '拿住后赔率',
                      format(odds * 100, '.5f') + '%', '总资产：', self.principal)
                # time.sleep(0.11)
            return False

    def _is_sotpLoss(self, close_price):
        if self.property != 0:
            failure = ((close_price - self.tradingPrice) / self.tradingPrice)
            if failure <= 0 and failure <= self.stopLoss:
                return abs(failure) >= self.stopLoss
            else:
                return False
        else:
            return False

    def get_kline_fromCsv(self, path):
        return pd.read_csv(path)

    def allBuy(self, mediumPrice):
        self.tradingPrice = mediumPrice
        self.property = self.principal // mediumPrice + self.property
        self.principal = self.principal - (self.property * mediumPrice)
        self.buyTraces = self.buyTraces + 1
        print('买入后剩余本金', self.principal, '交易价格', self.tradingPrice, '购买的比特币',
              self.property)

    def allSell(self, mediumPrice):
        self.tradingPrice = mediumPrice
        self.principal = self.property * mediumPrice + self.principal
        self.property = 0
        print('卖出后剩余本金', self.principal, '交易价格', self.tradingPrice)

    def get_MACD(self,
                 price,
                 timeTamps,
                 fastperiod=12,
                 slowperiod=26,
                 signalperiod=9):
        """
        入参：价格和基准等
        出参：dataFrame格式的数据结构
        """
        ewma12 = price.ewm(span=fastperiod).mean()
        ewma60 = price.ewm(span=slowperiod).mean()
        dif = ewma12 - ewma60
        dea = dif.ewm(span=signalperiod).mean()
        bar = (dif - dea
               )  #有些地方的bar = (dif-dea)*2，但是talib中MACD的计算是bar = (dif-dea)*1
        macd = dif - dea
        return pd.DataFrame({
            'macd': macd,
            'dif': dif,
            'dea': dea,
            'bar': bar,
            'id_tamp': timeTamps.values
        })


if __name__ == "__main__":
    kline_15m_SamplePath = '../../kline_csv/2020_kline_15m.csv'  # 样本地址1
    kline_1H_SamplePath = '../../kline_csv/2020_kline_1H.csv'  # 样本地址2
    main = Main(0.18, 0.08, 1000000)
    #读取dataFrame变量
    klineMediumLevel = main.get_kline_fromCsv(kline_15m_SamplePath)
    klineAdvancedLevel = main.get_kline_fromCsv(kline_1H_SamplePath)
    medDF = main.get_MACD(klineMediumLevel['close_price'],
                          klineMediumLevel['id_tamp'])
    advDF = main.get_MACD(klineAdvancedLevel['close_price'],
                          klineAdvancedLevel['id_tamp'])

    # main.runBackTest(klineMediumLevel, klineAdvancedLevel, medDF, advDF)

    # python 画图 已废弃
    # drawMacd = DrawMacd(medDF.loc[0:10])
    # drawMacd.run(medDF)
