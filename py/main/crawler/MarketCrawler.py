# -*- coding:UTF-8 -*-
import base64
import hmac
import json
import time
import requests
import emoji

from urllib.parse import urljoin


class MarketCrawler:
    """OKEX Spot REST API client."""
    def __init__(self,
                 access_key,
                 secret_key,
                 passphrase,
                 host=None,
                 simulated=False):
        self._host = host or "https://www.okex.com"
        self._access_key = access_key
        self._secret_key = secret_key
        self._passphrase = passphrase
        self._simulated = simulated

    # 工具函数

    def request(self,
                method,
                uri,
                params=None,
                body=None,
                headers=None,
                auth=False):
        """Initiate network request
      @param method: request method, GET / POST / DELETE / PUT
      @param uri: request uri
      @param params: dict, request query params
      @param body: dict, request body
      @param headers: request http header
      @param auth: boolean, add permission verification or not
      """
        if params:
            query = "&".join(
                ["{}={}".format(k, params[k]) for k in sorted(params.keys())])
            uri += "?" + query
        url = urljoin(self._host, uri)

        if auth:
            timestamp = (str(time.time()).split(".")[0] + "." +
                         str(time.time()).split(".")[1][:3])
            if body:
                body = json.dumps(body)
            else:
                body = ""
            message = str(timestamp) + str.upper(method) + uri + str(body)
            mac = hmac.new(
                bytes(self._secret_key, encoding="utf8"),
                bytes(message, encoding="utf-8"),
                digestmod="sha256",
            )
            d = mac.digest()
            sign = base64.b64encode(d)

            if not headers:
                headers = {}
            if self._simulated:
                headers["x-simulated-trading"] = '1'
            headers["Content-Type"] = "application/json"
            headers["OK-ACCESS-KEY"] = self._access_key
            headers["OK-ACCESS-SIGN"] = sign
            headers["OK-ACCESS-TIMESTAMP"] = str(timestamp)
            headers["OK-ACCESS-PASSPHRASE"] = self._passphrase
        result = requests.request(method,
                                  url,
                                  data=body,
                                  headers=headers,
                                  timeout=10).json()
        if result.get("code") and result.get("code") != "0":
            return None, result
        return result, None

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
