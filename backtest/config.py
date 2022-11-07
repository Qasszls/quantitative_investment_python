CONFIG = {
    "initFund": 5000000.0,  # 初始资金
    "initCoin": 0.0,  # 初始币数量
    "avgPx": 0.0,  # 开仓均价
    "slippage": 0.0001,  # 滑点
    "rateInHour": 0.000003,  # 杠杆利率
    "entryOrders": 0.0008,  # 挂单手续费
    "eatOrder": 0.001,  # 吃单手续费
    "lever": 10,
    "liability": 0.0,  # 负债
    "instId": "BTC-USDT",
    "name": '柳尚佐',
    "bar": "1H",  # 粒度
    "table_name": "BTC_USDT_1H",
    "start_timestamp": "2019-10-1 20:00:00",
    "end_timestamp": "2022-11-6 00:00:00",
    # "bar": "30m",  # 粒度
    # "table_name": "BTC_USDT_30m",
    # "start_timestamp": "2019-10-4 00:00:00",
    # "end_timestamp": "2022-11-6 00:00:00",
    # "bar": "15m",  # 粒度
    # "table_name": "BTC_USDT_15m",
    # "start_timestamp": "2020-8-30 00:00:00",
    # "end_timestamp": "2022-11-6 00:00:00",
    # "bar": "5m",  # 粒度
    # "table_name": "BTC_USDT_5m",
    # "start_timestamp": "2021-2-15 00:00:00",
    # "end_timestamp": "2022-11-6 00:00:00",
}


class ConfigEngine:

    def get_config(self, type=None):
        if type:
            return CONFIG[type]
        else:
            return CONFIG
