# -*- coding:UTF-8 -*-
import base64
import hmac
import json
import time
import requests
import emoji

from urllib.parse import urljoin


class Request:
    """OKEX Spot REST API client."""
    def __init__(self, trading_type='virtualPay'):
        # 取出任务队列 与 滤出队列
        f = open('../config.json', 'r')
        config = json.load(f)
        _pay = config[trading_type]
        self._host = _pay['host']
        self._access_key = _pay['access_key']
        self._secret_key = _pay['secret_key']
        self._passphrase = _pay['passphrase']
        self.trading_type = trading_type

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
            sign = str(base64.b64encode(d), 'utf-8')

            if not headers:
                headers = {}
            if self.trading_type == 'virtualPay':
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
