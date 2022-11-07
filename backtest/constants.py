# 数据库错误码
from logging import _Level


TABLE_NOT_EXITS = 1146

BUY = -1.0
SELL = 1.0


class AccountStructure:
    """用户资产信息
    """

    def __init__(self, fund) -> None:
        self.arg = {
            "channel": "account",
            "ccy": "BTC",
            "uid": "77982378738415879"}

        self.data = [{
            "details": [
                {
                    "availBal": fund,
                }
            ]
        }]


class PositionsStructure:
    """用户持仓
    """

    def __init__(self, uplRatio=0.0, availPos=0.0, avgPx=0.0, lever=1) -> None:
        self.arg = {
            "channel": "positions",
            "uid": "",
            "instType": "FUTURES"}
        self.data = [
            {
                "uplRatio": uplRatio,  # 未实现收益率
                "avgPx": avgPx,  # 开仓均价
                "availPos": availPos,  # 可平仓数量
                "level": lever
            }]


class Market:
    def __init__(self, k_line_data) -> None:
        self.k_line_data = k_line_data
        self.timestamp = k_line_data[0]
        self.open = float(k_line_data[1])
        self.high = float(k_line_data[2])
        self.low = float(k_line_data[3])
        self.close = float(k_line_data[4])
        self.vol = float(k_line_data[5])
        self.volCcy = float(k_line_data[6])
