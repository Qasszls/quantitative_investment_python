CONFIG = {
    "initFund": 5000000.0, # 初始资金
    "initCoin": 1.0,  # 初始币数量
    "avgPx": 48400.0,  # 开仓均价
    "slippage": 0.01, # 滑点
    "rateInHour": 0.000003, # 杠杆利率
    "entryOrders": 0.0008, # 挂单手续费
    "eatOrder": 0.001, # 吃单手续费
    "level": 10,
    "bar": "5m", # 粒度
    "instId": "BTC-USDT",
    "name": '柳尚佐',
    "table_name": "BTC_USDT_5m",
    # "start_timestamp": "2021-8-29 23:59:59",
    "start_timestamp":"2022-10-1 00:00:00",
    "end_timestamp": "2022-10-30 00:00:00"
}


class ConfigEngine:

    def get_config(self, type=None):
        if type:
            return CONFIG[type]
        else:
            return CONFIG
