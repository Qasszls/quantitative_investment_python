# -*- coding:UTF-8 -*-

from util.TimeStamp import TimeTamp
# from dingtalkchatbot.chatbot import DingtalkChatbot
import base64
import hmac
import sys
import time
import websocket
import json

sys.path.append('..')

PUB_URL = "wss://ws.okx.com:8443/ws/v5/public"
PRI_URL = "ws://ws.okx.com:8443/ws/v5/private"


class BaseSocketApi:
    def __init__(self):
        None

    # 订阅函数

    def _get_base(self, ws, op='subscribe', args=None):
        _a = []
        # 编辑args
        if isinstance(args, list):
            if len(args) == 0:
                return
            for item in args:
                _a.append(item)
        elif isinstance(args, dict):
            _a.append(args)
        else:
            print('args类型错误', type(args))
            return
        # 发送订阅
        _s = {'op': op, 'args': _a}
        ws.send(json.dumps(_s))


class PublicSocketApi(BaseSocketApi):
    def __init__(self, on_created, on_message, on_closed, user_info):

        BaseSocketApi.__init__(self)

        self.market_lv = user_info['market_lv']
        self.symbol = user_info['symbol']
# 下面的内容后期都换成事件驱动的
        self.on_created = on_created
        self.on_message = on_message
        self.on_closed = on_closed

    # 启动公有链接
    def run(self):
        ws = websocket.WebSocketApp(PUB_URL,
                                    on_open=self.ON_OPEN,
                                    on_message=self.ON_MESSAGE,
                                    on_error=self.ON_ERROR,
                                    on_close=self.ON_CLOSED)
        # ws.run_forever(ping_interval=30, ping_timeout=10, proxy_type="socks5",
        #                http_proxy_host='127.0.0.1', http_proxy_port='10000')
        ws.run_forever(http_proxy_host="127.0.0.1",
                       http_proxy_port=10000, proxy_type='socks5')

    # 生命周期函数 再包装

    def ON_OPEN(self, ws):
        self._get_base(
            ws, args={"channel": self.market_lv, "instId": self.symbol})
        if self.on_created:
            self.on_created()

    def ON_MESSAGE(self, ws, *arg):
        self.on_message(arg)

    def ON_CLOSED(self, ws, *arg):
        print('ON_CLOSED')
        self.on_closed(arg)

    def ON_ERROR(self, ws, *args):
        print('ws 公共链接出错', args)


class PrivateSocketApi(BaseSocketApi):
    def __init__(self, on_created, on_message, on_closed, user_info):

        BaseSocketApi.__init__(self)

        self.apiKey = user_info['access_key']
        self.market_lv = user_info['market_lv']
        self.passphrase = user_info['passphrase']
        self.SecretKey = user_info['secret_key']
        self.trading_type = user_info['trading_type']

        self.on_created = on_created
        self.on_message = on_message
        self.on_closed = on_closed

    # 启动私有链接
    def run(self):
        ws = websocket.WebSocketApp(PRI_URL,
                                    on_open=self.ON_OPEN,
                                    on_message=self.ON_MESSAGE,
                                    on_error=self.ON_ERROR,
                                    on_close=self.ON_CLOSED)
        ws.run_forever(ping_interval=30, ping_timeout=10)

    # 生命周期函数

    async def ON_OPEN(self, ws):
        status = await self.login(ws)
        if not status:
            raise Exception('登录出错')
        await self._positions(ws)
        await self._account(ws)
        if self.on_created:
            self.on_created()

    def ON_MESSAGE(self, ws, res):
        self.on_message(res)

    def ON_CLOSED(self, ws, res):
        self.on_closed(res)

    def ON_ERROR(self, ws, *args):
        print('ws 公共链接出错')

    # 订阅 登录

    async def login(self, _w):
        timestamp = (str(time.time()).split(".")[0])

        # 私有函数
        def _get_sign():
            message = str(timestamp) + "GET" + '/users/self/verify'
            mac = hmac.new(
                bytes(self.SecretKey.encode('utf-8')),
                bytes(message.encode('utf-8')),
                digestmod="sha256",
            )
            d = mac.digest()
            sign = base64.b64encode(d)
            return str(sign, 'utf-8')

        args = {'apiKey': '', 'passphrase': '', 'timestamp': '', 'sign': ''}

        args['apiKey'] = self.apiKey
        args['passphrase'] = self.passphrase
        args['timestamp'] = timestamp
        args['sign'] = _get_sign()

        await self._get_base(_w, op='login', args=args)

        recv_text = json.loads(await _w.recv())
        # 成功或失败推送处理
        if 'event' in recv_text:
            if recv_text['event'] == 'error':
                print('登录出错，错误码为：' + recv_text['code'])
                return False
            else:
                if recv_text['code'] == '0':
                    return True

    # 订阅持仓频道-私有
    async def _positions(self, _w):
        await self._get_base(_w,
                             args={
                                 "channel": "positions",
                                 "instType": "ANY"
                             })

    # 订阅持仓频道-私有
    async def _account(self, _w):
        await self._get_base(_w, args={
            "channel": "account",
        })
