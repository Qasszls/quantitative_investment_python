

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

    def start(self):
        self.event_engine.register(BACK_TEST, self.on_back_test)

    def on_back_test(self, event):
        try:
            data: AnalysisStructure = event.data
            win_ratio = '{ratio}%'.format(ratio='%.2f' % ((
                data.win_times/data.game_times if data.game_times != 0 else 0)*100))
            self.Logger.log(level=INFO, msg='{name}分析完成!\n总收益率: {uplRatio}%\n胜率:{win_ratio}'.format(
                name=data.config['table_name'], uplRatio='%.2f' % (data.uplRatio*100), win_ratio=win_ratio))
        except Exception as e:
            print('有问题啦', str(e))

    def stacked_area_plot(self):
        # Create data
        x = range(1, 6)
        y1 = [1, 4, 6, 8, 9]
        y2 = [2, 2, 7, 10, 12]
        y3 = [2, 8, 5, 10, 6]

        # Basic stacked area chart.
        plt.stackplot(x, y1, y2, y3, labels=['A', 'B', 'C'])
        plt.legend(loc='upper left')
