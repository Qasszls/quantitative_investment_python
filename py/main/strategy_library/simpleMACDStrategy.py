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
from os import close
import sys
import talib
import pandas as pd
import emoji

import time

talib.OBV

sys.path.append('..')
from util.TimeStamp import TimeTamp


class SimpleMacd():
    def __init__(self, mode, odds):
        self.lowest_price = {
            'first_confirmation': None,
            'again_confirmation': None
        }
        self.lowest_dif = {
            'first_confirmation': None,
            'again_confirmation': None
        }
        self.step = 0
        self.mode = mode
        self.odds = odds
        self.timeTamp = TimeTamp()

    def runStrategy(self, kline_data, medDF_line, onCalculate, completed):
        med_tamp = kline_data['id_tamp']
        close_price = kline_data['close_price']
        # 计算中 钩子
        onCalculate({
            'close_price': close_price,
            'id_tamp': med_tamp,
        })

        # 核心算法，是否做多，本级别确认
        medium_status = self.medium_read(close_price, medDF_line, med_tamp)
        # 实例化核心算法对象----高级别
        completed({
            'medium_status': medium_status,
            'kline_data': kline_data,
            'medDF_line': medDF_line,
            "step": self.step
        })

    # 获得同一时间的时间戳 时间戳同步
    # def _get_syn_timestamp(self, advTampList, medTamp):
    #     index = 0
    #     for item in advTampList:
    #         diff = int(medTamp) - int(item)
    #         # 兼容时间差为：
    #         # if diff >= 0 and diff <= 86400000:
    #         #     return index
    #         if diff >= 0 and diff <= 3600000:
    #             return index
    #         index = index + 1

    # # 高级别研判
    # def advance_read(self, todayMacd):
    #     # 在水上做多
    #     if self._is_under_water(todayMacd['dif'], todayMacd['dea']):
    #         return False
    #     # 在水下的再研判 没有做
    #     else:
    #         return True

    # 本级别研判
    def medium_read(self, close_price, todayMacd, med_tamp):
        dif = todayMacd['dif']
        # 研判模块
        if self.step == 0:
            self._reset()
            self._step_0(todayMacd)
            return False
        elif self.step == 1:
            # 首次水下死叉的波谷的线价记录
            self.price_lowest_record(close_price, 'first_confirmation')
            self.dif_lowest_record(dif, 'first_confirmation')
            self._step_1(todayMacd)
            return False
        elif self.step == 2:
            # 回抽零轴前研判
            self._step_2(todayMacd)
            return False
        elif self.step == 3:
            # 记录本次回抽后波谷的价线情况
            self.price_lowest_record(close_price, 'again_confirmation')
            self.dif_lowest_record(dif, 'again_confirmation')
            # 走研判内容
            self._step_3(todayMacd)
            if self.step == 2:
                # print('dif', self.lowest_dif, 'price', self.lowest_price,
                #       'date', self.timeTamp.get_time_normal(med_tamp))

                # 回抽零轴后波谷可能 深于【首次死叉】时的波谷，故尝试记录一下
                self.price_lowest_record(
                    self.lowest_price['again_confirmation'],
                    'first_confirmation')
                self.dif_lowest_record(self.lowest_dif['again_confirmation'],
                                       'first_confirmation')

                # 清空过往回抽后波谷的价线记录
                self._reset('again_confirmation')
                return False
            elif self.step == 9999:
                # print('dif', self.lowest_dif, 'price', self.lowest_price,
                #       'date', self.timeTamp.get_time_normal(med_tamp))
                return True
        elif self.step == 9999:
            self._reset()
            self._step_0(todayMacd)
            return False

    # 工具函数

    # 是否在水下
    def _is_under_water(self, dif, dea):
        return dif < 0 or dea < 0

    # 在水下 是否金叉
    def _is_golden_cross(self, macd):
        return macd > 0

    #非严格模式的 白线收盘价是否背离
    def _loose_deviate_from(self):
        odds = self.odds

        # 内部函数
        def _get_odds(mode='dif'):
            if mode == 'dif':
                first = self.lowest_dif['first_confirmation']
                again = self.lowest_dif['again_confirmation']
                return abs((first - again) / again) <= odds
            else:
                first = self.lowest_price['first_confirmation']
                again = self.lowest_price['again_confirmation']
                return abs((again - first) / first) <= odds

        if self._is_white_line_up() and self._is_down_channel():
            return True
        elif self._is_white_line_up() and _get_odds('price'):
            return True
        elif self._is_down_channel() and _get_odds('dif'):
            return True
        else:
            return False

        # 白线波谷上移 或 收盘价创新低

    # 白线是否上移
    def _is_white_line_up(self):
        return self.lowest_dif['again_confirmation'] > self.lowest_dif[
            'first_confirmation']

    # 收盘价是否低中低
    def _is_down_channel(self):
        return self.lowest_price['again_confirmation'] < self.lowest_price[
            'first_confirmation']

    def _reset(self, target='all'):
        if target == 'all':
            self.lowest_price['first_confirmation'] = None
            self.lowest_price['again_confirmation'] = None
            self.lowest_dif['first_confirmation'] = None
            self.lowest_dif['again_confirmation'] = None
        else:
            self.lowest_price[target] = None
            self.lowest_dif[target] = None

    # 步骤 0 水下生死叉
    def _step_0(self, macdDist):
        """ 死叉 ==>
        等待进入空头市场
            等待空头市场的死叉状态 next
        """
        if self._is_under_water(macdDist['dif'], macdDist['dea']):
            if not self._is_golden_cross(macdDist['macd']):
                self.step = 1
            else:
                self.step = 0
        else:
            self.step = 0

    # 步骤 1 死后返生叉
    def _step_1(self, macdDist):
        """ 死叉 ==> 金叉
        是否在空头市场
            等待它的金叉状态 next
        """
        if self._is_under_water(macdDist['dif'], macdDist['dea']):
            if self._is_golden_cross(macdDist['macd']):
                self.step = 2
            else:
                self.step = 1
        else:
            self.step = 0

    # 步骤 2 回抽零轴 或 出水重生
    def _step_2(self, macdDist):
        """ 死叉 ==> 金叉 ==> 死叉
        是否仍在空头市场
            等待它的死叉状态 next
        """
        if self._is_under_water(macdDist['dif'], macdDist['dea']):
            if not self._is_golden_cross(macdDist['macd']):
                self.step = 3
            else:
                self.step = 2
        else:
            self.step = 0

    # 步骤 3 金叉确认 蓄势登场
    def _step_3(self, macdDist):
        """ 死叉 ==> 金叉 ==> 死叉 ==> 金叉 与 背离
        是否仍在空头市场
            等待它的金叉状态 next
        """

        if self._is_under_water(macdDist['dif'], macdDist['dea']):
            if self._is_golden_cross(macdDist['macd']):
                if self._is_white_line_up() and self._is_down_channel():
                    self.step = 9999
                elif self.mode == 'strict' and self._loose_deviate_from():
                    self.step = 9999
                else:
                    self.step = 2
            else:
                self.step = 3
        else:
            self.step = 0

    #背离记录模块 价格与dif
    def price_lowest_record(self, close_price, time_quantum):
        if self.lowest_price[time_quantum] == None:
            self.lowest_price[time_quantum] = close_price
        else:
            if close_price < self.lowest_price[time_quantum]:
                self.lowest_price[time_quantum] = close_price

    def dif_lowest_record(self, dif, time_quantum):
        if self.lowest_dif[time_quantum] == None:
            self.lowest_dif[time_quantum] = dif
        else:
            if dif < self.lowest_dif[time_quantum]:
                self.lowest_dif[time_quantum] = dif