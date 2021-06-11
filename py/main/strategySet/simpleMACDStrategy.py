# -*- coding:UTF-8 -*-
"""
策略结构

回测容器（调用策略代码）

    本代码位置：策略代码(输入：k线；输出：买点，卖点，总金额，总仓位等)

    可视化（金额与走势图绘制在html上）

MACD原理

数据参照：短期EMA（一般12），长期EMA（一般26），DIF（EMA(12) - EMA(26)），DEA（前一日 DEA * 8/10 + 今日 DIF * 2/10）
    MACD：DIF与DEA的差值。红绿柱是 DIF 与 DEA 的差值 * 2.

指标：
    零轴: DIF == 0 and DEA == 0
    零上: DIF > 0 and DEA > 0
    零下: DIF < 0 and DEA < 0
    金叉: MACD > 0 and MACD 昨日 <= 0
    死叉: MACD < 0 and MACD 昨日 >= 0
    价格不断创新低: 
        价格低点: k线收盘价现最小值
        价格前低: k线收盘价前最小值
    macd快慢线 低点提高:
        快慢线前低: DIF前最小值
        快慢线现低: DIF现最小值
    回抽零轴-快慢线低点上移后金叉确认:
        快慢线低点上移（依赖金叉确认）:DIF现最小值 > DIF前最小值
        金叉确认(如果不是零下的金叉确认，就不是我们做的点位): MACD > 0 and MACD 昨日 <= 0
        零下: DIF < 0 and DEA < 0

        执行队列
		step0				step 1			step 2		  step3               step4
		零下死叉============>是金叉=====>是死叉 and 水下====>是金叉====>白线低点是否上移 and 收盘价是否比前低更低
        
        
        因为在零下的快慢线低点上移后，自然就完成回抽零轴的动作，故策略与公式的转换完成。

代码实现
for item in kline:
    # 是否满足条件 买
    status(条件是否满足),price(当前价格),kline(当日K线) = underwater_collide(item)

    # 止损 小于当前价格 10%

    # 止盈 大于当前价格 22%
    
"""
import sys
import talib
import pandas as pd

import time

talib.OBV


class SimpleMacd():
    def __init__(self, close_price, lowest_dif):
        self.lowest_price = close_price
        self.lowest_dif = lowest_dif
        self.step = 0

    def run(self, klineMediumLevel, klineAdvancedLevel, medDF, advDF,
            onCalculate, completed):
        for index in range(len(medDF['macd'] - 1)):
            # 初始化变量
            close_price = klineMediumLevel.loc[index]['close_price']  # 获取当日收盘价
            med_tamp = klineMediumLevel.loc[index]['id_tamp']  # 获取本级别的时间戳
            medDF_line = medDF.loc[index]  # 获取本级别的当日macd
            adv_tamp = advDF['id_tamp']  # 获取高级别的时间戳
            # 计算中 钩子
            onCalculate({'index': index})

            # 核心算法，是否做多，本级别确认
            mediumStatus = self.medium_read(close_price, medDF_line)

            if mediumStatus:
                # print('本级别确认')
                # 实例化核心算法对象----高级别
                advMacdIndex = self._get_syn_timestamp(adv_tamp, med_tamp)
                advancedStatus = self.advance_read(advDF.loc[advMacdIndex])
                completed({
                    'mediumStatus': mediumStatus,
                    'advancedStatus': advancedStatus,
                    'klineMediumLevel': klineMediumLevel,
                    'klineAdvancedLevel': klineAdvancedLevel,
                    'medDF': medDF,
                    'advDF': advDF,
                    'index': index
                })
            else:
                # 流程跑完 钩子
                completed({
                    'mediumStatus': mediumStatus,
                    'advancedStatus': None,
                    'klineMediumLevel': klineMediumLevel,
                    'klineAdvancedLevel': klineAdvancedLevel,
                    'medDF': medDF,
                    'advDF': advDF,
                    'index': index
                })

    # 获得同一时间的时间戳 时间戳同步
    def _get_syn_timestamp(self, advTamp, medTamp):
        advTampList = advTamp.values
        for index in range(len(advTampList)):
            diff = int(medTamp) - int(advTampList[index])

            if (diff > 0 and diff <= 3600000) or (diff >= 0
                                                  and diff < 3600000):
                return index

    # 高级别研判
    def advance_read(self, todayMacd):
        # 在水上做多
        if self._is_under_water(todayMacd['dif'], todayMacd['dea']):
            return False
        # 在水下的再研判 没有做
        else:
            return True

    # 本级别研判
    def medium_read(self, close_price, todayMacd):

        #初始化模块
        dif = todayMacd['dif']

        # 研判模块
        if self.step == 0:
            self._step_0(todayMacd)
        elif self.step == 1:
            self._step_1(todayMacd)
        elif self.step == 2:
            self._step_2(todayMacd)
        elif self.step == 3:
            self._step_3(todayMacd)
        elif self.step == 4:
            self._step_4(todayMacd, close_price)
        elif self.step == 5:
            return True

        # 记录模块 价格 与 dif 低点
        if dif < self.lowest_dif:
            self.lowest_dif = dif
        if close_price < self.lowest_price:
            self.lowest_price = close_price

    # 工具函数

    # 是否在水下
    def _is_under_water(self, dif, dea):
        return dif < 0 and dea < 0

    # 在水下 是否金叉
    def _is_golden_cross(self, macd):
        return macd > 0

    # 白线是否上移
    def _is_white_line_up(self, dif, lowest_dif):
        return dif > lowest_dif

    # 收盘价是否低中低
    def _is_down_channel(self, lowest_price, close_price):
        return lowest_price >= close_price

    # 步骤 0 水下生死叉
    def _step_0(self, macdDist):
        if self._is_under_water(macdDist['dif'], macdDist['dea']):
            if self._is_golden_cross(macdDist['macd']):
                self.step = 2
            else:
                self.step = 1
        else:
            self.step = 0

    # 步骤 1 死后返生叉
    def _step_1(self, macdDist):
        if self._is_golden_cross(macdDist['macd']):
            self.step = 2
        else:
            self.step = 1

    # 步骤 2 回抽零轴 或 出水重生
    def _step_2(self, macdDist):
        if self._is_under_water(macdDist['dif'], macdDist['dea']):
            if not self._is_golden_cross(macdDist['macd']):
                self.step = 3
            else:
                self.step = 2
        else:
            self.step = 0

    # 步骤 3 金叉确认 蓄势登场
    def _step_3(self, macdDist):
        if self._is_golden_cross(macdDist['macd']):
            self.step = 4
        else:
            self.step = 3

    # 步骤 4 形危而势强
    def _step_4(self, tMDist, close_price):
        if self._is_white_line_up(tMDist['dif'],
                                  self.lowest_dif) and self._is_down_channel(
                                      close_price, self.lowest_price):
            self.step = 5
        else:
            self.step = 2
