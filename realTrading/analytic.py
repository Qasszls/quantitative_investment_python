"""
    解析器
    功能
        1.负责解析特定交易所传入的数据结构
        2.负责输出统一的数据结构
    属性
        1.传入数据结构 
            1.1 okx的行情数据结构
            1.2 ……
        2.输出数据结构 standard_data_structures
            粒度：channel
            币对名称：instId
            行情：market
                时间戳：timestamp
                开盘价：open
                最高价格：high
                最低价格：low
                收盘价格：close
                交易量/张：vol
                交易量/币：volCcy
    方法
        1.run-解析(marketData){……}
    分析
        1.传入的数据分为多种
            1.1 订阅频道成功后的推送（本期希望屏蔽的内容）
            1.2 服务端对于行情的推送（本期期望处理的内容）******
            1.3 请求端口回调的数据（不用理会）
            1.4 其他长连接返回的数据，比如：私有频道的持仓信息，交易回调，订单详情等。（不用理会）
    结果
        1.只处理服务端对于行情的推送，其他的或屏蔽，或不予处理。
    使用方法
        输入交易所名称，实例化一个指定交易所的解析器
        解析器.run(行情数据) 可以返回标准格式化的数据
"""

# 标准数据处理的数据结构字段
SDS = {
    'channel': '',  # 粒度
    'instId': '',  # 币对
    'market': {
        'date': '',  # 时间戳
        'vol': '',  # 成交量/张
        'volCcy': '',  # 成交量/币
        'open': '',  # 开盘价
        'high': '',  # 最高价
        'low': '',  # 收盘价
        'close': '',  # 收盘价
    }  # 行情数据
}


class Base():
    def __init__(self):
        # 标准的输出数据结构
        self.standard_data_structures = SDS

    def run(self):
        pass


class Okx(Base):
    def __init__(self):
        Base.__init__(self)
        self.input_structures = {
            'arg': {'channel': 'candle15m', 'instId': 'BTC-USDT'},
            'data': [
                ['1665163800000', '19443.9', '19459.6', '19425.9',
                    '19459.6', '42.5582242', '827681.30939902']
            ]}

    def run(self, data):
        self.standard_data_structures['instId'] = self._get_instId(data)
        self.standard_data_structures['channel'] = self._get_channel(data)
        self.standard_data_structures['market'] = self._get_market(data)

    # 获取币对
    def _get_instId(self, data):
        return data['arg']['instId']

    # 获取粒度
    def _get_channel(self, data):
        return data['arg']['channel']

    # 获取market
    def _get_market(self, data):
        market_data = data['data'][0]
        return {
            'timestamp': market_data[0],
            'open': market_data[1],
            'high': market_data[2],
            'low': market_data[3],
            'close': market_data[4],
            'vol': market_data[5],
            'volCcy': market_data[6]
        }
