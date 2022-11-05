from concurrent.futures import ThreadPoolExecutor
from share.request import Request


class BaseEngine:
    def __init__(self):
        self.pools = ThreadPoolExecutor(
            5, thread_name_prefix='Account_Thread_Pool')
        self.request = Request().request
    # 未来可以做一些进度条，每秒并发数量等数据展示的内容


class OkxCrawlerEngine(BaseEngine):
    def __init__(self,  config=None) -> None:
        BaseEngine.__init__(self)
        self.bar = config['bar']
        self.instId = config['instId']

    def get_market(self,  after=None, limit=100):
        try:
            future = self.pools.submit(self._get_data, after, limit)
            res = future.result()
            return res[0]['data']
        except Exception as e:
            raise Exception('爬虫错误', str(e))

    def _get_data(self,  after=None, limit=100):
        if not after:
            print('当前未定义时间戳')

        params = {"instId": self.instId, "bar": self.bar, "limit": limit}
        if after:
            params["after"] = str(after)
        kline = self.request("GET", "/api/v5/market/history-candles", params)

        return kline
