# -*- coding:UTF-8 -*-
"""
一个完整的策略类包含
1.策略运行函数 runStarategy
2.止盈止损函数 isSell
"""
import sys
import pandas as pd
import emoji

import time

# talib.OBV

sys.path.append('..')
from util.TimeStamp import TimeTamp


class Strategy:
    def __init__(self, check_surplus, stop_loss):
        self.check_surplus = check_surplus
        self.stop_loss = stop_loss

    def runStrategy(self, data, completed):
        completed()

    # 止损函数
    def is_need_sell(self, uplRatio):
        """
        uplRatio 收益率
        checkSurplus 止盈率
        stoploss 止损率
        """
        if not isinstance(uplRatio, float):
            uplRatio = float(uplRatio)

        def _is_checkSurplus():
            return uplRatio >= self.check_surplus

        def _is_sotpLoss():
            if uplRatio <= 0:
                return abs(uplRatio) >= self.stop_loss

        return _is_checkSurplus() or _is_sotpLoss()


class SimpleMacd(Strategy):
    def __init__(self, mode, odds, check_surplus, stop_loss, user_info):
        Strategy.__init__(self, check_surplus, stop_loss)
        self.lowest_price = {
            'first_confirmation': None,
            'again_confirmation': None
        }
        self.lowest_dif = {
            'first_confirmation': None,
            'again_confirmation': None
        }

        self.step = 0
        self.ema12 = float(user_info['ema12'])
        self.ema26 = float(user_info['ema26'])
        self.ema240 = float(user_info['ema240'])

        self.has_strong_history = False  # 是否有强势的历史
        self.is_strong_gains = False  # 当前是否强势
        self.dea = float(user_info['dea'])
        self.old_kl = []

        self.mode = mode
        self.odds = odds
        self.timeTamp = TimeTamp()

    # 策略运行函数
    def runStrategy(self, data,  completed):
        # 第一次进入循环 或者 同一时间的老数据，都会进入
        if len(self.old_kl) == 0 or data[0] in self.old_kl:
            # 其实可以完全不写下面的代码，但是意义就不一样了。
            self.old_kl = data
            return
        self.old_kl = data
        # k线数据
        KLINE_DATA = self.set_kline_dict(data)
        # 取出变量
        med_tamp = KLINE_DATA['id_tamp']
        close_price = KLINE_DATA['close_price']
        # 指标数据
        INDICATORS_DATA = self._befor_investment(KLINE_DATA)
        # 记录涨幅是否强势
        self.monitoring_status(INDICATORS_DATA, KLINE_DATA)

        # 核心算法，是否做多，本级别确认
        medium_status = self.medium_read(close_price, INDICATORS_DATA,
                                         med_tamp)
        completed({
            'medium_status': medium_status,
            'kline_data': KLINE_DATA,
            'indicators': INDICATORS_DATA,
            "step": self.step,
            "other": {' has_strong_history':self.has_strong_history}
        })

    # 止盈止损函数
    def runOddsMonitoring(self, uplRatio):
        """
        is_need_sell 是否达成了止盈止损条件 boolean
        is_Strong 当前股价是否强势 boolean
        """

        is_need_sell = self.is_need_sell(uplRatio)
        # 此时股价已经运行在ema240之上
        if self.is_strong_gains:
            self.has_strong_history = True
            return False
        else:
            print('当前股价是否强势过:',self.has_strong_history)
            # 是否有过强势历史
            if self.has_strong_history:
                # 有过，说明目前涨势变成不强势
                return True
            else:
                return is_need_sell

    # 重置强势历史
    def reset_has_strong_history(self):
        self.has_strong_history = False

    # 计算策略运行的数据
    def _befor_investment(self, kline_data):
        # 私有函数
        # 计算macd值
        price = kline_data['close_price']

        # 获取往日 数据
        last_ema12 = self.ema12
        last_ema26 = self.ema26
        last_ema240 = self.ema240
        last_dea = self.dea
        # 计算当日 数据

        EMA12 = last_ema12 * 11 / 13 + price * 2 / 13
        EMA26 = last_ema26 * 25 / 27 + price * 2 / 27
        EMA240 = last_ema240 * 119 / 121 + price * 2 / 121
        DIF = EMA12 - EMA26
        DEA = last_dea * 8 / 10 + DIF * 2 / 10
        MACD = DIF - DEA
        # 计算macd
        # 赋值当日macd变量

        return {
            'ema12': EMA12,
            'ema26': EMA26,
            'ema240': EMA240,
            'dif': DIF,
            'dea': DEA,
            'macd': MACD,
            "bar": MACD * 2
        }

    # 股价动态监测与记录
    def monitoring_status(self, idata, kdata):
        self.ema12 = idata['ema12']
        self.ema26 = idata['ema26']
        self.ema240 = idata['ema240']
        self.dea = idata['dea']
        # 涨势是否强势
        self.is_strong_gains = float(kdata['close_price']) > idata['ema240']

    # k线数据 dict化
    def set_kline_dict(self, kline_data):
        _k = pd.DataFrame([kline_data]).astype(float)
        _k.columns = [
            'id_tamp', 'open_price', 'high_price', 'lowest_price',
            'close_price', 'vol', 'volCcy'
        ]
        return _k.to_dict('records')[0]

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

    # 策略工具函数
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
                elif self.mode != 'strict' and self._loose_deviate_from():
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