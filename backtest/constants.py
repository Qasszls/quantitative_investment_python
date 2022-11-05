# 数据库错误码
TABLE_NOT_EXITS = 1146

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

       # 设置data下的字段值
    def set_data(self, type, data):
        self.data[0]['details'][type] = data

    # 获取字段数据
    def get_data(self, type=None):
        if type:
            return self.data[0]['details'][type]
        else:
            return {"arg": self.arg, "data": self.data}


class PositionsStructure:
    """用户持仓
    """

    def __init__(self, coin=0) -> None:
        self.arg = {
            "channel": "positions",
            "uid": "",
            "instType": "FUTURES"}
        self.data = [
            {
                "uplRatio": 0.0,  # 未实现收益率
                "avgPx": 0,  # 开仓均价
                "availPos": coin  # 可平仓数量
            }]

    # 设置data下的字段值
    def set_data(self, type, data):
        self.data[0][type] = data

    # 获取字段数据
    def get_data(self, type=None):
        if type:
            return self.data[0][type]
        else:
            if self.data[0]['availPos'] == 0:
                return {"arg": self.arg, "data": []}
            else:
                return {"arg": self.arg, "data": self.data}
