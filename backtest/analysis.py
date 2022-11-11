

from backtest.constants import AnalysisStructure
from events.event import BACK_TEST, EVENT_ACCOUNT
import matplotlib.pyplot as plt
import logging
from logging import INFO, Logger
from events.engine import EventEngine

add_service_charge = 0.0  # 手续费累计
# 胜率
win_times = 0.0
game_times = 0
add_up = 0.0  # 累计金额
# 赔率
odds = 0.0


class AnalysisEngine:
    def __init__(self, event_engine):
        self.event_engine: EventEngine = event_engine
        self.Logger: Logger = logging.getLogger()
        self.uplRatio = []
        self.event_engine.register(BACK_TEST, self.on_back_test)

    def on_back_test(self, event):
        try:
            data: AnalysisStructure = event.data
            win_ratio = '{ratio}%'.format(ratio='%.2f' % ((
                data.win_times/data.game_times if data.game_times != 0 else 0)*100))
            self.Logger.log(level=INFO, msg='{name}分析完成! 总收益率: {uplRatio}% 胜率:{win_ratio}'.format(
                name=data.config['table_name'], uplRatio='%.2f' % (data.uplRatio*100), win_ratio=win_ratio))
        except Exception as e:
            print('有问题啦', str(e))

    def get_test_config(self, bar_config, cs_scope, sl_scope, base_config):

        config_group = []
        # 循环采样粒度维度
        config_group = self.get_bar_list(config_group, bar_config, base_config)
        # 循环采样止盈率
        config_group = self.get_config_group(
            config_group, cs_scope, 'checkSurplus')
        # 循环采样止损率
        config_group = self.get_config_group(
            config_group, sl_scope, 'stopLoss')

        return config_group

    def get_bar_list(self, config_group: list, scope, base_config):
        config = {**base_config}
        for bar in scope:
            config['bar'] = bar
            config['table_name'] = 'BTC_USDT_{bar}'.format(bar=bar)
            config_group.append(config)

        return config_group
    # 获取格式化的配置组

    def get_config_group(self, config_group, scope, type):
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
