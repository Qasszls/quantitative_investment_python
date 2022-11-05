CONFIG = {
    "initFund": 500000,
    "initCoin": 0,
    "slippage": 0.01,
    "rateInHour": 0.000003,
    "EntryOrders": 0.0008,
    "eatOrder": 0.001,
    "level": 10,
    "bar": "5m",
    "instId": "BTC-USDT",
    "name": '柳尚佐',
    "table_name": "BTC_USDT_5m",
    "start_timestamp":"2021-8-29 23:59:59",
    # "start_timestamp":"2022-9-1 00:00:00",
    "end_timestamp":"2022-10-30 00:00:00"
}


class ConfigEngine:

    def get_config(self, type=None):
        if type:
            return CONFIG[type]
        else:
            return CONFIG
