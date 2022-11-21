

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
from timeit import default_timer as timer
from decimal import getcontext, Decimal
from empyrical import max_drawdown

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
        self.max_positions_weight = 0.0

    # 获得策略当前胜率
    def count_current_win_times(self):
        return self.win_times/self.game_times if self.game_times != 0 else 0

    # 获得用户当前收益率
    def count_current_upl_ratio(self):
        total = self.count_current_user_net_assets()
        init_fund = self.config['initFund']  # 初始资金
        return (total-init_fund)/init_fund  # 收益率

    # 计算用户当前净总资产
    def count_current_user_net_assets(self):
        equity = self.user.availPos * \
            self.market.close - self.user.liability   # 收益
        return equity + self.user.availBal  # 总资产 = 收益+可用月

    # 计算用户持仓的净资产
    def count_positions_net_assets(self):
        equity = self.user.availPos * \
            self.user.avgPx - self.user.liability   # 权益类资产
        return equity + self.user.availBal  # 总资产

    # 计算用户仓位风险
    def set_positions_weight(self):
        availBal = self.user.availBal
        weight = (self.count_current_user_net_assets()-availBal) / \
            self.count_current_user_net_assets()
        self.max_positions_weight = weight if self.max_positions_weight < weight else self.max_positions_weight

    # 计算用户总工扣息
    def count_account_interest_deduct(self):
        return self.user.interest/self.count_positions_net_assets()

    # 设置胜率
    def set_win_times_info(self):
        self.game_times = self.game_times + 1
        market_asset = self.market.close * self.user.availPos  # 仓位资产现价
        service_charge = market_asset * self.config['eatOrder']  # 手续费
        earnings = market_asset - self.user.liability - service_charge  # 收益
        # 计算用户平均持仓价 和 当前产品价格
        self.win_times = self.win_times + 1 if earnings > 0 else self.win_times

    # 设置资产最高峰和高峰后的低谷
    def set_current_return(self):
        _return = self.count_positions_net_assets() - self.count_current_user_net_assets()
        self.history_returns.append(_return)

    # 计算最大回撤率
    def count_maximum_drawdown_ratio(self):
        return max_drawdown(np.array(self.history_returns))


class AnalysisEngine:
    def __init__(self):
        self.Logger: Logger = logging.getLogger()
        self.columns = ['条目名称', '总收益率', '胜率', '交易次数', '扣息占总资产比率',
                        '用户持仓风险', '止盈率', '止损率']  # '最大回撤率',
        self.cols = {}
        self.data_length_dict = {}

    def handle(self, record: DataRecordEngine):
        try:
            self.on_back_test(record)
            self.save_record(record)
        except Exception as e:
            self.Logger.log(
                level=ERROR, msg='analysis.py 有问题啦'+traceback.format_exc())

    def on_back_test(self, data):
        record: DataRecordEngine = data
        total_name = record.config['table_name']  # 表名称
        win_ratio = record.count_current_win_times()  # 胜率
        game_times = record.game_times  # 游戏次数
        upl_ratio = record.count_current_upl_ratio()  # 收益率
        interest = record.count_account_interest_deduct()  # 总扣息率
        positions_weight = record.max_positions_weight  # 用户持仓风险
        bar = record.config['bar']
        # maximum_drawdown = '%.2f' % record.count_maximum_drawdown_ratio()  # 最大回撤
        if bar not in self.cols:
            self.cols[bar] = []
        self.cols[bar].append([total_name, upl_ratio, win_ratio, game_times, interest, positions_weight,
                               record.config['checkSurplus'], record.config['stopLoss']])

    # 保存行情数据
    def save_record(self, record: DataRecordEngine):
        bar = record.config['bar']
        self.data_length_dict[bar] -= 1
        if self.data_length_dict[bar] == 0:
            self.export_report(
                file_name='simpleMACDStrategy_earnings_report.xlsx', bar=bar)

    # 获得回测数据素材
    def get_test_config(self, bar_config, cs_scope, sl_scope, base_config):
        config_group = []
        # 循环采样粒度维度
        config_group = self._set_bar_list(
            bar_config, base_config)
        # 循环采样止盈率
        config_group = self._get_config_group(
            config_group, cs_scope, 'checkSurplus')
        # 循环采样止损率
        config_group = self._get_config_group(
            config_group, sl_scope, 'stopLoss')

        # 计算各个粒度会被测量的数量总和
        self._set_data_length_dict(bar_config=bar_config,
                                   cs_scope=cs_scope, sl_scope=sl_scope)

        return config_group

    def _set_data_length_dict(self, bar_config, sl_scope, cs_scope):
        def _get_group_length(scope):
            _len = 0
            cursor = scope['min']
            while cursor <= scope['max']:
                _len += 1
                cursor += scope['up']
            return _len

        sl_scope_length = _get_group_length(sl_scope)
        cs_scope_length = _get_group_length(cs_scope)
        for bar in bar_config:
            self.data_length_dict[bar] = sl_scope_length*cs_scope_length

    # 为测试数据素材配置粒度相关信息
    def _set_bar_list(self, scope: list, base_config):
        group = []
        for bar in scope:
            config = {**base_config}
            config['bar'] = bar
            config['table_name'] = 'BTC_USDT_{bar}'.format(bar=bar)
            group.append(config)
        return group

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
            df.to_excel(file_name, sheet_name=sheet_name,
                        encoding='GBK', index=False)
        else:
            with pd.ExcelWriter(file_name, engine='openpyxl', mode='a') as writer:
                df.to_excel(writer, sheet_name=sheet_name,
                            index=False)
                writer.save()

    def export_report(self, file_name, bar):
        self._write_excel(file_name=file_name,
                          cols_data=self.cols[bar], sheet_name=bar)
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
