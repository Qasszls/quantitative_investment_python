# , '30m', '15m', '1D', '4H', '2H'
BAR_CONFIG = ['1H']

CHECK_SURPLUS_SCOPE = {'min': 0.2, 'max': 0.2, 'up': 0.05}  # 最小止盈，最大止盈，止盈变化粒度
STOP_LOSS_SCOPE = {'min': 0.22, 'max': 0.22, 'up': 0.05}  # 最小止损，最大止损，止损变化粒度
# CHECK_SURPLUS_SCOPE = {'min': 0.35, 'max': 4.5, 'up': 0.05}  # 最小止盈，最大止盈，止盈变化粒度
# STOP_LOSS_SCOPE = {'min': 0.22, 'max': 1.12, 'up': 0.1}  # 最小止损，最大止损，止损变化粒度

VAR_CONFIG = {
    "slippage": 0.0001,  # 滑点
    "rateInHour": 0.000003,  # 杠杆利率
    "entryOrders": 0.0008,  # 挂单手续费
    "eatOrder": 0.001,  # 吃单手续费
    "lever": 10,
    "name": '柳尚佐',
}

BASE_CONFIG = {
    "initFund": 5000000.0,  # 初始资金
    "initCoin": 0.0,  # 初始币数量
    "avgPx": 0.0,  # 开仓均价
    "liability": 0.0,  # 负债
    "instId": "BTC-USDT",
    "start_timestamp": "2016-10-1 00:00:00",
    # "start_timestamp": "2021-9-1 00:00:00",
    "end_timestamp": "2022-11-6 00:00:00",
    "checkSurplus": 0.322,  # 默认止盈
    "stopLoss": 0.169,  # 默认止损

    # "bar": "1H",  # 粒度
    # "table_name": "BTC_USDT_1H",
    # "start_timestamp": "2019-10-1 20:00:00",
    # "end_timestamp": "2022-11-6 00:00:00",
    # "bar": "30m",  # 粒度
    # "table_name": "BTC_USDT_30m",
    # "start_timestamp": "2019-10-4 00:00:00",
    # "end_timestamp": "2022-11-6 00:00:00",
    # "bar": "15m",  # 粒度
    # "table_name": "BTC_USDT_15m",
    # "start_timestamp": "2020-8-30 00:00:00",
    # "end_timestamp": "2022-11-6 00:00:00",
}


class ConfigEngine:

    def get_config(self, type=None):
        config = {**VAR_CONFIG, **BASE_CONFIG}
        if type:
            return config[type]
        else:
            return config
