

from backtest.constants import Market
from events.event import BACK_TEST, EVENT_ACCOUNT
import matplotlib.pyplot as plt
import time
import numpy as np
import logging
from logging import INFO, Logger, ERROR
import pandas as pd
import traceback
import os
from decimal import getcontext, Decimal
from empyrical import max_drawdown
from share.utils import ProgressBar, get_time_stamp

# 设置最大小数位长度
getcontext().prec = 4


class DataRecordEngine:
    def __init__(self, user, market, config):
        self.config = config
        self.fund = config['initFund']
        self.win_times = 0
        self.game_times = 0
        self.maximum_fund = self.fund  # 资产最大值
        self.minimum_fund = self.fund  # 资产最小值
        self.maximum_drawdown = 0.0  # 最大回撤
        self.user = user
        self.market: Market = market
        self.history_returns = []

    # 获得策略当前胜率
    def count_current_win_times(self):
        return self.win_times/self.game_times if self.game_times != 0 else 0

    # 获得用户当前收益率
    def count_current_upl_ratio(self):
        total = self.count_current_user_total_fund().__float__()
        init_fund = self.config['initFund']  # 初始资金
        return (total-init_fund)/init_fund  # 收益率

    # 计算用户当前总资产
    def count_current_user_total_fund(self):
        equity = self.user.availPos * \
            self.market.close - self.user.liability + \
            self.user.margin_lever  # 权益类资产
        return equity + self.user.availBal  # 总资产

    # 计算用户持仓时总资产
    def count_positions_total_fund(self):
        equity = self.user.availPos * \
            self.user.avgPx - self.user.liability + \
            self.user.margin_lever  # 权益类资产
        return equity + self.user.availBal  # 总资产

    # 设置胜率
    def set_win_times_info(self):
        self.game_times = self.game_times + 1
        # 用户平均持仓价
        sell_price = self.user.avgPx * \
            (1 - self.config['slippage']) * (1 - self.config['eatOrder'])
        # 计算用户平均持仓价 和 当前产品价格
        self.win_times = self.win_times + \
            1 if (sell_price - self.market.close) > 0 else self.win_times

    # 设置资产最高峰和高峰后的低谷
    def set_current_return(self):
        _return = self.count_positions_total_fund() - self.count_current_user_total_fund()
        self.history_returns.append(_return.__float__())
        # 计算最大回撤率

    def count_maximum_drawdown_ratio(self):
        return max_drawdown(np.array(self.history_returns))


class AnalysisEngine:
    def __init__(self, right_pipe=None):
        self.Logger: Logger = logging.getLogger()
        self.right_pipe = right_pipe
        self.columns = ['条目名称', '总收益率', '胜率', '止盈率', '止损率']  # '最大回撤率',
        self.cols = {

        }
        self.index = 0
        self.progress: ProgressBar = ProgressBar()

    def start(self, length):
        self.progress.create_bar(total=length)
        self.index = length
        while True:
            res = self.right_pipe.recv()
            if res:
                self.progress.update(1)
                self.index -= 1
                self.on_back_test(res)
                if self.index == 0:
                    break

    def on_back_test(self, data):
        try:
            record: DataRecordEngine = data
            total_name = record.config['table_name']  # 表名称
            win_ratio = record.count_current_win_times()  # 胜率
            upl_ratio = record.count_current_upl_ratio()  # 收益率
            bar = record.config['bar']
            # maximum_drawdown = '%.2f' % record.count_maximum_drawdown_ratio()  # 最大回撤
            if bar not in self.cols:
                self.cols[bar] = []
            self.cols[bar].append([total_name, upl_ratio, win_ratio,
                                   record.config['checkSurplus'], record.config['stopLoss']])

        except Exception as e:
            self.Logger.log(
                level=ERROR, msg='analysis.py 有问题啦'+traceback.format_exc())

    def get_test_config(self, bar_config, cs_scope, sl_scope, base_config):

        config_group = []
        # 循环采样粒度维度
        config_group = self._get_bar_list(
            config_group, bar_config, base_config)
        # 循环采样止盈率
        config_group = self._get_config_group(
            config_group, cs_scope, 'checkSurplus')
        # 循环采样止损率
        config_group = self._get_config_group(
            config_group, sl_scope, 'stopLoss')

        return config_group

    def _get_bar_list(self, config_group: list, scope: list, base_config):
        for bar in scope:
            config = {**base_config}
            config['bar'] = bar
            config['table_name'] = 'BTC_USDT_{bar}'.format(bar=bar)
            config_group.append(config)

        return config_group
    # 获取格式化的配置组

    def _get_config_group(self, config_group, scope, type):
        new_group = []
        cursor = scope['min']
        for config in config_group:
            while cursor <= scope['max']:
                _c = {**config}
                _c[type] = cursor
                new_group.append(_c)
                cursor = cursor + scope['up']
            cursor = scope['min']
        return new_group

    def _read_from_excel(self, file_name="", dtype: dict = {}):
        data = pd.read_excel(file_name, dtype=dtype)
        return data

    def _write_excel(self, file_name, cols_data,  sheet_name='test.xlsx', columns=None):
        df = pd.DataFrame(
            data=cols_data, columns=columns if columns else self.columns)
        
        if not os.path.exists(file_name):
            df.to_excel(file_name, encoding='GBK', index=False)
        else:
            with pd.ExcelWriter(file_name, engine='openpyxl', mode='a') as writer:
                df.to_excel(writer, sheet_name=sheet_name,
                            index=False)
                writer.save()

    def export_report(self, file_name):
        for key in self.cols.keys():
            self._write_excel(file_name=file_name,
                              cols_data=self.cols[key], sheet_name=key)
         # 画图
        # def stacked_area_plot(self):
        #     # Create data
        #     x = range(1, 6)
        #     y1 = [1, 4, 6, 8, 9]
        #     y2 = [2, 2, 7, 10, 12]
        #     y3 = [2, 8, 5, 10, 6]

        #     # Basic stacked area chart.
        #     plt.stackplot(x, y1, y2, y3, labels=['A', 'B', 'C'])
        #     plt.legend(loc='upper left')
