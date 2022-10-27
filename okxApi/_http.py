# -*- coding:UTF-8 -*-

from share.utils import to_json_stringify
from share.request import Request
import sys
import asyncio
import time
import json

from numpy import result_type
from events.engine import Event
from events.event import EVENT_LOG

sys.path.append('..')


class HttpApi:
    def __init__(self, event_engine, user_info=None):
        self.req = Request(user_info)
        self.event_engine = event_engine

    # 再次封装
    def request(self, path, params=None, body=None, methods='GET', auth=False):
        try:
            result, error = self.req.request(methods,
                                             path,
                                             params,
                                             body=body,
                                             auth=auth)
        except:
            result = None
            error = '网络出错'
        if result:
            return result['data'], error
        else:
            event: Event = Event(EVENT_LOG, '接口'+path +
                                 to_json_stringify(error))
            self.event_engine.put(event)
            return result, error

    # 获取okex服务器时间
    def get_public_time(self):
        return self.request('/api/v5/public/time')

    # 获取服务器更新时间
    def get_update_status(self):
        return self.request('/api/v5/system/status')

    # 获取okex @params 最大可买卖/开仓数量  （最多可以买/卖多少个币）买进来
    def get_account_max_size(self, params):
        return self.request('/api/v5/account/max-size',
                            params=params,
                            auth=True)

    # 获取okex @params 最大可用  拿出去
    def get_account_max_avail_size(self, params):
        return self.request('/api/v5/account/max-avail-size',
                            params=params,
                            auth=True)

    # 获取交易产品基础信息-主要拿最小交易数量和交易精度
    def get_public_instruments(self, params):
        return self.request('/api/v5/public/instruments', params=params)

    # 普通下单
    def trade_order(self, params):
        return self.request('/api/v5/trade/order',
                            body=params,
                            methods="POST",
                            auth=True)

    # 订单详情
    def search_order(self, params):
        return self.request('/api/v5/trade/order', params=params, auth=True)

    # 市价仓位全平
    def close_position(self, params):
        return self.request('/api/v5/trade/close-position',
                            body=params,
                            methods="POST",
                            auth=True)

    # 策略委托下单
    def order_algo(self, params):

        return self.request('/api/v5/trade/order-algo',
                            body=params,
                            methods="POST",
                            auth=True)

    # 获取当个产品行情信息
    def market_ticker(self, params):
        return self.request('/api/v5/market/ticker', params=params)

    # 获取指数k线行情
    def _get_kline_data(self, params):
        return self.request('/api/v5/market/index-candles', params=params)

    # # 获取杠杆倍数
    # def get_account_leverage_info(self, params):
    #     """
    #     参数名	类型	是否必须	描述
    #     instId	String	是	产品ID
    #     mgnMode	String	是	保证金模式 isolated：逐仓 cross：全仓
    #     """
    #     result = self.request('/api/v5/account/leverage-info',
    #                           params,
    #                           auth=True)
    #     print(result)
    #     return result

    # # 设置杠杆倍数
    def set_account_set_leverage(self, params):
        result = self.request('/api/v5/account/set-leverage',
                              methods='POST',
                              body=params,
                              auth=True)
        return result
