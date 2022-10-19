# -*- coding:UTF-8 -*-
import base64
import hmac
import json
import time
import requests
import emoji
import sys

sys.path.append('..')
from share.request import Request


class MarketCrawler:
    """OKEX Spot REST API client."""
    def __init__(self):
        self.request = Request('virtualPay').request

    # 流程函数
    def fetch_history_candles(
        self,
        limit,
        bar,
        instId=None,
        after=None,
        before=None,
    ):
        if not after and not before:
            print('当前未定义时间戳')
        if not instId:
            instId = "BTC-USDT"
        params = {"instId": instId, "bar": bar, "limit": limit}
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        fifteen_min_kline = self.request("GET",
                                         "/api/v5/market/history-candles",
                                         params)
        # print(params, fifteen_min_kline)
        return fifteen_min_kline
